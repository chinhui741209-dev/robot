---
name: plan-and-doc
description: 強制執行「計畫先行」開發流程。每當收到開發指令時，自動產出 Markdown 開發計劃書，並在實作過程中迭代更新 PROGRESS_REPORT.md 與 Software_Handover_Spec.md，確保開發履歷可稽核且具備接手價值。
---

# 技能：計畫與文檔同步開發 (Plan-and-Doc)

## 核心流程 (Workflow)

每當接收到涉及代碼修改或架構變更的指令時，必須嚴格遵守以下步驟：

### 1. 自動計畫產出 (Auto-Planning)
*   **動作**：首先調用 `enter_plan_mode` 並在 `robot/docs/plans/` 目錄下建立一個新的計畫文件（例如 `PLAN_YYYYMMDD_TASK.md`）。
*   **內容要求**：
    *   **背景與目標**：說明本次修改的動機。
    *   **實作細節**：列出受影響的模組、檔案與資料結構。
    *   **驗證計畫**：定義測試指令與預期輸出。
*   **稽核點**：將計畫內容摘要呈現給用戶，並詢問「是否同意此計畫？」。

### 2. 開發履歷記錄 (Iterative Reporting)
*   **動作**：每完成一個關鍵邏輯變更並驗證成功後，立刻更新 `robot/docs/progress_report_v0.1.md`。
*   **更新內容**：
    *   記錄完成的 Sub-task。
    *   附上實測數據或截圖摘要。
    *   記錄遇到的技術障礙與解決方案（作為開發履歷）。

### 3. 技術規格同步 (Final Handover Sync)
*   **動作**：在宣告任務完成前，必須同步更新 `robot/docs/Software_Handover_Spec.md`。
*   **更新內容**：
    *   更新版本號。
    *   更新 API 規格、資料結構或環境相依。

## 文件格式標準 (Documentation Standards)

*   **可稽核性**：所有變更必須能追蹤回特定的計畫。
*   **可接手性**：文件必須詳細到讓新工程師能「一鍵重現」開發環境。
*   **一致性**：架構圖、BOM 清單與程式碼實作必須完全對齊。
