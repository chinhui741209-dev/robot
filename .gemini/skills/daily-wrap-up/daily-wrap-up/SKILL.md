---
name: daily-wrap-up
description: 當使用者下達「結束今天開發」或類似指令時觸發。自動執行日終收尾工作流：彙整當日開發成果、更新進度報告與技術規格文件、並將所有變更推送到 GitHub。
---

# 技能：日終收尾與成果同步 (Daily Wrap-Up)

當接收到「結束今天開發」、「結束開發」、「Wrap up for today」等關鍵字時，必須執行以下標準化流程：

## 1. 開發成果彙整 (Content Synthesis)
*   **動作**：回顧當日所有完成的 `PLAN_*.md` 與 `sub-tasks`。
*   **產出**：產出一個簡短但資訊密集的「今日開發摘要」。

## 2. 文件最後同步 (Final Documentation Sync)
*   **PROGRESS_REPORT.md**：確保「目前狀態」已反映當日最新的進度，並在「重構履歷」中加入當日的最後總結。
*   **Software_Handover_Spec.md**：確保版本號與規格（API, Data Structs）與代碼實作一致。
*   **Plans Sync**：檢查 `/Users/joeylin/.gemini/tmp/` 下的臨時計畫文件，確保它們都已複製到 `robot/docs/plans/` 中。

## 3. Git 安全推送 (Git Workflow)
*   **檢查**：執行 `git status` 確保沒有漏掉的文件。
*   **暫存**：執行 `git add .`。
*   **提交**：執行 `git commit -m "Daily Wrap-up: YYYY-MM-DD - [今日重點概述]" `。
*   **推送**：執行 `git push origin main`。

## 4. 結束彙報 (Final Report)
*   提供一個清單，列出：
    1.  今日新增/修改的關鍵功能。
    2.  今日更新的文件。
    3.  Git Commit Hash。
    4.  明天的建議開發起點。
