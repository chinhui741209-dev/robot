#!/usr/bin/env python3
"""
demo_show — one-command demo launcher (演出啟動器).

Runs the robot demo program act-by-act with narration. Acts map to the NVIDIA
"three AIs" story, escalating from fully-offline-and-reliable to API-headline:

  0  背景幕      Web dashboard (camera + telemetry)            OFFLINE
  1  感知        ONNX 4-class -> Claude open-vocabulary         1a OFFLINE / 1b API
  2  學習的身體  BC policy vs random (eval_policy)              OFFLINE
  3  規模化評估  scenario-sweep across regimes (eval_suite)     OFFLINE
  4  Agentic加速 agentic_train: gen->train->eval coverage       OFFLINE
  5  VLA/3D閉環  language -> see 3D -> reachability -> COMPLETED 5a OFFLINE / 5b API
  6  整合 E2E    full stack (launch_demo / w3)                  OFFLINE / API
  7  互動工作室  camera + open-vocab lock + 3D arm + motor HUD   API (點選/離線備援)

Usage (run AFTER `source /opt/ros/humble/setup.bash` for the ROS acts):
    python3 scripts/demo_show.py --act 5
    python3 scripts/demo_show.py --acts 2,3,4
    python3 scripts/demo_show.py --act 1 --api
    ANTHROPIC_API_KEY=sk-ant-... python3 scripts/demo_show.py --act 5 --api

The default ROS_DOMAIN_ID is 88 (isolated from the live robot-core on 42).
Every API act degrades gracefully to its OFFLINE counterpart when no usable
ANTHROPIC_API_KEY is present.
"""

import argparse
import glob
import os
import signal
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIVE_ONNX = "models/active/simple_policy.onnx"


# ----------------------------------------------------------------------------
# presentation helpers
# ----------------------------------------------------------------------------

def banner(act, title, story, expect):
    line = "=" * 72
    print(f"\n{line}\n  ACT {act} — {title}\n{line}")
    print(f"  ▶ 講什麼：{story}")
    print(f"  ▶ 預期  ：{expect}\n{line}", flush=True)


def note(msg):
    print(f"  ‹demo› {msg}", flush=True)


def child_env(domain):
    e = dict(os.environ)
    e["PYTHONPATH"] = REPO + os.pathsep + e.get("PYTHONPATH", "")
    e["ROS_DOMAIN_ID"] = str(domain)
    e.setdefault("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp")
    return e


def run(argv, env=None):
    """Run a subprocess to completion, streaming its output."""
    note("$ " + " ".join(argv))
    return subprocess.run(argv, cwd=REPO, env=env or dict(os.environ)).returncode


def has_api_key():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or
                os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def find_pt():
    """Locate a trained torch checkpoint for the eval_policy headline (164x)."""
    for c in ("models/candidate/simple_policy_bc.pt",
              "models/candidate/simple_policy_agentic.pt"):
        if os.path.exists(os.path.join(REPO, c)):
            return c
    pts = sorted(glob.glob(os.path.join(REPO, "models/candidate/*.pt")))
    if pts:
        return os.path.relpath(pts[0], REPO)
    return None


# ----------------------------------------------------------------------------
# blocking node-stack launcher (for the live ROS acts)
# ----------------------------------------------------------------------------

def run_stack(procs, env, banner_url=None):
    """Spawn a set of [argv,...] node processes, stream, block until Ctrl-C."""
    children = []
    try:
        for argv in procs:
            note("spawn: " + " ".join(argv))
            children.append(subprocess.Popen(argv, cwd=REPO, env=env))
        if banner_url:
            print("\n" + "=" * 72)
            print(f"  {banner_url}")
            print("  (Ctrl-C 結束本 act)")
            print("=" * 72, flush=True)
        while True:
            time.sleep(1.0)
            for c in children:
                if c.poll() is not None:
                    note(f"a node exited (rc={c.returncode}); stopping stack")
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        note("收工：停止節點…")
    finally:
        for c in children:
            try:
                c.send_signal(signal.SIGINT)
            except Exception:
                pass
        time.sleep(1.0)
        for c in children:
            try:
                c.terminate()
            except Exception:
                pass


# ----------------------------------------------------------------------------
# acts
# ----------------------------------------------------------------------------

def act0(args):
    banner(0, "背景幕：感知 + 狀態儀表板", "Physical AI 的即時感知與狀態，作為整場演出的視覺背景。",
           f"瀏覽器開 http://{args.orin_ip}:{args.port} 看到相機影像、偵測框、IMU、32 關節動作。")
    env = child_env(args.domain)
    env["CAMERA"] = "ros"
    env["DEVICE"] = str(args.device)
    env["PORT"] = str(args.port)
    note("啟動 verify 儀表板（相機 + ONNX 感知 + GUI）…")
    run(["bash", "bringup/bringup_verify.sh"], env=env)  # has its own cleanup trap


