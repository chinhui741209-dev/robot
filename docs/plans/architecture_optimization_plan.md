# 系統架構優化與實作計畫 (Architecture Optimization & Implementation Plan)

## 1. 核心目標 (Objective)
基於當前系統架構評估報告，本計畫旨在將系統從「概念驗證 (POC) 階段的空殼」推進至「具備物理閉環與真實硬體互動能力」的生產就緒狀態。計畫將優先解決系統中的高風險缺口，包括硬體串接、狀態估計精度、以及感知與策略的整合。

## 2. 階段性執行計畫 (Implementation Phases)

### 階段一：打通物理控制閉環 (Phase 1: Hardware-in-the-Loop) - **最高優先級**
目標：移除 `sim=True` 的純模擬狀態，將系統與真實馬達控制及硬體感測器接通。

*   **1.1 HAL 層真實硬體適配 (HAL Real Hardware Integration)**
    *   **目標檔案:** `rt_cpp/src/hal_buddy.cpp`, `hal/scripts/hal_buddy_node.py`
    *   **行動:** 將 mock 的 sine wave 邏輯替換為真實的硬體 SDK (如 Unitree SDK) 或基於 SPI/CAN bus 的底層驅動。
    *   **驗證:** 能從真實 IMU 讀取數據並寫入 SHM，能將 SHM 中的關節指令下發至真實馬達。
*   **1.2 策略層輸出轉換 (Policy Output Translation)**
    *   **目標檔案:** `policy/policy_node.py`, `models/generate_simple_policy.py`
    *   **行動:** 將策略模型的輸出由高階的 `Twist` (6維) 轉換為實體的 `JointCommand` (關節力矩 `tau_ff`、目標位置 `q_des` 等)。更新 ONNX 模型的 Action Space 定義。
    *   **驗證:** 策略節點的輸出能正確對應到 32-DOF 的關節控制指令。
*   **1.3 E-Stop 安全機制補全 (E-Stop Logic Completion)**
    *   **目標檔案:** `rt_cpp/src/test_safety_logic.cpp`, `rt_cpp/src/hal_buddy.cpp`
    *   **行動:** 補齊 E-Stop 觸發後的重置 (Reset) 邏輯，確保系統在異常後能安全恢復。

### 階段二：核心演算法升級 (Phase 2: Core Algorithm Upgrades)
目標：提升基礎模組的穩定性與正確性，替換掉過於簡陋的實作。

*   **2.1 升級狀態估計器 (State Estimator Upgrade)**
    *   **目標檔案:** `rt_cpp/src/state_estimator.cpp`
    *   **行動:** 移除單純的加速度積分邏輯。引入互補濾波器 (Complementary Filter) 或擴展卡爾曼濾波器 (EKF)，結合 IMU 與關節運動學進行姿態融合。
    *   **驗證:** 在靜止與劇烈運動下，位置與姿態估計收斂且無發散現象。
*   **2.2 LCM 型態自動化生成 (LCM Generation Automation)**
    *   **目標檔案:** `lcm_types/generate_types.sh`, `lcm_types/robot_lcm_types.py`
    *   **行動:** 廢棄手寫的 python struct marshalling，改用 `lcm-gen` 工具透過 `.lcm` 檔案自動生成 C++ 與 Python 的綁定代碼，確保跨語言型態安全。
    *   **驗證:** 成功編譯生成的代碼並通過序列化/反序列化單元測試。

### 階段三：高階智慧整合 (Phase 3: Autonomy & Perception Integration)
目標：讓系統具備完整的自主感知與任務執行能力，為 VLA 大模型鋪路。

*   **3.1 感知與策略融合 (Perception-Policy Fusion)**
    *   **目標檔案:** `policy/policy_node.py`
    *   **行動:** 修改 Policy 節點，使其訂閱 `/perception/detections` 主題，將視覺感知特徵作為模型的輸入狀態之一，建立完整的 Sensor-to-Action 迴路。
*   **3.2 任務與規劃層實作 (Task & Planner Realization)**
    *   **目標檔案:** `task_parser/scripts/task_parser_node.py`, `planner/scripts/planner_node.py`
    *   **行動:** 建立基礎的任務狀態機 (State Machine) 與路徑/行為規劃邏輯，連接 Task Parser 解析出的指令，將其轉換為 Planner 可執行的 Step-by-Step 動作序列。

## 3. 驗證與測試策略 (Verification & Testing)
1.  **單元測試 (Unit Testing):** 針對狀態估計的 EKF 邏輯、LCM 序列化撰寫獨立測試。
2.  **硬體迴路測試 (HIL Testing):** 透過懸空測試 (Bench Test) 驗證 HAL 驅動與馬達通訊，確認延遲在 1ms (1000Hz) 內。
3.  **端到端閉環測試 (End-to-End Testing):** 在實體機器人或高擬真物理模擬器 (如 Gazebo/Isaac Sim) 中，運行完整的 Perception -> Policy -> ROS2 -> SHM -> HAL 流程，觀察動作的連貫性與 E-Stop 反應時間。
