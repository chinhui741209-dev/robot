# 軟體架構圖 — Orin Robot Software Architecture

**文件版本：** v1.1  
**建立日期：** 2026-05-04  
**修訂日期：** 2026-05-04 — 補充單向/雙向方向標示、補上 JointCommand 閉迴路  
**ROS 版本：** ROS 2 Humble Hawksbill  
**語言：** C++17 (RT 層) / Python 3.10 (策略、感知層)

---

## 0. 方向標示說明

| 符號 | 類型 | 範例 |
|------|------|------|
| `──►` | **單向**（Pub/Sub Topic） | `/buddy/imu`、`/camera/image_raw` |
| `◄──►` | **雙向**（各讀寫不同欄位） | SHM 各進程、Watchdog 計數器 |
| `⇄` | **請求/回應**（ROS2 Service） | `/estop_reset` Trigger |
| `↺` | **In-process 呼叫**（非 IPC） | ONNX Runtime、TensorRT |
| `- - ►` | **選用/fallback/待啟用** | TRT 路徑、LCM legacy |

---

## 1. 軟體模組全覽（含介面方向）

```mermaid
graph TD
    subgraph RTCpp["rt_cpp — C++ 即時控制 (robot_rt_cpp v0.1.0)"]
        direction LR
        HAL_CPP["hal_buddy\n▶ 寫 SHM: imu, joint_state, imu_counter\n◀ 讀 SHM: joint_cmd, watchdog_counter,\n          estop_active, stop\n► HW stub write()"]
        SE_CPP["state_estimator\n◀ 讀 SHM: imu, imu_counter\n▶ 寫 SHM: pose, pose_counter\n          estop_active (watchdog)"]
        BRIDGE_CPP["ros2_bridge\n◀ 讀 SHM: imu, joint_state, pose\n▶ 寫 SHM: watchdog_counter, joint_cmd\n► 發布 ROS2 Topics\n◀ 訂閱: /policy/joint_commands, /estop\n⇄ /estop_reset service"]
        SHM_HPP["shared_memory.hpp\nPOSIX SHM ~2.3 KB\ninterface header"]
    end

    subgraph PolicyPy["policy — 策略推理"]
        POL_NODE["policy_node.py\n◀ 訂閱: /buddy/imu,\n        /joint_states,\n        /perception/objects\n↺ ONNX/TRT 推理\n► /policy/joint_commands"]
    end

    subgraph PerceptionPy["perception — 視覺感知"]
        CAM_NODE["camera_node.py\n► /camera/image_raw"]
        PERC_NODE["perception_node.py\n◀ /camera/image_raw\n↺ ONNX/TRT 推理\n► /perception/objects"]
        TRT_INF["trt_inference.py\n↺ CUDA async pipeline\nH2D → inference → D2H"]
    end

    subgraph HALPy["hal — Python HAL ⚠ Deprecated"]
        HAL_PY["hal_buddy_node.py\nLCM Pub (1kHz)\n⚠ DEPRECATED — 啟動時顯示警告"]
    end

    subgraph Middleware["middleware — 資料橋接"]
        LCM_BRIDGE["lcm_ros2_bridge.py\n◀ LCM Subscribe\n► ROS2 Publish\nDecimation: 1kHz→100Hz"]
        RECORDER["recorder_node.py\n◀ 訂閱多個 Topics\n▶ 寫入 MCAP bag"]
    end

    subgraph Models["models — 推理模型"]
        POL_ONNX["simple_policy.onnx\n(1,13)→(1,32) MLP Tanh\n12.9 KB"]
        DET_ONNX["detection_v2.onnx\n(1,3,224,224)→(1,5) CNN\n~12 MB"]
        DET_V1["detection.onnx\n~18 KB (fallback)"]
    end

    SHM_HPP --- HAL_CPP
    SHM_HPP --- SE_CPP
    SHM_HPP --- BRIDGE_CPP

    HAL_CPP <-->|"◄──► SHM 雙向"| SE_CPP
    SE_CPP <-->|"◄──► SHM 雙向"| BRIDGE_CPP
    HAL_CPP <-->|"◄──► SHM 雙向"| BRIDGE_CPP

    BRIDGE_CPP -->|"► 單向 ROS2 Pub"| POL_NODE
    POL_NODE -->|"► 單向 /policy/joint_commands"| BRIDGE_CPP

    CAM_NODE -->|"► 單向"| PERC_NODE
    PERC_NODE -->|"► 單向"| POL_NODE
    TRT_INF -->|"↺ 被呼叫"| PERC_NODE
    TRT_INF -->|"↺ 被呼叫"| POL_NODE

    POL_ONNX -->|"↺"| POL_NODE
    DET_ONNX -->|"↺"| PERC_NODE
    DET_V1 -.->|"↺ fallback"| PERC_NODE

    HAL_PY -.->|"- - ► LCM Pub (deprecated)"| LCM_BRIDGE
    LCM_BRIDGE -.->|"- - ► ROS2 Pub (deprecated)"| POL_NODE

    style RTCpp fill:#fee2e2,stroke:#dc2626
    style PolicyPy fill:#dcfce7,stroke:#16a34a
    style PerceptionPy fill:#dbeafe,stroke:#3b82f6
    style HALPy fill:#f1f5f9,stroke:#94a3b8
    style Middleware fill:#fef9c3,stroke:#ca8a04
    style Models fill:#f0fdf4,stroke:#15803d
```

