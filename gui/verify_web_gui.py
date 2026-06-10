#!/usr/bin/env python3
"""
Verification Web GUI — vision + simulation dashboard.

A lightweight, dependency-free (stdlib http.server only) web dashboard for
verifying the vision pipeline and the BC policy in simulation. View it from any
browser on the network at  http://<orin-ip>:8088

Panels:
  1. Camera + detection overlay  — live frames with bounding boxes.
  2. Sensor / pose telemetry      — IMU roll/pitch/quat + the 13-dim observation.
  3. 32-joint actions             — bar chart of the policy's joint commands.
  4. Policy vs Expert             — policy(obs) vs ScriptedExpert(obs) + mean-abs diff.

Camera source (param `camera`):
  - "device" (default): open /dev/video<N> directly and run detection in-process
    (self-contained — needs no camera_node/perception_node). NOTE the project's
    real USB cam is /dev/video1, not video0.
  - "ros": subscribe /camera/image_raw and overlay /perception/objects (visualises
    the real ROS pipeline; launch camera_node + perception_node).

IMU comes from /buddy/imu (run sim/sim_sensors_node.py, or a real source).
The policy is loaded from models/active/simple_policy.onnx; the expert is the
same ScriptedExpert used for BC. Runs CPU-only.

Run (device mode, self-contained vision):
    export PYTHONPATH=$PWD; python3 gui/verify_web_gui.py --ros-args \
        -p camera:=device -p device:=1 -p port:=8088
"""

import io
import os
import sys
import json
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, Image
from vision_msgs.msg import Detection2DArray
from std_msgs.msg import Float32MultiArray

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from policy.obs_utils import (
    assemble_obs13, best_detection, build_obs13_from_msgs,
    quat_to_roll_pitch, OBS_DIM, ACT_DIM,
)
from policy.scripted_expert import ScriptedExpert
from perception.detection_utils import decode_yolov8
from perception.classes import get_class_names

try:
    import onnxruntime as ort
    HAS_ORT = True
except Exception:
    HAS_ORT = False


# ── Shared state between ROS callbacks and the HTTP server ────────────────────
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.jpeg = _placeholder_jpeg("waiting for camera...")
        self.telemetry = {}


def _placeholder_jpeg(text):
    img = np.zeros((480, 640, 3), np.uint8)
    cv2.putText(img, text, (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 200, 255), 2)
    ok, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


class RateMeter:
    def __init__(self, win=30):
        self.t = []
        self.win = win

    def tick(self):
        now = time.time()
        self.t.append(now)
        if len(self.t) > self.win:
            self.t.pop(0)

    def hz(self):
        if len(self.t) < 2:
            return 0.0
        dt = self.t[-1] - self.t[0]
        return (len(self.t) - 1) / dt if dt > 0 else 0.0


