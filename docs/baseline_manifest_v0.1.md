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
| PyTorch | 2.11.0+cpu | ✅ |
| ONNX | 1.21.0 | ✅ |
| ONNX Runtime | 1.23.2 (CPU) | ✅ |
| TensorRT | 10.3.0 | ✅ (CLI) |
| OpenCV | 4.13.0 | ✅ |
| NumPy | 1.26.4 | ✅ |
| Pandas | 1.3.5 | ✅ |

### 感知層

| 項目 | 版本 | 備註 |
|------|------|------|
| USB Camera | /dev/video0 | ✅ |
| Camera Node | v0.1 | ✅ |
| Detection Model | detection.onnx | ✅ |
| Visualization | v0.1 | ✅ |

### 容器層

| 項目 | 版本 | 備註 |
|------|------|------|
| Docker | 29.1.5 | ✅ |
| Docker Compose | 5.0.1 | ✅ |
| K3s | 1.34.6 | ✅ 已安裝 |
| Containerd | 2.x | ✅ |

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

1. **RT Kernel 未安裝** - 僅有 PREEMPT，無 PREEMPT_RT (future)
2. **TensorRT Python binding** - 缺少 libnvdla library (future)
3. **ONNX Runtime GPU** - 使用 CPU 版本 (future)
4. **USB Camera 驅動** - 已驗證可用
5. **高頻控制置於 ROS 2** - 需重構 (future)

## 待完成項目 (Future)

- [ ] 安裝 RT Linux kernel (PREEMPT_RT)
- [ ] 重構運控架構 (RT thread 分離)
- [ ] 優化 detection model
- [ ] 整合 policy action

## 當前可用功能 (v0.2)

- [x] Git 版本控制
- [x] K3s 容器編排
- [x] USB Camera ROS 2 node
- [x] ONNX Object Detection
- [x] Bring-up scripts
- [x] Docker Compose

## 驗收條件

- [x] Git repo 初始化完成
- [x] 代碼推送至 GitHub
- [ ] Baseline 文件建立完成 (本文件)
- [ ] Software BOM 建立完成
- [ ] Hardware Config 建立完成