def act1(args):
    use_api = args.api and has_api_key()
    if args.api and not use_api:
        note("⚠ 無 ANTHROPIC_API_KEY → 退回離線 ONNX 感知。")
    backend = "api" if use_api else "onnx"
    banner(1, f"感知：封閉 → 開放詞彙（backend={backend}）",
           "ONNX YOLOv8 只認訓練過的 4 類；Claude Vision 可開放詞彙偵測任意物體。",
           "離線：偵到 pen/box/apple/orange；API：鏡頭擺任意物（馬克杯/鑰匙）也被框出。")
    env = child_env(args.domain)
    procs = [
        ["python3", "perception/scripts/camera_node.py", "--ros-args",
         "-p", f"device:=/dev/video{args.device}"],
        ["python3", "perception/scripts/perception_node.py", "--ros-args",
         "-p", f"backend:={backend}"],
        ["python3", "gui/verify_web_gui.py", "--ros-args",
         "-p", "camera:=ros", "-p", f"device:={args.device}", "-p", f"port:={args.port}"],
    ]
    run_stack(procs, env, banner_url=f"開放詞彙感知儀表板：http://{args.orin_ip}:{args.port}")


def act2(args):
    pt = find_pt()
    banner(2, "學習的身體（Behavior Cloning）",
           "locomotion 策略不是隨機初始化，而是模仿 ScriptedExpert 學出來的。",
           "trained 的 action-MSE 遠低於 random（約 164×），yaw 轉向一致率高。")
    if pt:
        run([sys.executable, "scripts/eval_policy.py", "--model", pt], env=child_env(args.domain))
    else:
        note("找不到 trained .pt（候選為 gitignored）→ 改用 active ONNX 跑規模化評估（無 random 基準）。")
        run([sys.executable, "scripts/eval_suite.py", "--model", ACTIVE_ONNX, "--steps", "2000"],
            env=child_env(args.domain))


def act3(args):
    pt = find_pt()
    model = pt or ACTIVE_ONNX
    banner(3, "規模化評估（軟體版 Cosmos）",
           "不靠單一平均分數唬人 —— 在 6 種情境（calm/aggressive/noisy/flaky/offset…）掃描穩健度。",
           "印出逐情境 action-MSE 與 best/mean/worst" + ("（含 PASS 判定）" if pt else "（ONNX：無基準）") + "。")
    if not pt:
        note("無 trained .pt → 用 active ONNX（無 PASS 基準，仍展示跨情境分佈）。")
    run([sys.executable, "scripts/eval_suite.py", "--model", model, "--steps", "2000"],
        env=child_env(args.domain))


def act4(args):
    banner(4, "Agentic 加速器（招牌論點）",
           "Agentic AI 當 Physical AI 的加速器：自動 生成多樣情境 → 訓練 → 規模化評估 → 找覆蓋缺口。",
           "印出覆蓋報告：trained 跨情境表現 + held-out 標記 + worst 情境（= 下一輪要補的缺口）。")
    if args.agentic:
        note("『agentic』模式：請在 Claude 對話請我執行 train-policy skill（用 Workflow 編排 fan-out + critic loop）。")
        note("本腳本先跑確定性版本作為現場可見的 baseline：")
    run([sys.executable, "scripts/agentic_train.py",
         "--train-scenarios", args.train_scenarios,
         "--steps-per", str(args.steps_per), "--epochs", str(args.epochs),
         "--eval-steps", "1500", "--out", "models/candidate", "--tag", "demo"],
        env=child_env(args.domain))


def act5(args):
    use_api = args.api and has_api_key()
    if args.api and not use_api:
        note("⚠ 無 ANTHROPIC_API_KEY → 退回離線 rule + 3D 閉環（5a）。")
    if use_api:
        act5b(args)
    else:
        act5a(args)


def act5a(args):
    banner("5a", "語言×視覺×3D 閉環（rule 離線）",
           "NL「把筆放進盒子」→ 規劃 → planner 卡在 grasp 直到筆『存在且進入 ~1.5m』→ 盒子出現 → 完成。",
           "看到 planner 因 reach:pen 延後 grasp（pen FAR），t≈2s 進入可達後前進，最後 state=COMPLETED。")
    run([sys.executable, "scripts/test_closed_loop.py"], env=child_env(args.domain))