---

## 2. C++ SHM 介面詳細設計（讀寫擁有者）

```mermaid
classDiagram
    class RobotSharedData {
        +pthread_mutex_t mutex [40B, 共用]
        +BuddyImu imu [88B, HAL寫]
        +JointState joint_state [768B, HAL寫]
        +JointCommand joint_cmd [1280B, Bridge寫←policy]
        +StatePose pose [64B, SE寫]
        +bool stop [HAL寫]
        +bool estop_active [多進程讀寫]
        +uint64_t watchdog_counter [Bridge遞增, HAL監控]
        +uint64_t imu_counter [HAL遞增, SE監控]
        +uint64_t pose_counter [SE遞增]
        <<SHM /robot_shared_data ~2.3 KB>>
    }

    class BuddyImu {
        +int64_t timestamp [μs, steady_clock]
        +double orientation[4] [x,y,z,w 歸一化]
        +double angular_velocity[3] [rad/s]
        +double linear_acceleration[3] [m/s² 含重力]
        <<88 bytes, HAL寫入>>
    }

    class JointState {
        +double position[32] [rad]
        +double velocity[32] [rad/s]
        +double effort[32] [Nm]
        <<768 bytes, HAL寫入>>
    }

    class JointCommand {
        +double q_des[32] [rad, Bridge←policy寫入]
        +double dq_des[32] [rad/s]
        +double kp[32] [Nm/rad]
        +double kd[32] [Nm·s/rad]
        +double tau_ff[32] [Nm]
        <<1280 bytes, Bridge寫/HAL讀>>
    }

    class StatePose {
        +int64_t timestamp [μs]
        +double position[3] [m]
        +double orientation[4] [x,y,z,w]
        <<64 bytes, SE寫入>>
    }

    RobotSharedData *-- BuddyImu
    RobotSharedData *-- JointState
    RobotSharedData *-- JointCommand
    RobotSharedData *-- StatePose
```

---

## 3. JointCommand 閉迴路（已修復）

```mermaid
flowchart LR
    POL["policy_node\n50 Hz\n↺ ONNX推理\n(1,13)→(1,32)"]
    TOPIC["► /policy/joint_commands\nFloat32MultiArray[32]\n單向 Topic @ 50 Hz"]
    BRIDGE["ros2_bridge\n◀ 訂閱並接收"]
    SHM_CMD["SHM.joint_cmd.q_des[32]\n◄──► bridge寫 / HAL讀"]
    HAL["hal_buddy\n◀ 讀 joint_cmd\n@1kHz"]
    HW["HardwareInterfaceStub\n.write(joint_cmd)\n[stub: no-op]"]

    POL -->|"► 單向 Publish"| TOPIC
    TOPIC -->|"► 單向 Subscribe callback"| BRIDGE
    BRIDGE -->|"▶ mutex lock 寫入\nq_des[0..31]\nestop guard"| SHM_CMD
    SHM_CMD -->|"◀ mutex lock 讀取"| HAL
    HAL -->|"► 單向\n(stub no-op)"| HW

    style SHM_CMD fill:#dcfce7,stroke:#16a34a
    style HW fill:#fef9c3,stroke:#ca8a04
```

**安全保護：**
- `estop_active == true` 時，`joint_cmd_callback` 直接 return，**不更新 joint_cmd**
- 收到 data.size() < 32 時，WARN_ONCE 並忽略，**不做部分寫入**

---

## 4. 策略推理管線（In-Process 方向）

```mermaid
flowchart LR
    subgraph Input["◀ 輸入聚合 (50 Hz timer)"]
        IMU_IN["◀ /buddy/imu\n100 Hz buffer (last)"]
        DET_IN["◀ /perception/objects\n15 Hz buffer (last)"]
    end

    subgraph Prep["特徵組合"]
        FEAT["(1,13) float32\n[qx qy qz qw]\n[gx gy gz]\n[ax ay az]\n[det_cx det_cy det_conf]"]
    end

    subgraph Backend["↺ 推理後端 (優先序)"]
        B1["↺ TRTInference.run()\n.engine 檔 (優先)"]
        B2["↺ ort.InferenceSession.run()\nONNX CPU (fallback)"]
        B3["↺ mock: sin(t)×32\n(無模型 fallback)"]
    end

    subgraph Output["► 輸出"]
        JC["► /policy/joint_commands\nFloat32MultiArray[32]\n∈ [-1.0, 1.0] Tanh"]
        AC["► /policy/action_chunk\nFloat32MultiArray[33]\n(+sim_flag)"]
        LAT["► /policy/latency\n[avg_ms, p99_ms] @ 1Hz"]
    end

    IMU_IN --> FEAT
    DET_IN --> FEAT
    FEAT --> B1
    B1 -.->|"fallback"| B2
    B2 -.->|"fallback"| B3
    B1 --> JC
    B2 --> JC
    B3 --> JC
    JC --> AC
    JC --> LAT

    style B1 fill:#dcfce7,stroke:#16a34a
    style B2 fill:#fef9c3,stroke:#ca8a04
    style B3 fill:#fee2e2,stroke:#dc2626
```

