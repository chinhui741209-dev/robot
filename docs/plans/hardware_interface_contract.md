# 硬體介面標準化合約 (Hardware Interface Contract v1.0)

## 1. 簡介 (Introduction)
本文件定義了「通用機器人平台 (Platform)」與「硬體供應商 (Vendor)」之間的通訊介面規範。透過此標準化介面，平台可以無視底層硬體差異，直接下達任務並取得感測數據。

## 2. 通訊機制 (Communication Mechanism)
*   **技術實作**: POSIX Shared Memory (SHM)。
*   **共享名稱**: `/robot_shared_data`。
*   **存取限制**: 存取任何欄位前必須取得 `pthread_mutex_t` 鎖。
*   **同步頻率**: 
    *   Vendor 寫入頻率建議: 1000 Hz。
    *   Platform 監控頻率: 100 Hz - 500 Hz。

## 3. 欄位擁有權與責任 (Ownership & Responsibility)

為了確保多進程穩定，各欄位被分配給唯一的「寫入者 (Owner)」。

### 3.1 供應商負責 (Vendor Owned - 寫入)
供應商提供的 Adapter 必須準確填寫以下欄位：
*   **`imu`**: 實體感測器的原始或融合數據。
*   **`joint_state`**: 32 個關節的目前位置 (rad)、速度 (rad/s) 與力矩 (Nm)。
*   **`imu_counter`**: 每寫入一次數據必須遞增一次。
*   **`robot_type`**: 於初始化時聲明機器人型態 (如：AMR, Quadruped)。

### 3.2 平台負責 (Platform Owned - 寫入)
*   **`joint_cmd`**: 發送給硬體的控制命令。Vendor 應讀取此欄位並轉換為驅動器指令。
*   **`watchdog_counter`**: 平台發出的心跳信號。Vendor 應監控此值，若 100ms 未變動應進入安全模式。
*   **`pose`**: 由平台狀態估計器產生的融合位姿。

## 4. 安全規範 (Safety Protocol)
*   **E-Stop**: 當 `estop_active` 為 `true` 時，Vendor 必須立即物理切斷馬達動力或進入零力矩模式。
*   **Watchdog**: 供應商 Adapter 必須具備 Watchdog 功能，偵測到平台當機時應主動剎車。

## 5. 接入流程 (Onboarding)
1. 廠商下載並包含 `shared_memory.hpp`。
2. 實作 `init_shared_memory(false)` 附加至記憶體區段。
3. 建立 1000Hz 迴圈，持續同步物理狀態至 `joint_state` 並讀取 `joint_cmd`。
