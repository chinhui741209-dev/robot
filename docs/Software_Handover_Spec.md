# Software Environment & Development Handover Specification
# 軟體環境與開發接手交付規格

**文件版本**：v1.1.0　｜　**日期**：2026-05-02　｜　**平台**：NVIDIA AGX Orin (aarch64)

> 本文件依據 PDF 10 層平台化架構優化，新增 C++ RT 控制層與共享記憶體 (SHM) 規格。

---

## 0. 文件資訊

| 項目 | 內容 |
|------|------|
| 專案名稱 | Robot POC — Vision-Language-Action (VLA) 機械臂操控系統 |
| 文件版本 | v1.1.0 (Optimization) |
| 對應軟體 Release Tag | v0.2 |
| 更新日期 | 2026-05-02 |

---

## 1. 環境總覽 (Updated)

| 項目 | 內容 | 備註 |
|------|-----------|------|
| 是否使用 PREEMPT_RT | **建議為是** | C++ RT 模組已支援 `SCHED_FIFO` |
| 即時通訊機制 | **POSIX Shared Memory (SHM)** | 取代原本 L3/L4 的 LCM 通訊 |

---

## 6. 通訊架構 (v1.1 Optimized)

| 通訊類型 | 用途 | 實作方式 | 頻率 | 備註 |
|---------|------|---------|------------|------|
| **Shared Memory** | **HAL ↔ RT Control 核心通道** | POSIX SHM + Mutex | 1000 Hz | **v0.2 新增，極低延遲** |
| ROS 2 / DDS | 感知、規劃、UI 層主幹通訊 | CycloneDDS | 1–100 Hz | |
| ROS 2 Bridge | SHM 資料橋接至 ROS 2 | `robot_rt_cpp/ros2_bridge` | 100 Hz | C++ 實作 |
| LCM | 舊有相容通道 | `lcm_types/` | 1000 Hz | 僅作為監控備援 |

---

## 7. RT 任務與頻率 (C++ 重構版)

| 模組 / 任務 | 頻率 | Priority (SCHED_FIFO) | 通訊方式 | 備註 |
|------------|------|---------|---------|------|
| **hal_buddy (C++)** | 1000 Hz | **80** | SHM Write | L3 Layer |
| **state_estimator (C++)** | 500 Hz | **70** | SHM Read/Write | L4 Layer |
| ros2_bridge (C++) | 100 Hz | Default | SHM Read / ROS2 Pub | Bridge Layer |
| Policy Node (Py) | 50 Hz | Default | ROS2 Sub / Pub | L5 Layer |

---

## 8. HAL 與 Driver (Updated)

| 項目 | Interface / Driver 名稱 | 是否白盒 | 備註 |
|------|------------------------|---------|------|
| **RT HAL (C++)** | `robot_rt_cpp/hal_buddy` | 白盒 | 基於 SHM 的高頻抽象 |
| Motor Driver | `robot_control_cpp/` | 白盒 | C++ 實作，介接 Unitree SDK |

---

## 16. Source Code 交付範圍 (v1.1)

| 模組 | 語言 | Build 方式 | 職責 |
|-----------|---------|-----------|------|
| **robot_rt_cpp** | C++17 | `colcon build` | **SHM RT 核心、HAL、Bridge** |
| robot_control_cpp | C++17 | `colcon build` | 馬達控制介接 |
| policy | Python | N/A | 策略推論 (支援 ROS2 IMU) |
| middleware | Python | N/A | 舊有 LCM 橋接與錄製器 |

---

*本文件由 Gemini CLI 根據 Sync-Doc 技能規範自動更新，版本 v1.1.0，日期 2026-05-02*
