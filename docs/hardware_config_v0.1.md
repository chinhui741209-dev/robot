# Hardware Configuration v0.1

## 硬體平台

### 主控: NVIDIA AGX Orin

| 項目 | 規格 |
|------|------|
| Model | NVIDIA Jetson AGX Orin |
| CPU | 12-core ARM Cortex-A78AE (Armv8.2) |
| GPU | 2048-core NVIDIA Ampere |
| Memory | 32GB LPDDR5 |
| Storage | 64GB eMMC + NVMe SSD |
| AI Performance | 275 TOPS |
| Power | 15W - 60W (configurable) |

### 系統資源

| Resource | Usage |
|----------|-------|
| CPU | 2.6GB / 29GB (9%) |
| Memory | 8.2GB / 29GB available |
| Storage | 30GB / 54GB used (58%) |
| Swap | 14GB |

## 感測器配置

### IMU (慣性測量單元)

| Topic | Frame | Rate | Message Type |
|-------|-------|------|--------------|
| /buddy/imu | buddy_imu | 1000 Hz | sensor_msgs/Imu |
| /omni/imu | omni_imu | 1000 Hz | sensor_msgs/Imu |

### Motor State

| Topic | Frame | Rate | Message Type |
|-------|-------|------|--------------|
| /buddy/motor_state | - | 1000 Hz | geometry_msgs/Twist |
| /omni/motor_state | - | 1000 Hz | geometry_msgs/Twist |

### Camera (待確認)

| Topic | Frame | Rate | Resolution | Message Type |
|-------|-------|------|------------|--------------|
| /perception/camera | camera | 15 Hz | 640x480 | sensor_msgs/Image |

### Lidar (待確認)

| Topic | Frame | Rate | Points | Message Type |
|-------|-------|------|--------|--------------|
| /perception/lidar | lidar | 15 Hz | - | std_msgs/Float32MultiArray |

## 軟體架構與 Topic Map

```
                    ┌──────────────────┐
                    │   HAL (1kHz)     │
                    │  hal_buddy_node  │
                    └────────┬─────────┘
                             │ /buddy/imu
                             │ /buddy/motor_state
                             │ /buddy/hal/health
                             ▼
┌──────────────────┐   ┌──────────────────┐
│ State Estimator  │◄──│   OMNI (1kHz)    │
│    (500 Hz)      │   │ hal_omni_node    │
└────────┬─────────┘   └──────────────────┘
         │ /state/pose
         │ /tf
         ▼
┌──────────────────┐   ┌──────────────────┐
│   Policy (50Hz)  │◄──│  Perception      │
│  policy_node     │   │  (15 Hz)         │
└────────┬─────────┘   └──────────────────┘
         │ /policy/action
         │ /policy/action_chunk
         ▼
┌──────────────────┐
│   Recorder       │
│  recorder_node  │
└──────────────────┘
```

## ROS 2 Topic 清單

### 已定義 Topics

| Topic | Type | Frequency | Publisher | Subscriber |
|-------|------|-----------|-----------|------------|
| /buddy/imu | sensor_msgs/Imu | 1000 Hz | hal_buddy | state_estimator |
| /buddy/motor_state | geometry_msgs/Twist | 1000 Hz | hal_buddy | - |
| /buddy/hal/health | std_msgs/String | 1000 Hz | hal_buddy | - |
| /omni/imu | sensor_msgs/Imu | 1000 Hz | hal_omni | - |
| /omni/motor_state | geometry_msgs/Twist | 1000 Hz | hal_omni | - |
| /omni/hal/health | std_msgs/String | 1000 Hz | hal_omni | - |
| /state/pose | geometry_msgs/Pose | 500 Hz | state_estimator | - |
| /tf | geometry_msgs/Twist | 500 Hz | state_estimator | - |
| /policy/action | geometry_msgs/Twist | 50 Hz | policy_node | - |
| /policy/action_chunk | std_msgs/Float32MultiArray | 50 Hz | policy_node | - |
| /policy/latency | std_msgs/Float32MultiArray | 1 Hz | policy_node | - |
| /perception/camera | sensor_msgs/Image | 15 Hz | perception | - |
| /perception/lidar | std_msgs/Float32MultiArray | 15 Hz | perception | - |
| /metrics/system | std_msgs/Float32MultiArray | 1 Hz | w3_launch | - |
| /metrics/rt_jitter | std_msgs/Float32MultiArray | 1 Hz | w3_launch | - |
| /recorder/status | std_msgs/String | 1 Hz | recorder | - |

## 通訊介面

### 有線

| Interface | Protocol | Purpose |
|-----------|----------|---------|
| USB-C | - | Debug / Flash |
| Ethernet | 1 Gbps | Network |
| CAN Bus | CAN 2.0 | Motor Control (待確認) |
| UART | - | Serial Debug |
| I2C | - | Sensor Bus (待確認) |
| SPI | - | High-speed (待確認) |

### 無線

| Interface | Standard | Purpose |
|-----------|----------|---------|
| WiFi | 802.11ax | Network |
| Bluetooth | 5.x | Debug |

## 功耗配置

| Mode | CPU | GPU | Total |
|------|-----|-----|-------|
| MAXN | 15W | 50W | 60W |
| MODE_15W | 15W | - | 15W |
| MODE_30W | 30W | - | 30W |

## 待確認項目

- [ ] CAN Bus 連接配置
- [ ] Camera 實際型號與解析度
- [ ] Lidar 型號與規格
- [ ] Motor Controller 型號
- [ ] 電壓/功率需求
- [ ] 散熱方案

## 驗證指令

```bash
# 系統資訊
cat /etc/os-release
uname -a

# CPU/Memory
free -h
htop

# 存儲
df -h

# NVIDIA
tegrastats
jtop

# USB 設備
lsusb

# 網路
ip addr
```