def act5b(args):
    banner("5b", "VLA 大腦（Claude 語言+視覺+3D）",
           "口說/輸入指令 → Claude VLA 大腦看相機與 3D 場景 → 產生考量空間可達性的任務計畫。",
           "/task/parsed_command 出現結構化計畫；planner 依 3D 可達性閉環執行。")
    env = child_env(args.domain)
    procs = [
        ["python3", "perception/scripts/camera_node.py", "--ros-args",
         "-p", f"device:=/dev/video{args.device}"],
        ["python3", "perception/scripts/perception_node.py", "--ros-args", "-p", "backend:=onnx"],
        ["python3", "world_model/scripts/world_model_node.py"],
        ["python3", "policy/vla_inference_node.py", "--ros-args", "-p", "backend:=api"],
        ["python3", "planner/scripts/planner_node.py"],
    ]
    note("節點起好後，在另一個（已 source ROS、ROS_DOMAIN_ID=%d）終端發指令：" % args.domain)
    note("  ros2 topic pub --once /ui/user_command std_msgs/msg/String \"data: '把筆放進盒子'\"")
    note("  ros2 topic echo /task/parsed_command   # 看 Claude VLA 出的計畫")
    run_stack(procs, env, banner_url="VLA/3D 大腦管線執行中（API）")


def act6(args):
    use_api = args.api and has_api_key()
    if args.api and not use_api:
        note("⚠ 無 ANTHROPIC_API_KEY → 整合 E2E 以 mock 後端執行。")
    banner(6, "整合 E2E（全棧）",
           "感知 → 世界模型 → 規劃 → 雙腦仲裁 → 動作，全節點同時運轉。",
           "完整系統 live；遙測在儀表板可見。" + ("（VLA 走 API）" if use_api else "（mock 後端）"))
    env = child_env(args.domain)
    if use_api:
        run_stack([["python3", "scripts/w3_launch.py", "--ros-args", "-p", "backend:=api"]],
                  env, banner_url="整合 E2E（API VLA）執行中")
    else:
        note("啟動 bringup/launch_demo.sh（mock E2E）…")
        run(["bash", "bringup/launch_demo.sh"], env=env)


def act7(args):
    banner(7, "互動工作室（相機+開放詞彙鎖定+3D G1 7軸臂&Dex2/5靈巧手+馬達遙測）",
           "說/打「幫我拿起桌上的滑鼠」→ 相機鎖定該物 → 3D G1 7軸臂+Dex2/5 靈巧手抓取 → 逐馬達即時參數。",
           f"瀏覽器開 http://{args.orin_ip}:{args.studio_port}：影像鎖定框 + 3D 動畫 + 17 馬達遙測。")
    note("鎖定三層：開放詞彙 API（有額度）→ 本地 ONNX(pen/box/apple/orange) → 點畫面手動鎖定。")
    note("零額度也能演：拿蘋果/筆當道具走本地 ONNX 自動鎖定；任意物體點畫面。")
    note("提醒：本 act 用相機 /dev/video1，請先 `sudo systemctl stop robot-core` 釋放相機。")
    cam = "device" if args.device >= 0 else "none"
    run_stack([["python3", "gui/demo_studio.py",
                "--camera", cam, "--device", str(args.device),
                "--port", str(args.studio_port)]],
              child_env(args.domain),
              banner_url=f"互動工作室：http://{args.orin_ip}:{args.studio_port}")


ACTS = {0: act0, 1: act1, 2: act2, 3: act3, 4: act4, 5: act5, 6: act6, 7: act7}


def main():
    ap = argparse.ArgumentParser(description="robot demo show launcher")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--act", type=int, choices=sorted(ACTS), help="run a single act")
    g.add_argument("--acts", help="comma list, e.g. 2,3,4")
    ap.add_argument("--api", action="store_true", help="use Claude API for API-capable acts")
    ap.add_argument("--agentic", action="store_true", help="Act4: note the Workflow agentic loop")
    ap.add_argument("--domain", type=int, default=88, help="ROS_DOMAIN_ID (isolated from live=42)")
    ap.add_argument("--orin-ip", default="<orin-ip>", help="IP shown in dashboard URLs")
    ap.add_argument("--device", type=int, default=1, help="camera /dev/videoN (<0 = no camera)")
    ap.add_argument("--port", type=int, default=8088, help="dashboard port")
    ap.add_argument("--studio-port", type=int, default=8090, help="Act 7 studio port")
    # Act4 sizing (kept modest for a live run; raise for a real candidate).
    ap.add_argument("--train-scenarios", default="calm,nominal,aggressive,offset_target")
    ap.add_argument("--steps-per", type=int, default=3000)
    ap.add_argument("--epochs", type=int, default=20)
    args = ap.parse_args()

    if args.acts:
        seq = [int(x) for x in args.acts.split(",") if x.strip()]
    else:
        seq = [args.act]

    if args.api and not has_api_key():
        note("⚠ --api 指定但未偵測到 ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN；API acts 將自動退回離線。")

    for a in seq:
        ACTS[a](args)
    print("\n✅ demo show 結束。")


if __name__ == "__main__":
    main()
