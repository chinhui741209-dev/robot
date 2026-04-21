# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Target Platform

**NVIDIA AGX Orin** (aarch64) running Ubuntu 22.04.5 LTS + JetPack 6.1  
User: `nvidia@192.168.99.73`  
Deployment path on device: `/home/nvidia/poc/poc-orin/`

## Environment Setup (on Orin)

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export PYTHONPATH=$PYTHONPATH:/home/nvidia/poc/poc-orin
export POC_ROOT=/home/nvidia/poc/poc-orin
```

## Key Commands

### Bring-up (layered, run in order)
```bash
./bringup/bringup_core.sh        # Check ROS 2, env, log dir
./bringup/bringup_control.sh     # HAL + state estimator
./bringup/bringup_perception.sh  # Camera + detection
./bringup/bringup_all.sh         # All three in sequence
```

### Launch
```bash
./bringup/launch_demo.sh         # Demo mode
./bringup/launch_mission.sh      # Mission mode
./bringup/recover_safe_mode.sh   # Recovery after fault
```

### Testing
```bash
./bringup/run_smoke_test.sh      # Check ROS 2, Python, module presence
./bringup/run_e2e_test.sh        # Smoke + bringup_core flow
python3 scripts/test_demo_flow.py
```

### Models
```bash
python3 models/generate_simple_policy.py   # Regenerate policy ONNX
python3 models/generate_detection.py       # Regenerate detection ONNX
python3 models/test_inference.py           # Validate inference
./models/build_tensorrt.sh                 # Convert ONNX → TRT (requires full JetPack)
```

### Systemd service (on Orin)
```bash
sudo systemctl start robot-core
sudo systemctl status robot-core
sudo journalctl -u robot-core -f
```

## Architecture

### Data Flow

```
HAL (1kHz)                        Perception (15Hz)
hal_buddy_node.py                 camera_node.py
  /buddy/imu                        /perception/camera
  /buddy/motor_state          ──►  perception_node.py
  /buddy/hal/health                  └─ detection.onnx (ONNX Runtime CPU)
        │
        ▼
rt_control/state_estimator.py (500Hz)
  /state/pose, /tf
        │
        ▼
policy/policy_node.py (50Hz)         ◄── /buddy/imu
  /policy/action (Twist)
  /policy/action_chunk (Float32MultiArray)
  /policy/latency
        │
        ▼
robot_bridge/robot_bridge_node.py
        │
        ▼
middleware/recorder_node.py
  /recorder/status
```

Higher-level nodes: `planner/planner_node.py`, `task_parser/task_parser_node.py`  
GUI: `gui/scripts/demo_gui_tk.py` (Tkinter)

### Layers

| Layer | Frequency | Components |
|-------|-----------|------------|
| HAL / RT Control | 1000 Hz | hal_buddy_node, state_estimator |
| Policy | 50 Hz | policy_node, robot_bridge_node |
| Perception | 15 Hz | camera_node, perception_node |
| Orchestration | event-driven | planner_node, task_parser_node |

### Models (`models/active/`)

| File | Purpose | Input | Output | Budget |
|------|---------|-------|--------|--------|
| `simple_policy.onnx` | Locomotion MLP | (batch, 10): imu+joints | (batch, 6): linear+angular | <10ms |
| `detection.onnx` | Object detection CNN | (batch, 3, 224, 224) | (batch, 5): bbox+conf | <50ms |
| `detection_v2.onnx` | Detection (v2) | same | same | — |

Inference currently uses **ONNX Runtime CPU**. TensorRT path requires complete JetPack CUDA libraries (not yet available).

### Deployment Options

| Method | Path | Notes |
|--------|------|-------|
| systemd | `services/systemd/robot-core.service` | Auto-start on boot |
| Docker Compose | `services/docker-compose/` | Simple or full stack |
| k3s (Kubernetes) | `services/k3s/` | HAL + policy deployments |

### POC Scripts (legacy, kept for compatibility)

`scripts/start_w1.sh` through `start_w3.sh` and `demo_w1.sh`–`demo_w3.sh` are the original W1–W3 POC entrypoints. Prefer `bringup/` scripts for new work.

## Known Constraints

- **No RT kernel**: Running PREEMPT only, not PREEMPT_RT — high-frequency control is in ROS 2 nodes, not isolated RT threads
- **ONNX Runtime CPU only**: GPU inference blocked until full JetPack CUDA is installed via SDK Manager
- **TensorRT Python binding**: Missing `libnvdla` — `trtexec` CLI works but Python API does not
- **All nodes currently in sim mode** (`sim=True` parameter) — no physical hardware commands issued by default