class VerifyGui(Node):
    def __init__(self, state):
        super().__init__("verify_gui")
        self.state = state
        self.declare_parameter("camera", "device")    # device | ros
        self.declare_parameter("device", 1)            # /dev/videoN for device mode
        self.declare_parameter("port", 8088)
        self.declare_parameter("img_w", 640)
        self.declare_parameter("img_h", 480)
        self.declare_parameter("policy_model", "models/active/simple_policy.onnx")
        self.declare_parameter("detect_model", "models/active/detection_v2.onnx")
        self.declare_parameter("det_conf", 0.5)
        self.declare_parameter("det_size", 224)

        self.camera_mode = self.get_parameter("camera").value
        self.img_w = self.get_parameter("img_w").value
        self.img_h = self.get_parameter("img_h").value
        self.det_conf = self.get_parameter("det_conf").value
        self.det_size = self.get_parameter("det_size").value
        self.expert = ScriptedExpert(img_w=self.img_w, img_h=self.img_h)

        self.policy_sess = self._load_onnx(self.get_parameter("policy_model").value)
        self.detect_sess = (self._load_onnx(self.get_parameter("detect_model").value)
                            if self.camera_mode == "device" else None)
        self.det_classes = get_class_names()

        self._last_imu = None
        self._last_det_msg = None
        self._last_dets = []      # list of {cls, score, cx, cy, w, h}
        self.cam_rate = RateMeter()
        self.imu_rate = RateMeter()

        self.create_subscription(Imu, "/buddy/imu", self._imu_cb, 10)
        if self.camera_mode == "ros":
            self.create_subscription(Image, "/camera/image_raw", self._image_cb, 10)
            self.create_subscription(Detection2DArray, "/perception/objects", self._det_cb, 10)
        else:
            threading.Thread(target=self._device_camera_loop, daemon=True).start()

        # Recompute telemetry at a steady rate even if topics are sparse.
        self.create_timer(0.1, self._update_telemetry)
        self.get_logger().info(
            f"Verify GUI: camera={self.camera_mode} policy={'ok' if self.policy_sess else 'none'} "
            f"detect={'ok' if self.detect_sess else 'n/a'}")

    def _resolve(self, p):
        if not os.path.isabs(p):
            p = os.path.join(os.environ.get("POC_ROOT", os.getcwd()), p)
        return p

    def _load_onnx(self, path):
        if not HAS_ORT:
            return None
        path = self._resolve(path)
        try:
            return ort.InferenceSession(path)
        except Exception as e:
            self.get_logger().warn(f"could not load {path}: {e}")
            return None

    # ── inputs ────────────────────────────────────────────────────────────
    def _imu_cb(self, msg):
        self._last_imu = msg
        self.imu_rate.tick()

    def _det_cb(self, msg):
        self._last_det_msg = msg
        self._last_dets = []
        for d in msg.detections:
            if not d.results:
                continue
            self._last_dets.append({
                "cls": d.results[0].hypothesis.class_id,
                "score": float(d.results[0].hypothesis.score),
                "cx": float(d.bbox.center.position.x),
                "cy": float(d.bbox.center.position.y),
                "w": float(d.bbox.size_x), "h": float(d.bbox.size_y),
            })

    def _image_cb(self, msg):
        try:
            ch = 3 if msg.encoding in ("bgr8", "rgb8") else 1
            # Honour row stride (msg.step may exceed width*ch with padded buffers).
            step = msg.step if msg.step else msg.width * ch
            arr = np.frombuffer(msg.data, np.uint8).reshape(msg.height, step)
            arr = arr[:, : msg.width * ch].reshape(msg.height, msg.width, ch)
            if msg.encoding == "rgb8":
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            elif ch == 1:
                arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            self._publish_frame(arr.copy())
            self.cam_rate.tick()
        except Exception as e:
            self.get_logger().warn(f"image decode failed: {e}")

    def _device_camera_loop(self):
        dev = self.get_parameter("device").value
        cap = cv2.VideoCapture(dev)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.img_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.img_h)
        if not cap.isOpened():
            self.get_logger().error(f"cannot open /dev/video{dev}")
            return
        while rclpy.ok():
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            self._last_dets = self._run_detection(frame)
            self._publish_frame(frame)
            self.cam_rate.tick()
        cap.release()

    def _run_detection(self, frame):
        if self.detect_sess is None:
            return []
        try:
            H, W = frame.shape[:2]
            img = cv2.resize(frame, (self.det_size, self.det_size)).astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))[None, ...]
            name = self.detect_sess.get_inputs()[0].name
            out = self.detect_sess.run(None, {name: img})[0]
            # Shared, tested YOLOv8 decoder (perception/detection_utils.py).
            dets = decode_yolov8(out, W, H, input_size=self.det_size,
                                 conf_thresh=self.det_conf, iou_thresh=0.45,
                                 class_names=self.det_classes)
            # Map "class" -> "cls" for this GUI's dict shape.
            return [{"cls": d["class"], "score": d["score"], "cx": d["cx"],
                     "cy": d["cy"], "w": d["w"], "h": d["h"]} for d in dets]
        except Exception as e:
            self.get_logger().warn(f"detection failed: {e}")
            return []

    def _publish_frame(self, frame):
        for d in list(self._last_dets):  # snapshot ref (set by another thread)
            x1 = int(d["cx"] - d["w"] / 2); y1 = int(d["cy"] - d["h"] / 2)
            x2 = int(d["cx"] + d["w"] / 2); y2 = int(d["cy"] + d["h"] / 2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
            cv2.putText(frame, f'{d["cls"]} {d["score"]:.2f}', (x1, max(y1 - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 1)
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            with self.state.lock:
                self.state.jpeg = buf.tobytes()

    # ── compute telemetry ───────────────────────────────────────────────────
    def _update_telemetry(self):
        # Camera + detections render even without IMU (e.g. ros mode without a
        # sim_sensors/IMU source); obs/policy/expert panels need the IMU.
        tel = {
            "detections": list(self._last_dets),
            "rates": {"cam_hz": round(self.cam_rate.hz(), 1),
                      "imu_hz": round(self.imu_rate.hz(), 1)},
            "has_imu": self._last_imu is not None,
            "has_policy": self.policy_sess is not None,
            "ts": round(time.time(), 2),
        }
        if self._last_imu is not None:
            det = self._best_det_for_obs()
            obs = build_obs13_from_msgs(self._last_imu, self._last_det_msg) \
                if (self.camera_mode == "ros") else self._obs_from_imu_and_det(det)
            roll, pitch = quat_to_roll_pitch(obs[0:4])
            policy_act = self._run_policy(obs)
            expert_act = self.expert.act(obs)
            diff = float(np.mean(np.abs(policy_act - expert_act))) if policy_act is not None else None
            tel["imu"] = {
                "roll_deg": round(float(np.degrees(roll)), 2),
                "pitch_deg": round(float(np.degrees(pitch)), 2),
                "quat": [round(float(x), 4) for x in obs[0:4]],
                "gyro": [round(float(x), 4) for x in obs[4:7]],
                "accel": [round(float(x), 3) for x in obs[7:10]],
            }
            tel["obs"] = [round(float(x), 4) for x in obs]
            tel["policy"] = [round(float(x), 4) for x in policy_act] if policy_act is not None else []
            tel["expert"] = [round(float(x), 4) for x in expert_act]
            tel["diff_mae"] = round(diff, 5) if diff is not None else None
        with self.state.lock:
            self.state.telemetry = tel

    def _best_det_for_obs(self):
        if not self._last_dets:
            return [0.0, 0.0, 0.0]
        b = max(self._last_dets, key=lambda d: d["score"])
        return [b["cx"], b["cy"], b["score"]]

    def _obs_from_imu_and_det(self, det):
        m = self._last_imu
        quat = [m.orientation.x, m.orientation.y, m.orientation.z, m.orientation.w]
        gyro = [m.angular_velocity.x, m.angular_velocity.y, m.angular_velocity.z]
        accel = [m.linear_acceleration.x, m.linear_acceleration.y, m.linear_acceleration.z]
        return assemble_obs13(quat, gyro, accel, det)

    def _run_policy(self, obs):
        if self.policy_sess is None:
            return None
        try:
            name = self.policy_sess.get_inputs()[0].name
            out = self.policy_sess.run(None, {name: obs.reshape(1, -1).astype(np.float32)})[0]
            return np.asarray(out).ravel()[:ACT_DIM]
        except Exception as e:
            self.get_logger().warn(f"policy run failed: {e}")
            return None


# ── HTTP server ───────────────────────────────────────────────────────────────
def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass  # silence per-request logging

        def do_GET(self):
            if self.path.startswith("/data.json"):
                with state.lock:
                    body = json.dumps(state.telemetry).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            elif self.path.startswith("/stream.mjpg"):
                self.send_response(200)
                self.send_header("Content-Type",
                                 "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                try:
                    while True:
                        with state.lock:
                            frame = state.jpeg
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                         b"Content-Length: " + str(len(frame)).encode()
                                         + b"\r\n\r\n" + frame + b"\r\n")
                        time.sleep(0.05)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            else:
                body = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
    return Handler


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>Robot Verify GUI</title><style>
body{background:#0a0a14;color:#cfe;font-family:monospace;margin:0;padding:12px}
h1{color:#3cf;font-size:18px;margin:0 0 10px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.card{background:#11162a;border:1px solid #243;border-radius:8px;padding:10px}
.card h2{font-size:13px;color:#7df;margin:0 0 8px;border-bottom:1px solid #243;padding-bottom:4px}
img{width:100%;border-radius:4px;background:#000}
.kv{font-size:12px;line-height:1.6}.kv b{color:#9fd}
.bar{height:10px;margin:1px 0;background:#1c2440;position:relative;border-radius:2px}
.bar i{position:absolute;top:0;bottom:0;left:50%;background:#3cf}
.bar.e i{background:#f86}
.row{display:flex;align-items:center;font-size:10px;gap:4px}
.row span{width:24px;color:#79a;text-align:right}
.big{font-size:22px;color:#3f9}
.muted{color:#789}
</style></head><body>
<h1>🤖 Robot Verification Dashboard <span id=ts class=muted></span></h1>
<div class=grid>
  <div class=card><h2>1 · Camera + Detection</h2><img id=cam src=/stream.mjpg>
    <div class=kv id=dets></div></div>
  <div class=card><h2>2 · Sensor / Pose Telemetry</h2><div class=kv id=imu></div>
    <div class=kv id=obs style=margin-top:6px></div>
    <div class=kv id=rates style=margin-top:6px></div></div>
  <div class=card><h2>3 · 32-Joint Commands (policy)</h2><div id=joints></div></div>
  <div class=card><h2>4 · Policy vs Expert</h2>
    <div class=kv>mean|diff| = <span id=diff class=big>–</span></div>
    <div id=cmp style=margin-top:6px></div>
    <div class=kv muted style=margin-top:6px>blue = policy &nbsp; orange = expert</div></div>
</div>
<script>
function bars(el,arr,cls){el.innerHTML='';arr.forEach((v,i)=>{
 let r=document.createElement('div');r.className='row';
 let s=document.createElement('span');s.textContent=i;
 let b=document.createElement('div');b.className='bar '+(cls||'');
 let f=document.createElement('i');let w=Math.min(Math.abs(v)*50,50);
 f.style.width=w+'%';f.style.left=(v<0?50-w:50)+'%';b.appendChild(f);
 r.appendChild(s);r.appendChild(b);el.appendChild(r);});}
function cmp(el,p,e){el.innerHTML='';for(let i=0;i<Math.max(p.length,e.length);i++){
 let r=document.createElement('div');r.className='row';
 let s=document.createElement('span');s.textContent=i;r.appendChild(s);
 let wrap=document.createElement('div');wrap.style.flex='1';
 [['',p[i]||0],['e',e[i]||0]].forEach(([c,v])=>{let b=document.createElement('div');
  b.className='bar '+c;let f=document.createElement('i');let w=Math.min(Math.abs(v)*50,50);
  f.style.width=w+'%';f.style.left=(v<0?50-w:50)+'%';b.appendChild(f);wrap.appendChild(b);});
 r.appendChild(wrap);el.appendChild(r);}}
async function tick(){try{let d=await(await fetch('/data.json?'+Date.now())).json();
 if(!d.ts){return}
 document.getElementById('ts').textContent='@'+d.ts;
 // camera + detections + rates render with or without IMU
 document.getElementById('dets').innerHTML='<b>detections:</b> '+
  (d.detections&&d.detections.length?d.detections.map(x=>`${x.cls}(${x.score.toFixed(2)})`).join(', '):'<span class=muted>none</span>');
 if(d.rates)document.getElementById('rates').innerHTML=
  `<b>cam</b> ${d.rates.cam_hz} Hz  <b>imu</b> ${d.rates.imu_hz} Hz  `+
  `<b>policy</b> ${d.has_policy?'loaded':'<span style=color:#f66>none</span>'}`;
 if(d.imu){let im=d.imu;document.getElementById('imu').innerHTML=
   `<b>roll</b> ${im.roll_deg}°  <b>pitch</b> ${im.pitch_deg}°<br>`+
   `<b>quat</b> [${im.quat.join(', ')}]<br><b>gyro</b> [${im.gyro.join(', ')}]<br>`+
   `<b>accel</b> [${im.accel.join(', ')}]`;
  document.getElementById('obs').innerHTML='<b>obs[13]</b> ['+d.obs.join(', ')+']';
  if(d.policy&&d.policy.length)bars(document.getElementById('joints'),d.policy);
  document.getElementById('diff').textContent=(d.diff_mae==null?'–':d.diff_mae);
  cmp(document.getElementById('cmp'),d.policy||[],d.expert||[]);
 }else{document.getElementById('imu').innerHTML='<span class=muted>waiting for IMU (/buddy/imu)…</span>';}
 }catch(e){}}
setInterval(tick,200);tick();
</script></body></html>"""


def main(args=None):
    rclpy.init(args=args)
    state = State()
    node = VerifyGui(state)
    port = node.get_parameter("port").value

    httpd = ThreadingHTTPServer(("0.0.0.0", port), make_handler(state))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    node.get_logger().info(f"Dashboard at http://0.0.0.0:{port}  (open from your browser)")

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
