# Baseline Manifest v0.1

## 基本資訊

| 項目 | 值 |
|------|-----|
| Project | Robot POC (Orin Platform) |
| Version | v0.1 (Baseline) |
| Date | 2025-04-20 |
| Git Commit | 7804bfa |
| Git Repo | https://github.com/chinhui741209-dev/robot |

## 軟體版本總覽

### 系統層

| 項目 | 版本 | 備註 |
|------|------|------|
| OS | Ubuntu 22.04.5 LTS (Jammy Jellyfish) | |
| Kernel | 5.15.148-tegra | NVIDIA Jetson Linux |
| PREEMPT | PREEMPT (非 RT-PREEMPT) | 軟即時 |
| Architecture | aarch64 (ARMv8) | NVIDIA AGX Orin |
| Python | 3.10.12 | |
| GCC | 11.4.0 | |

### ROS 2 層

| 項目 | 版本 | 備註 |
|------|------|------|
| ROS 2 Distribution | Humble | |
| ROS 2 Package Count | 194 | ros-humble-* |
| Build System | ament_cmake | |
| Build Tool | colcon | |
| Python Client | rclpy | 已安裝 |

### ML/推理層

| 項目 | 版本 | 備註 |
|------|------|------|
| PyTorch | 未安裝 | 需安裝 |
| ONNX Runtime | 未安裝 | 需安裝 |
| TensorRT | 未安裝 | 需安裝 (JetPack) |
| NumPy | 1.26.4 | |
| Pandas | 1.3.5 | |

### 容器層

| 項目 | 版本 | 備註 |
|------|------|------|
| Docker | 29.1.5 | |
| Docker Compose | 2.x (plugin) | |
| K3s | 未安裝 | 需安裝 |
| Containerd | 2.x | |

## 目錄結構

```
poc-orin/
├── hal/                    # Hardware Abstraction Layer
│   ├── launch/            # ROS 2 launch files
│   ├── scripts/           # HAL nodes & scripts
│   └── src/              # ROS 2 packages
├── middleware/            # Middleware (recorder, etc)
├── policy/               # RL Policy Node
├── rt_control/           # Real-time Control (state estimator)
├── scripts/              # Demo & bring-up scripts
└── docs/                 # Documentation (本目錄)
```

## 已知問題

1. **RT Kernel 未安裝** - 僅有 PREEMPT，無 PREEMPT_RT
2. **ML 框架未安裝** - PyTorch, ONNX Runtime, TensorRT 需另行安裝
3. **K3s 未安裝** - 容器編排待部署
4. **高頻控制置於 ROS 2** - 1kHz/500Hz 控制迴路在 ROS 2 node 內
5. **模型全為模擬** - policy, perception 為 sim=True 假資料

## 待完成項目

- [ ] 安裝 RT Linux kernel (PREEMPT_RT)
- [ ] 安裝 PyTorch + ONNX Runtime
- [ ] 安裝 TensorRT (via JetPack)
- [ ] 安裝 K3s
- [ ] 重構運控架構 (RT thread 分離)
- [ ] 部署實際 ONNX 模型

## 驗收條件

- [x] Git repo 初始化完成
- [x] 代碼推送至 GitHub
- [ ] Baseline 文件建立完成 (本文件)
- [ ] Software BOM 建立完成
- [ ] Hardware Config 建立完成