---

## 5. 狀態估計演算法（資料方向）

```mermaid
flowchart TD
    SHM_IN["◀ SHM: BuddyImu\n(ax,ay,az,gx,gy,gz,quat)\n@1kHz更新"]

    subgraph SE["state_estimator @ 500 Hz"]
        VINT["▶ 速度積分\nv += [ax, ay, az-9.81] × dt"]
        ZUPT["▶ ZUPT 靜止偵測\ngyro_mag = √(gx²+gy²+gz²)\naccel_mag = √(ax²+ay²+az²)\nif gyro<0.05 AND |accel-9.81|<0.3\n  v = [0,0,0]"]
        PINT["▶ 位置積分\np += v × dt"]
        CF["▶ Complementary Filter (α=0.98)\nroll  = 0.98×(roll+gx×dt) + 0.02×acc_roll\npitch = 0.98×(pitch+gy×dt) + 0.02×acc_pitch\nyaw  += gz×dt"]
        QUAT["▶ Euler→Quaternion\n(roll,pitch,yaw)→(qx,qy,qz,qw)"]
        WD["⚡ Watchdog\nimu_stale_count > 25 @500Hz\n= 50ms 無更新\n▶ estop_active = true"]
    end

    SHM_OUT["▶ SHM: StatePose\nposition[3], orientation[4]\n@500Hz更新"]

    SHM_IN --> VINT
    VINT --> ZUPT
    ZUPT --> PINT
    PINT --> SHM_OUT
    SHM_IN --> CF
    CF --> QUAT
    QUAT --> SHM_OUT
    SHM_IN --> WD
    WD -->|"▶ 單向寫入"| SHM_OUT
```

---

## 6. 模組責任邊界（含方向）

| 模組 | 語言 | 頻率 | SHM 方向 | ROS2 方向 | 主要責任 |
|------|------|------|---------|---------|---------|
| `hal_buddy` | C++17 | 1000 Hz | ▶ 寫 imu/js ◀ 讀 cmd | — | 硬體 I/O、Watchdog 觸發 |
| `state_estimator` | C++17 | 500 Hz | ◀ 讀 imu ▶ 寫 pose | — | CF 姿態、ZUPT、Watchdog |
| `ros2_bridge` | C++17+rclcpp | 100 Hz | ◀ 讀 ▶ 寫 cmd/watchdog | ► Pub ◀ Sub ⇄ Srv | SHM↔DDS 橋接、E-stop 服務 |
| `policy_node` | Python 3 | 50 Hz | — | ◀ Sub ► Pub | 13D→32D 推理、感知融合 |
| `perception_node` | Python 3 | 15 Hz | — | ◀ Sub ► Pub | 物件偵測 |
| `camera_node` | Python 3 | 15 Hz | — | ► Pub | USB 攝影機採集 |
| `recorder_node` | Python 3 | async | — | ◀ Sub | MCAP bag 錄製 |

---

## 7. Build 系統

### C++ (colcon + CMake)

```
robot_rt_cpp (package.xml v0.1.0)
  依賴: rclcpp, sensor_msgs, geometry_msgs, std_msgs,
        std_srvs, nav_msgs, pthread, rt
  標準: C++17, -Wall -Wextra -Wpedantic
  產出:
    hal_buddy        — standalone RT binary (SCHED_FIFO prio 80)
    state_estimator  — standalone RT binary (SCHED_FIFO prio 70)
    ros2_bridge      — rclcpp node (100 Hz timer)
    test_shm_logic   — unit test binary
    test_safety_logic — unit test binary
    benchmark_rt     — 1kHz jitter benchmark (5000 iterations)
```

### Python 依賴

```
numpy         — 數值運算、tensor 組裝
onnxruntime   — CPU 推理後端
opencv-python — v4l2 採集、影像前處理
torch         — 模型訓練/ONNX 匯出（離線開發機用）
tensorrt      — GPU 推理（JetPack 預裝，Python API 待啟用）
pycuda        — TRT CUDA 記憶體管理
lcm           — LCM 序列化（Legacy 路徑用）
pytest        — 單元測試
```
