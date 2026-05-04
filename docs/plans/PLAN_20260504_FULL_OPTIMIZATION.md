# 開發計畫：系統全方位架構優化 (2026-05-04)

## 背景與目標
本計畫旨在將 Robot 專案從 POC 階段推向生產就緒。我們將同時執行三個階段的優化，涵蓋硬體閉環、演算法升級與高階智慧整合，並確保所有變更符合 `plan-and-doc` 與 `daily-wrap-up` 技能規範。

## 實作細節 (Stages 1-3)

### 階段一：打通物理控制閉環
*   **HAL 真實硬體對接**:
    *   修改 `rt_cpp/src/hal_buddy.cpp`: 替換 mock sine wave 為底層通訊存根（預留 SDK 接口）。
    *   修改 `hal/scripts/hal_buddy_node.py`: 增加硬體通訊狀態監控。
*   **策略輸出轉換 (Twist to JointCommand)**:
    *   修改 `policy/policy_node.py`: 將輸出從 `geometry_msgs/Twist` 轉換為 `JointCommand` 映射。
    *   修改 `models/generate_simple_policy.py`: 更新 ONNX 模型的 Action Space 輸出維度定義。
*   **安全機制**:
    *   修改 `rt_cpp/src/test_safety_logic.cpp`: 實作 E-stop 後的狀態重置邏輯。

### 階段二：核心演算法升級
*   **狀態估計器 (EKF/互補濾波)**:
    *   修改 `rt_cpp/src/state_estimator.cpp`: 引入基礎的姿態融合演算法，解決純積分漂移問題。
*   **LCM 型態自動化**:
    *   執行 `lcm_types/generate_types.sh`: 透過 `lcm-gen` 自動產出綁定代碼，不再依賴手動維護的 `robot_lcm_types.py`。

### 階段三：高階智慧整合
*   **感知與策略融合**:
    *   修改 `policy/policy_node.py`: 訂閱 `/perception/detections` 並將其特徵輸入模型。
*   **任務與規劃層實作**:
    *   修改 `task_parser/scripts/task_parser_node.py` & `planner/scripts/planner_node.py`: 建立基於行為樹或狀態機的基礎任務邏輯。

## 驗證計畫
1.  **RT 延遲驗證**: 確保 SHM 讀寫在 1ms 內完成。
2.  **型態安全驗證**: 確保 Python 與 C++ 端的 LCM 型態完全對齊。
3.  **閉環模擬**: 在 `sim=False` 模式下測試 E-stop 觸發。

## 文件更新清單
*   `docs/progress_report_v0.1.md` (迭代更新)
*   `docs/Software_Handover_Spec.md` (任務結束前更新)
