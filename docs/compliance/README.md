# 合規文件索引 — Orin Robot

軟體層合規記錄（ASPICE **SWE.1–SWE.6** + ISO 26262 **Part 6**）。涵蓋本開發週期（Phase 0–5）落地於分支 `feat/bc-training` 的工作。

| 檔案 | 內容 | 主要 ID |
|---|---|---|
| `01-software-requirements.md` | 軟體需求 | `SR-` |
| `02-software-architecture.md` | 元件、介面、靜態結構 | `ARC-`, `IF-` |
| `03-data-flow.md` | 資料流 + 信任邊界 | `DF-` |
| `05-unit-test-spec.md` | 單元測試案例規格 | `TC-` |
| `06-unit-test-results.md` | 測試結果、pass/fail、覆蓋 | `TR-` |
| `07-traceability-matrix.md` | 雙向追溯矩陣 | — |
| `08-development-history.md` | 開發歷程／決策 | `DEV-` |
| `09-compliance-audit.md` | 標準檢查表 + 缺口 + 就緒度 | — |
| `.audit-log.jsonl` | 稽核軌跡 | — |

**ID 規則**：三位補零、指派後不重用、刪除標 `(已廢止)`。追溯鏈 `SR → ARC → 原始碼 → TC → TR` 雙向。

**範圍**：軟體層（SWE.1–6 / 26262-6 §6–9）。系統層、整合/合格測試、硬體在險（HARA）標為範圍外。`04-detailed-design.md` 暫以 02/03 涵蓋。

**執行環境**：NVIDIA AGX Orin（CPU-only：torch 2.1 no-CUDA、ONNX Runtime CPU、TensorRT 綁定不可用）。雲端推論走 Claude Vision API（憑證僅由環境變數提供）。
