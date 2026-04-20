# Directory Structure v0.1

## 目錄結構

```
poc-orin/
├── bringup/              # Bring-up scripts (重構後)
│   ├── bringup_core.sh      # 核心系統 bring-up
│   ├── bringup_control.sh   # 控制和狀態 bring-up
│   ├── bringup_perception.sh # 感知 bring-up
│   ├── bringup_all.sh     # 完整 bring-up
│   ├── launch_mission.sh # Mission 啟動
│   ├── launch_demo.sh    # Demo 啟動
│   ├── run_smoke_test.sh # Smoke test
│   ├── run_e2e_test.sh # E2E test
│   └── recover_safe_mode.sh # 安全模式恢復
│
├── services/            # 服務化部署
│   ├── systemd/        # systemd service files
│   ├── runtime/        # Runtime services (inference, etc)
│   └── monitors/      # Health monitoring services
│
├── ros2_ws/            # ROS 2 workspace
│
├── models/             # 模型部署
│   ├── active/        # 正式模型 (.onnx, .trt)
│   ├── fallback/      # 備援模型
│   └── calibration/  # 校準參數
│
├── configs/            # 配置文件
│
├── logs/              # 日誌目錄
│
├── diagnostics/       # 診斷腳本
│
├── tests/             # 測試
│   ├── smoke/        # Smoke tests
│   ├── integration/  # Integration tests
│   ├── safety/      # Safety tests
│   └── regression/  # Regression tests
│
├── deploy/            # 部署腳本
│   ├── install.sh
│   ├── start.sh
│   ├── stop.sh
│   ├── restart.sh
│   └── rollback.sh
│
├── docs/              # 文件
│
├── hal/               # Hardware Abstraction Layer (原始)
│
├── middleware/        # Middleware (原始)
│
├── policy/            # Policy Node (原始)
│
├── rt_control/        # Real-time Control (原始)
│
└── scripts/           # POC Scripts (保留相容性)
```

## 使用說明

### Bring-up 流程

```bash
# 1. 核心系統 bring-up
./bringup/bringup_core.sh

# 2. 控制層 bring-up
./bringup/bringup_control.sh

# 3. 感知層 bring-up
./bringup/bringup_perception.sh

# 或一次完整 bring-up
./bringup/bringup_all.sh
```

### 測試流程

```bash
# Smoke test
./bringup/run_smoke_test.sh

# E2E test
./bringup/run_e2e_test.sh
```

### 部署流程

```bash
cd deploy
./install.sh
./start.sh
```