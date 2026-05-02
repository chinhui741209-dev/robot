# Software Environment & Development Handover Specification
# 軟體環境與開發接手交付規格

**文件版本**：v1.3.0　｜　**日期**：2026-05-02　｜　**平台**：NVIDIA AGX Orin (aarch64)

> 本文件依據 PDF 10 層平台化架構優化，涵蓋 C++ RT 控制層、32-DOF 關節支援、共享記憶體 (SHM) 以及 TensorRT GPU 加速規格。

---

## 0. 文件資訊

| 項目 | 內容 |
|------|------|
| 專案名稱 | Robot POC — Vision-Language-Action (VLA) 機械臂操控系統 |
| 目前階段 | Phase 3: Hardware-Ready & AI Acceleration |
| 對應軟體 Release Tag | v0.3 |
| 更新日期 | 2026-05-02 |

---

## 1. 環境總覽 (v1.3 Updated)

| 項目 | 內容 | 備註 |
|------|-----------|------|
| 目標平台 | NVIDIA AGX Orin Developer Kit | IP: 192.168.99.73 |
| 是否使用 PREEMPT_RT | **建議為是** | C++ RT 模組已支援 `SCHED_FIFO` |
| 即時通訊機制 | **POSIX Shared Memory (SHM)** | 取代 L3/L4 的 LCM 通訊，極低延遲 |
| AI 推理引擎 | **TensorRT 10.x (GPU)** | 支援 FP16 加速，大幅降低感知延遲 |

---

## 6. 通訊架構 (v1.3 Optimized)

| 通訊類型 | 用途 | 實作方式 | 頻率 | 備註 |
|---------|------|---------|------------|------|
| **Shared Memory** | **HAL ↔ RT Control 核心通道** | POSIX SHM + Mutex | 1000 Hz | **32-DOF 關節支援** |
| ROS 2 / DDS | 感知、規劃、UI 層主幹通訊 | CycloneDDS | 1–100 Hz | |
| **Joint States** | **全機關節狀態發布** | `/joint_states` | 100 Hz | 標準 ROS 2 JointState |

---

## 7. RT 任務與頻率 (32-DOF 版)

| 模組 / 任務 | 頻率 | Priority (SCHED_FIFO) | 通訊方式 | 備註 |
|------------|------|---------|---------|------|
| **hal_buddy (C++)** | 1000 Hz | **80** | SHM Write | 模擬 32x 關節狀態 |
| **state_estimator (C++)** | 500 Hz | **70** | SHM Read/Write | 整合 50ms Watchdog |
| **ros2_bridge (C++)** | 100 Hz | Default | SHM Read / ROS2 Pub | 橋接至 `/joint_states` |

---

## 13. 安全與故障處理 (Phase 4)

| 故障類型 | 偵測條件 | 反應策略 | 恢復條件 |
|---------|---------|---------|---------|
| **RT Heartbeat Lost** | `hal_buddy` 停止更新資料 > 50ms | `state_estimator` 觸發 **WATCHDOG** | 重啟 HAL 且手動清除 `estop_active` |
| **Emergency Stop** | `estop_active` 旗標被設為 true | 立即停止所有積分運算與馬達指令輸出 | 人工確認安全後重置 SHM |

---

## 20. Model / ONNX / TensorRT Deployment Spec (v1.3)

| Model | Version | Backend (Preferred) | Latency Target (Orin GPU) | Fallback |
|-------|---------|---------------------|---------------------------|----------|
| **Detection** | v2.0 | **TensorRT (.engine)** | **< 10 ms** | ONNX Runtime CPU |
| **Locomotion Policy** | v1.0 | **TensorRT (.engine)** | **< 2 ms** | ONNX Runtime CPU |

### AI 優化管線：
1. **轉換**：使用 `models/build_tensorrt.sh` 產生針對 Orin GPU 優化的 Engine。
2. **推論封裝**：透過 `perception/trt_inference.py` 進行非同步推論管理。

---

## 16. Source Code 交付範圍 (v1.3)

| 模組 | 語言 | 形式 | 職責 |
|-----------|---------|---------|------|
| **robot_rt_cpp** | C++17 | Source | **SHM RT 核心、Watchdog、ROS2 Bridge** |
| **perception** | Python | Source | 支援 TensorRT/ONNX 雙模推論 |
| **policy** | Python | Source | 策略推論 (支援 ROS2/LCM/TensorRT) |
| **models** | Shell/ONNX | Scripts | 模型轉換與管理工具 |

---

*本文件由 Gemini CLI 根據 Sync-Doc 技能規範自動更新，版本 v1.3.0，日期 2026-05-02*
