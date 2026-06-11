# 06 單元測試結果（TR）

ASPICE SWE.4 / ISO 26262-6 §9。

## 執行摘要

- **環境**：host (`.venv`, Python 3.13, pytest) — 純邏輯套件；於 Orin (Python 3.10) 同樣通過。
- **指令**：`PYTHONPATH=. pytest tests/test_bc_pipeline.py tests/test_phase2_closedloop.py tests/test_perception_phase3.py tests/test_api_backend.py tests/test_projection.py tests/test_language_backend.py`
- **結果**：**49 passed / 0 failed / 0 skipped**（3 warnings：torch.onnx 匯出 deprecation，非功能性）。
- 覆蓋率工具（pytest-cov）未安裝 → 覆蓋以 05 的單元盤點質性表示（純邏輯核心全覆蓋）。

## 結果 (TR)

TR-001 … TR-049：**全部 P（pass）**，一一對應 TC-001 … TC-049（見 07 追溯矩陣）。無 fail、無未跑。

| 檔案 | TC 範圍 | 結果 |
|---|---|---|
| test_bc_pipeline.py | TC-001..010 | 10 P |
| test_phase2_closedloop.py | TC-011..021 | 11 P |
| test_perception_phase3.py | TC-022..028 | 7 P |
| test_api_backend.py | TC-029..036 | 8 P |
| test_projection.py | TC-037..041 | 5 P |
| test_language_backend.py | TC-042..049 | 8 P |

## On-device smoke（節點層，非 host TC）

| 項目 | 結果 |
|---|---|
| BC 端到端（Orin CPU）：collect→build→train→eval | ✅ val MSE 0.0162→0.0040；trained vs random action-MSE 低 164×；torch-vs-onnx 6e-8 |
| Phase 2 閉環（ROS2）：planner 等 box 出現才前進 | ✅ COMPLETED（依場景閉環，非計時器） |
| 偵測解碼（真相機+真 YOLOv8）| ✅ 無物體時正確回空（無垃圾值） |
| Phase 5 NL→計畫（ROS2 rule 後端）| ✅ 中文「把蘋果放到盒子中」→ parsed_command |
| Claude Vision API 認證 | ✅ OAuth 有效；⚠️ token 限流過低致實偵測呼叫 429（需有配額金鑰，屬帳號層） |

## 未跑 / 已知限制

- `tests/test_contracts.py`、`tests/test_orchestration.py`（既有 ROS 整合測試）需 rclpy，僅能於 Orin 跑，未納入本次 host 執行 → 標記為**範圍外/待 on-device 補跑**。
- 真機 3D + 開放詞彙偵測 demo 受 API token 配額限制（429），管線/數學已由 TC 與 smoke 驗證。
