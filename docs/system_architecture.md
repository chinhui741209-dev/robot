# 系統架構圖 — Orin Robot System Architecture

**文件版本：** v1.1  
**建立日期：** 2026-05-04  
**修訂日期：** 2026-05-04 — 補充單向/雙向方向標示、修正 JointCommand 閉迴路  
**目標平台：** NVIDIA AGX Orin (aarch64) · Ubuntu 22.04.5 LTS · JetPack 6.1  
**部署位址：** `nvidia@192.168.99.73:/home/nvidia/poc/poc-orin/`

---

## 0. 方向標示說明

| 符號 | 意義 |
|------|------|
| `──►` | 單向資料流（發送方→接收方，接收方無回應） |
| `◄──►` | 雙向資料流（雙方互相讀寫，通常各自負責不同欄位） |
| `⇄` | 請求/回應（如 ROS2 Service：Client 發 Request，Server 返回 Response） |
| `↺` | In-process 函式呼叫（非 IPC，同進程內部輸入→輸出） |
| `- - ►` | 選用路徑 / 待啟用 / fallback |

---

## 1. 實體系統架構（含資料流方向）

```mermaid
graph TB
    subgraph HW["硬體層 (Physical Hardware)"]
        direction LR
        IMU_HW["IMU 感測器\n(SPI/CAN 介面)\n[Stub — 待接硬體]"]
        MOTORS["馬達驅動器 × 32\nJointCommand 介面\n[Stub — write() no-op]"]
        CAM_HW["USB 攝影機\n/dev/video0\n640×480 MJPG @ 15 Hz"]
    end

    subgraph OS["作業系統層"]
        KERNEL["Linux 5.15 (PREEMPT)\nJetPack 6.1"]
        POSIX_IPC["POSIX SHM /robot_shared_data\n~2.3 KB mmap\npthread_mutex (PROCESS_SHARED)"]
        SCHED["SCHED_FIFO\nhal_buddy: prio 80\nstate_est: prio 70"]
    end

    subgraph APP["應用層"]
        RT_BIN["C++ RT 二進位\nhal_buddy / state_estimator\nros2_bridge"]
        PY_NODES["Python ROS2 節點\npolicy_node / perception_node\ncamera_node"]
    end

    subgraph INFER["推理層 (↺ In-process)"]
        ONNX_CPU["ONNX Runtime CPU\npolicy + detection"]
        TRT["TensorRT 8.x\n(待 JetPack 完整安裝)"]
    end

    subgraph DEPLOY["部署層"]
        SYSTEMD["systemd\nrobot-core.service"]
        DOCKER["Docker Compose"]
        K3S["k3s / Kubernetes"]
    end

    IMU_HW -->|"► 單向 read()\nstatic stub data"| RT_BIN
    RT_BIN -->|"► 單向 write()\nJointCommand\n[no-op in stub]"| MOTORS
    CAM_HW -->|"► 單向 v4l2 frame\n900 KB @ 15 Hz"| PY_NODES

    RT_BIN <-->|"◄──► 雙向\nSHM 各進程讀寫不同欄位\n~2.3 KB / mutex 保護"| POSIX_IPC

    RT_BIN -->|"► 單向 ROS2 Publish\n(SHM → DDS bridge)"| PY_NODES
    PY_NODES -->|"► 單向 ROS2 Publish\n/policy/joint_commands"| RT_BIN

    PY_NODES -->|"↺ In-process 呼叫"| ONNX_CPU
    PY_NODES -.->|"↺ 優先 (待啟用)"| TRT

    KERNEL --> SCHED
    KERNEL --> POSIX_IPC
    SYSTEMD -->|"► ExecStart"| APP
    DOCKER -.->|"- - ► 可選"| APP
    K3S -.->|"- - ► 可選"| APP

    style HW fill:#fef3c7,stroke:#d97706
    style OS fill:#fee2e2,stroke:#dc2626
    style APP fill:#f0fdf4,stroke:#15803d
    style INFER fill:#fdf2f8,stroke:#be185d
    style DEPLOY fill:#f5f3ff,stroke:#7c3aed
```

---

## 2. 控制迴路頻率層次與資料方向

