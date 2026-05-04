# 開發計畫：修正架構評估遺留問題 (P0, P1, P3)

## 背景與目標
修正優化後架構評估中指出的三個關鍵問題：模型維度不匹配 (P0)、欠缺 E-stop 重置端點 (P1)，以及位置純積分漂移 (P3)。

## 實作細節
1. **模型與策略節點修正 (P0)**:
   - 執行 `python3 models/generate_simple_policy.py` 重新生成 13 維輸入的 ONNX 模型。
   - 修正 `policy/policy_node.py` 的 Docstring。
2. **安全機制補全 (P1)**:
   - 修改 `rt_cpp/src/ros2_bridge.cpp`：新增 `/estop_reset` 訂閱者，接收信號後重置 `shm->estop_active` 旗標。
3. **狀態估計優化 (P3)**:
   - 修改 `rt_cpp/src/state_estimator.cpp`：加入 ZUPT (Zero-Velocity Update) 靜止偵測，當加速度與角速度極小時，逐漸將速度歸零。

## 驗證計畫
- 編譯與執行 `ros2_bridge` 確保無語法錯誤。
- 檢查 `/estop_reset` topic 是否成功建立。
