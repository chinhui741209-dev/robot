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

## Architecture (Primary: C++ RT/SHM)

The primary control path uses C++ with Shared Memory for low-latency 1kHz control.

### Data Flow (C++ RT Path)

```
HAL (1kHz, C++, SHM)              Perception (15Hz, Python)
rt_cpp/hal_buddy                  camera_node.py
        │                           /perception/camera
        ▼                     ──►  perception_node.py
State Estimator (500Hz, C++, SHM)    └─ detection.onnx
rt_cpp/state_estimator
        │
        ▼
ROS2 Bridge (100Hz, C++, SHM → ROS2)
rt_cpp/ros2_bridge
        │
        ▼
Policy Node (50Hz, Python, ROS2)
policy/policy_node.py
  /policy/action
```

### Layers

| Layer | Frequency | Components | Path |
|-------|-----------|------------|------|
| HAL / RT Control | 1000 Hz | hal_buddy, state_estimator | `rt_cpp/` (C++ SHM) |
| Policy | 50 Hz | policy_node, robot_bridge_node | `policy/`, `robot_bridge/` |
| Perception | 15 Hz | camera_node, perception_node | `perception/` |

### Legacy Path (Python/LCM)

The legacy path (`hal_buddy_node.py` -> `state_estimator.py` via LCM) is kept for compatibility but deprecated.

## Key Commands

### Bring-up (Primary C++ RT)
```bash
./bringup/bringup_core.sh         # Check ROS 2, env, log dir
./bringup/bringup_control_cpp.sh  # C++ RT HAL + state estimator + ROS2 Bridge
./bringup/bringup_perception.sh   # Camera + detection
```

### Bring-up (Legacy Python/LCM)
```bash
./bringup/bringup_control.sh      # Deprecated
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

### Models (`models/active/`)

| File | Purpose | Input | Output | Budget |
|------|---------|-------|--------|--------|
| `simple_policy.onnx` | Locomotion MLP | (batch, 13): imu+gyro+accel+detection | (batch, 32): joint commands | <10ms |
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
