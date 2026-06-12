#!/usr/bin/env python3
"""
Demo Studio — interactive web stage (standalone, NO ROS).

A presentation server for the "robot eyes + brain + hand" demo:
  - live camera (cv2 device) as the robot's eyes, streamed as MJPEG;
  - a natural-language / voice command ("pick up the mouse") triggers an
    OPEN-VOCABULARY lock. Vision backend is auto-selected by available key:
    OPENAI_API_KEY -> OpenAI GPT-4o (perception/openai_backend.py, stdlib HTTP);
    else an Anthropic key -> Claude Vision (perception/api_backend.py).
    Force with --vision openai|claude|none; no key -> click-to-lock fallback.
  - a simulated 6-axis arm + dexterous hand (sim/arm_model.py) animates a
    reach -> grasp -> lift, with per-motor telemetry streamed to the page.

This is independent of the ROS control stack (the arm/hand/motor params are a
presentation simulation). It opens the camera directly with cv2, so the live
robot-core service (which holds /dev/video1) must be stopped first for the
camera acts.

Run:
    python3 gui/demo_studio.py --device 1 --port 8090
    python3 gui/demo_studio.py --camera none --port 8090     # no camera (UI preview)
Open http://<host>:<port> in a browser (Chrome for voice input).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

from sim.arm_model import ArmController

try:
    import cv2
    import numpy as np
    _CV = True
except Exception:
    _CV = False

# Verbs / stopwords stripped when extracting the target object from a command.
_STOP = ["幫我", "請", "幫", "拿起", "拿", "抓住", "抓", "取", "撿起", "撿", "把", "桌上的",
         "桌上", "上面的", "那個", "這個", "the", "a", "an", "please", "pick", "up",
         "grab", "get", "take", "hold", "on", "desk", "table", "that", "this", "me",
         "for", "lift"]


def load_secrets(path=None):
    """Load KEY=VALUE lines from config/secrets.env into the environment.

    Existing env vars take precedence (so an explicit `export` still wins).
    Supports optional `export ` prefix, # comments, and quoted values. Keys are
    never logged. Missing file is fine (silent).
    """
    path = path or os.path.join(REPO, "config", "secrets.env")
    loaded = []
    try:
        with open(path) as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("export "):
                    s = s[len("export "):]
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and v and not os.environ.get(k):
                    os.environ[k] = v
                    loaded.append(k)
    except FileNotFoundError:
        return []
    return loaded


def extract_target(text):
    """Crude open-vocab target extractor: strip verbs/stopwords -> object word."""
    t = (text or "").strip()
    low = t.lower()
    for w in sorted(_STOP, key=len, reverse=True):
        low = low.replace(w.lower(), " ")
        t = t.replace(w, " ")
    cleaned = " ".join((t if any(ord(c) > 127 for c in t) else low).split())
    return cleaned or t.strip() or text


# ---- shared state ----------------------------------------------------------

class Studio:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.ctrl = ArmController(img_w=args.img_w, img_h=args.img_h)
        self.frame = None              # latest BGR frame (np array) or None
        self.cam_hz = 0.0
        self.detectors = {}            # provider -> lazily built vision detector
        self.providers = self._available_providers(getattr(args, "vision", "auto"))
        self.provider = self.providers[0] if self.providers else "none"
        self.api_ready = bool(self.providers)
        # Local ONNX fallback (zero API): YOLOv8 detection_v2.onnx, 4 classes.
        self.onnx_sess = None
        self.onnx_model = os.path.join(REPO, "models", "active", "detection_v2.onnx")
        self.onnx_ready = os.path.exists(self.onnx_model)
        self.det_classes = None
        self._stop = False
        # 大腦 Agent（可抽換模型：雲端 LLM ↔ 本地，含 fallback）。視覺鎖定改走此抽象層。
        self.last_brain = None         # 最近一次 BrainAgent 視覺決策（稽核用）
        self.detect_retries = int(os.environ.get("BRAIN_DETECT_RETRIES", "3"))  # 鎖定多幀重試次數
        self.brain = self._build_brain()

    # provider -> env var(s) that enable it
    PROVIDER_KEYS = {
        "gemini": ("GEMINI_API_KEY",),
        "openai": ("OPENAI_API_KEY",),
        "claude": ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
    }
    # auto preference order (gemini first — see notes; quota-dead providers
    # simply return [] and the lock chain falls through to the next one).
    AUTO_ORDER = ["gemini", "openai", "claude"]

    @classmethod
    def _has_key(cls, p):
        return any(os.environ.get(k) for k in cls.PROVIDER_KEYS.get(p, ()))

    @classmethod
    def _available_providers(cls, pref):
        """Ordered list of open-vocab backends whose key is present.

        pref 'auto' -> all available in AUTO_ORDER; a specific provider name ->
        just that one if its key exists; 'none' -> [].
        """
        if pref in cls.PROVIDER_KEYS:
            return [pref] if cls._has_key(pref) else []
        if pref == "none":
            return []
        return [p for p in cls.AUTO_ORDER if cls._has_key(p)]

    @classmethod
    def _resolve_provider(cls, pref):
        av = cls._available_providers(pref)
        return av[0] if av else "none"

    # ---- camera ----
    def camera_loop(self):
        if not _CV:
            return
        cap = None
        if self.args.camera == "device":
            cap = cv2.VideoCapture(self.args.device)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.args.img_w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.args.img_h)
        last = time.time()
        while not self._stop:
            if cap is not None and cap.isOpened():
                ok, f = cap.read()
                if ok:
                    self.frame = f
            else:
                self.frame = self._test_pattern()
            now = time.time()
            self.cam_hz = round(1.0 / max(now - last, 1e-3), 1)
            last = now
            time.sleep(1.0 / 25.0)
        if cap is not None:
            cap.release()

    def _test_pattern(self):
        w, h = self.args.img_w, self.args.img_h
        img = np.zeros((h, w, 3), np.uint8)
        img[:] = (40, 40, 48)
        cv2.rectangle(img, (0, int(h * 0.7)), (w, h), (60, 55, 50), -1)  # desk
        # a fake "mouse" so the click/preset fallback has a target
        cx, cy = int(w * 0.62), int(h * 0.62)
        cv2.ellipse(img, (cx, cy), (46, 30), 0, 0, 360, (150, 150, 160), -1)
        cv2.putText(img, "TEST PATTERN (no camera)", (16, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 210), 2)
        return img

    def jpeg(self):
        if not _CV or self.frame is None:
            return None
        ok, buf = cv2.imencode(".jpg", self.frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes() if ok else None

    # ---- sim ----
    def sim_loop(self):
        dt = 1.0 / 30.0
        while not self._stop:
            with self.lock:
                self.ctrl.step(dt)
            time.sleep(dt)

    # ---- command / detection ----
    def on_command(self, text):
        with self.lock:
            self.ctrl.set_locating(text)
        threading.Thread(target=self._locate_worker, args=(text,), daemon=True).start()

    def _build_brain(self):
        """組出 BrainAgent（可抽換模型）。失敗（如模組未部署）→ None，回退舊鎖定鏈。"""
        try:
            from brain_agent.backends import build_default_agent
            return build_default_agent(logger=None)
        except Exception:
            return None

    def _locate_worker(self, text):
        """視覺鎖定：優先走 BrainAgent（依政策選雲端/本地 + fallback）；
        BrainAgent 不可用時回退舊鏈（open-vocab API -> 本地 ONNX -> 手動點選）。"""
        target = extract_target(text)
        if not (_CV and self.frame is not None):
            with self.lock:
                self.ctrl.fail_lock("no camera frame")
            return
        dets = []
        if self.brain is not None:               # 統一抽象層：雲端/本地 + fallback + 稽核
            # 多幀重試：每指令抓多張即時影像，取第一個有偵到的——對抗「單張沒拍好 / VLM 當次回空」。
            for attempt in range(self.detect_retries):
                f = self.frame
                if f is None:
                    break
                dets = self.brain.detect(f.copy(), class_hints=[target]) or []
                self.last_brain = self.brain.last_decision
                if dets:
                    break
                time.sleep(0.4)                  # 等相機換下一張影像再試
        else:                                    # 回退：舊的手刻鎖定鏈
            frame = self.frame.copy()
            if self.providers:
                dets = self._api_detect(frame, target)
            if not dets and self.onnx_ready:
                dets = self._onnx_detect(frame)
        if not dets:
            with self.lock:
                self.ctrl.fail_lock(f"'{target}' 未偵到 — 點畫面手動鎖定")
            return
        d = self._choose_det(dets, text, target)
        with self.lock:
            self.ctrl.set_lock(d.get("class", target) or target,
                               int(d["cx"]), int(d["cy"]),
                               int(d.get("w", 60)), int(d.get("h", 60)),
                               float(d.get("score", 0.0)))

    def _make_detector(self, p):
        if p == "gemini":
            from perception.gemini_backend import GeminiVisionDetector
            return GeminiVisionDetector(conf_thresh=0.3)
        if p == "openai":
            from perception.openai_backend import OpenAIVisionDetector
            return OpenAIVisionDetector(conf_thresh=0.3)
        from perception.api_backend import ClaudeVisionDetector
        return ClaudeVisionDetector(conf_thresh=0.3)

    def _api_detect(self, frame, target):
        """Try each available provider in order; return the first non-empty
        result. Quota-blocked / erroring providers return [] and are skipped."""
        for p in self.providers:
            try:
                det = self.detectors.get(p) or self._make_detector(p)
                self.detectors[p] = det
                dets = det.detect(frame, class_hints=[target]) or []
                if dets:
                    return dets
            except Exception:
                continue
        return []

    def _onnx_detect(self, frame):
        try:
            if self.onnx_sess is None:
                import onnxruntime as ort
                from perception.classes import get_class_names
                self.onnx_sess = ort.InferenceSession(
                    self.onnx_model, providers=["CPUExecutionProvider"])
                self.det_classes = get_class_names()
            from perception.detection_utils import decode_yolov8
            H, W = frame.shape[:2]
            img = cv2.resize(frame, (224, 224)).astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))[None, ...]
            name = self.onnx_sess.get_inputs()[0].name
            out = self.onnx_sess.run(None, {name: img})[0]
            return decode_yolov8(out, W, H, input_size=224, conf_thresh=0.35,
                                 iou_thresh=0.45, class_names=self.det_classes)
        except Exception:
            return []

    @staticmethod
    def _choose_det(dets, command, target):
        """Pick the detection the user asked for: class named in the command
        (via the zh/en lexicon), else label substring-matches the target, else
        the highest-confidence detection."""
        try:
            from task_parser.language_backend import LEXICON
        except Exception:
            LEXICON = {}
        cl = (command or "").lower()
        wanted = {canon for kw, canon in LEXICON.items() if kw.lower() in cl}
        named = [d for d in dets if str(d.get("class", "")).lower() in wanted]
        if named:
            return sorted(named, key=lambda x: -x.get("score", 0))[0]
        tl = (target or "").lower()
        sub = [d for d in dets if tl and (tl in str(d.get("class", "")).lower()
                                          or str(d.get("class", "")).lower() in tl)]
        if sub:
            return sorted(sub, key=lambda x: -x.get("score", 0))[0]
        return sorted(dets, key=lambda x: -x.get("score", 0))[0]

    def on_manual_lock(self, cx, cy, label="object"):
        with self.lock:
            self.ctrl.set_lock(label, int(cx), int(cy), 70, 60, 1.0)

    def snapshot(self):
        with self.lock:
            snap = self.ctrl.snapshot()
        snap["cam_hz"] = self.cam_hz
        snap["api_ready"] = self.api_ready
        snap["vision"] = self.provider
        snap["providers"] = self.providers
        snap["onnx"] = self.onnx_ready
        snap["camera"] = self.args.camera
        snap["brain"] = self.last_brain.as_dict() if self.last_brain else None
        return snap


STUDIO = None  # set in main


# ---- HTTP ------------------------------------------------------------------

_CT = {".html": "text/html", ".js": "application/javascript",
       ".css": "text/css", ".json": "application/json",
       ".urdf": "text/xml"}  # .stl/.dae 等走預設 application/octet-stream（_asset 以二進位讀檔）


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/plain", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _asset(self, name):
        path = os.path.normpath(os.path.join(ASSETS, name))
        if not path.startswith(ASSETS) or not os.path.isfile(path):
            return self._send(404, "not found")
        with open(path, "rb") as f:
            body = f.read()
        ext = os.path.splitext(path)[1]
        self._send(200, body, _CT.get(ext, "application/octet-stream"))

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            return self._asset("studio.html")
        if p.startswith("/assets/"):
            return self._asset(p[len("/assets/"):])
        if p == "/state.json":
            return self._send(200, json.dumps(STUDIO.snapshot()), "application/json")
        if p == "/stream.mjpg":
            return self._stream()
        return self._send(404, "not found")

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while True:
                jpg = STUDIO.jpeg()
                if jpg:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpg)}\r\n\r\n".encode())
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
                time.sleep(1.0 / 20.0)
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        if self.path == "/command":
            STUDIO.on_command(str(body.get("text", "")).strip())
            return self._send(200, json.dumps({"ok": True}), "application/json")
        if self.path == "/lock":
            STUDIO.on_manual_lock(body.get("cx", 320), body.get("cy", 240),
                                  body.get("label", "object"))
            return self._send(200, json.dumps({"ok": True}), "application/json")
        return self._send(404, "not found")


def _open_browser(port):
    """在本機桌面開瀏覽器指向 studio。從 SSH 啟動時自動鎖 DISPLAY=:0（Orin 桌面 session）。
    無桌面/無瀏覽器時靜默略過（只會看到上方印出的 URL）。"""
    url = f"http://localhost:{port}"
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")                                   # SSH 啟動時指向實體桌面
    env.setdefault("XAUTHORITY", os.path.expanduser("~/.Xauthority"))
    # 從 SSH 啟動時，user-session 的 runtime/dbus 不在環境裡，補上（GUI app 需要）。
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{os.getuid()}/bus")
    # 優先非 snap 瀏覽器（firefox/epiphany）——snap chromium 從 SSH 啟動會因缺 cap 而開不了視窗。
    for b in ("firefox", "epiphany-browser", "epiphany", "chromium-browser", "chromium", "xdg-open"):
        if shutil.which(b):
            if "chromium" in b:
                cmd = [b, f"--app={url}"]
            elif b == "firefox":
                cmd = [b, "--new-window", url]
            else:
                cmd = [b, url]
            try:
                subprocess.Popen(cmd, env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  [open] 已在桌面開啟瀏覽器（{b}）→ {url}", flush=True)
                return
            except Exception as e:
                print(f"  [open] {b} 開啟失敗：{e}", flush=True)
    print(f"  [open] 找不到可用瀏覽器；請手動開 {url}", flush=True)


def main():
    global STUDIO
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", choices=["device", "none"], default="device")
    ap.add_argument("--device", type=int, default=1, help="/dev/videoN")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--img-w", type=int, default=640)
    ap.add_argument("--img-h", type=int, default=480)
    ap.add_argument("--vision", choices=["auto", "gemini", "openai", "claude", "none"],
                    default="auto", help="open-vocab lock backend (auto tries all by key)")
    ap.add_argument("--open", action="store_true",
                    help="啟動後在本機桌面自動開瀏覽器（Orin 桌面 DISPLAY=:0）")
    args = ap.parse_args()

    loaded = load_secrets()
    if loaded:
        print(f"[secrets] loaded from config/secrets.env: {', '.join(loaded)}")
    STUDIO = Studio(args)
    threading.Thread(target=STUDIO.camera_loop, daemon=True).start()
    threading.Thread(target=STUDIO.sim_loop, daemon=True).start()

    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("=" * 64)
    print(f"  Demo Studio:  http://<host>:{args.port}")
    print(f"  camera={args.camera}  device=/dev/video{args.device}  "
          f"cv2={'yes' if _CV else 'NO'}  "
          f"vision={','.join(STUDIO.providers) or 'none'}  "
          f"onnx_lock={'yes' if STUDIO.onnx_ready else 'no'}")
    print("  (Ctrl-C 結束)")
    print("=" * 64, flush=True)
    if args.open:
        _open_browser(args.port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        STUDIO._stop = True
        srv.shutdown()


if __name__ == "__main__":
    main()
