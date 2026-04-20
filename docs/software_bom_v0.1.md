# Software Bill of Materials (BOM) v0.1

## 系統依賴

### OS / Kernel

| Package | Version | Source | Purpose |
|---------|---------|--------|---------|
| Ubuntu | 22.04.5 LTS | Base | Operating System |
| linux-image-5.15.148-tegra | 5.15.148 | NVIDIA Jetson Linux | Kernel |
| gcc | 11.4.0 | apt | C Compiler |
| g++ | 11.4.0 | apt | C++ Compiler |
| python3 | 3.10.12 | apt | Python Runtime |
| python3-pip | - | apt | Python Package Manager |

### ROS 2 Humble (已安裝 194 packages)

| Package | Version | Purpose |
|---------|---------|---------|
| ros-humble-rclpy | 1.x | Python ROS 2 Client |
| ros-humble-rosidl-runtime-py | - | Message Generation |
| ros-humble-std-msgs | - | Standard Messages |
| ros-humble-sensor-msgs | - | Sensor Messages |
| ros-humble-geometry-msgs | - | Geometry Messages |
| ros-humble-launch | - | Launch System |
| ros-humble-launch-xml | - | XML Launch |
| ros-humble-launch-py | - | Python Launch |

### Python Packages (已安裝)

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | 1.26.4 | Numerical Computing |
| pandas | 1.3.5 | Data Analysis |
| rclpy | (ROS 2) | ROS 2 Python |
| colcon | - | Build Tool |

### Python Packages (需安裝)

| Package | Version | Purpose | Priority |
|---------|---------|---------|----------|
| torch | 2.x | ML Framework | P0 |
| onnx | 1.15+ | ONNX Format | P0 |
| onnxruntime-gpu | 1.17+ | ONNX Inference | P0 |
| tensorrt | (via JetPack) | NVIDIA Inference | P0 |
| pycuda | - | CUDA Python | P1 |
| pyserial | - | Serial Comm | P1 |
| can-utils | - | CAN Bus | P1 |

### 容器與編排

| Package | Version | Purpose | Status |
|---------|---------|---------|--------|
| docker | 29.1.5 | Container Runtime | ✅ |
| docker-compose | 2.x | Compose Tool | ✅ |
| containerd | 2.x | Container Manager | ✅ |
| k3s | - | K8s Light | ❌ 需安裝 |

### 系統工具

| Package | Version | Purpose |
|---------|---------|---------|
| git | - | Version Control |
| curl | - | HTTP Client |
| wget | - | Download Tool |
| tmux | - | Terminal Multiplexer |
| htop | - | Process Monitor |
| iotop | - | I/O Monitor |
| strace | - | System Trace |
| latencytop | - | Latency Analysis |

## 環境變數

```bash
# ROS 2
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42

# Python
export PYTHONPATH=$PYTHONPATH:~/poc/poc-orin

# Workspace
export POC_ROOT=~/poc/poc-orin
```

## 依賴安裝順序

```bash
# 1. 系統依賴
sudo apt update
sudo apt install -y python3-pip git curl wget

# 2. ROS 2 (已安裝)
source /opt/ros/humble/setup.bash

# 3. ML Framework
pip3 install torch onnx onnxruntime-gpu

# 4. 容器 (Docker 已安裝)
# K3s 需另行安裝
```

## 驗證指令

```bash
# OS
cat /etc/os-release

# Kernel
uname -a

# Python
python3 --version

# ROS 2
source /opt/ros/humble/setup.bash
ros2 pkg list | wc -l

# Docker
docker --version

# GPU
tegrastats
```