```mermaid
flowchart LR
    subgraph F1["1000 Hz — HAL (SCHED_FIFO prio 80)"]
        HAL["hal_buddy\nrt_cpp/src/hal_buddy.cpp\n▶ 寫: imu, joint_state, imu_counter\n◀ 讀: joint_cmd (q_des), watchdog_counter\n      estop_active, stop"]
    end

    subgraph F2["500 Hz — State Estimator (SCHED_FIFO prio 70)"]
        SE["state_estimator\n◀ 讀: imu, imu_counter\n▶ 寫: pose, pose_counter\nComplementary Filter + ZUPT"]
    end

    subgraph F3["100 Hz — ROS2 Bridge"]
        BRIDGE["ros2_bridge\n◀ 讀 SHM: imu, joint_state, pose\n▶ 寫 SHM: watchdog_counter++\n          joint_cmd.q_des (from policy)\n► 發布: /buddy/imu, /joint_states, /state/pose\n◀ 訂閱: /policy/joint_commands, /estop\n⇄ 服務: /estop_reset"]
    end

    subgraph F4["50 Hz — Policy"]
        POLICY["policy_node.py\n◀ 訂閱: /buddy/imu, /joint_states\n        /perception/objects\n↺ 推理: (1,13)→(1,32)\n► 發布: /policy/joint_commands"]
    end

    subgraph F5["15 Hz — Perception"]
        CAM["camera_node.py\n► 發布: /camera/image_raw"]
        PERC["perception_node.py\n◀ 訂閱: /camera/image_raw\n↺ 推理: (1,3,224,224)→(1,5)\n► 發布: /perception/objects"]
    end

    HAL <-->|"◄──► SHM\npthread_mutex"| SE
    SE <-->|"◄──► SHM\n(各讀寫不同欄位)"| BRIDGE
    BRIDGE -->|"► 單向 ROS2 Topics\n100 Hz"| POLICY
    CAM -->|"► 單向 ROS2\n15 Hz"| PERC
    PERC -->|"► 單向 ROS2\n15 Hz"| POLICY
    POLICY -->|"► 單向 /policy/joint_commands\n50 Hz"| BRIDGE

    style F1 fill:#fee2e2,stroke:#dc2626
    style F2 fill:#ffedd5,stroke:#ea580c
    style F3 fill:#fef9c3,stroke:#ca8a04
    style F4 fill:#dcfce7,stroke:#16a34a
    style F5 fill:#dbeafe,stroke:#3b82f6
```

> **閉迴路說明：** policy_node → `/policy/joint_commands` → ros2_bridge 訂閱 → `SHM.joint_cmd.q_des` → hal_buddy 讀取 → HardwareInterfaceStub::write()。這是完整的感知–推理–執行閉迴路（目前 stub 模式，write() 為 no-op）。

---

## 3. 安全機制架構（雙向監控）

```mermaid
graph TD
    subgraph WATCHDOG["雙向 Watchdog 監控"]
        WD1["hal_buddy\n▶ 寫 imu_counter @ 1kHz\n◀ 監控 watchdog_counter\n若 >100ms 無更新 → E-stop"]
        WD2["state_estimator\n◀ 監控 imu_counter\n若 >50ms 無更新 → E-stop"]
        BRIDGE_WD["ros2_bridge\n▶ 寫 watchdog_counter @ 100Hz\n(hal_buddy 心跳來源)"]
    end

    ESTOP["SHM.estop_active = true\n任何進程可設為 true\n只有 /estop_reset 可清除"]

    subgraph ACTIONS["E-stop 動作（單向執行）"]
        ACT["► hal_buddy 執行\ntau_ff[32] = 0\nkp[32] = 0\nkd[32] = 0\n命令不送出"]
    end

    subgraph RESET["重置路徑"]
        R1["► /estop (topic)\n單向觸發，無回應"]
        R2["⇄ /estop_reset (service)\n雙向 req/resp\nestop=false + counters reset\n返回 success + message"]
        R3["► /estop_reset (topic Bool)\n單向，backward compatible"]
    end

    WD1 -->|"► 觸發"| ESTOP
    WD2 -->|"► 觸發"| ESTOP
    BRIDGE_WD <-->|"◄──► 雙向監控關係\nbridge 寫，hal 讀"| WD1
    R1 -->|"► 單向"| ESTOP
    ESTOP --> ACT
    R2 <-->|"⇄ req/resp"| ESTOP
    R3 -->|"► 單向"| ESTOP

    style ESTOP fill:#fee2e2,stroke:#dc2626
    style ACT fill:#fee2e2,stroke:#dc2626
    style R2 fill:#dcfce7,stroke:#16a34a
```

---

## 4. 部署架構

| 方式 | 設定檔 | 資料流入口 | 自動重啟 |
|------|--------|----------|---------|
| **systemd** (主要) | `services/systemd/robot-core.service` | `bringup_all.sh` | `Restart=on-failure (10s)` |
| **Docker Compose** | `services/docker-compose/docker-compose.yml` | 各 service command | `restart: unless-stopped` |
| **k3s** | `services/k3s/deploy-*.yaml` | HAL + Policy Deployment | ReplicaSet |

---

## 5. 已知系統限制

| 項目 | 現狀 | 影響層 | 解法方向 |
|------|------|--------|---------|
| PREEMPT_RT 核心 | 僅 PREEMPT | HAL jitter 可能 >100μs | 安裝 RT patch 核心 |
| GPU 推理 | ONNX Runtime CPU | 推理延遲無 GPU 加速 | 完整 JetPack CUDA |
| TensorRT Python | `libnvdla` 缺失 | 無法用 Python TRT API | SDK Manager 完整安裝 |
| 硬體閉迴路 | HardwareInterfaceStub | write() 為 no-op | 替換為真實 SDK |
| sim=True | 全節點模擬模式 | 無實際馬達命令 | 逐節點切換 sim=False |
