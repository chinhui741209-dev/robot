# 09 合規稽核

ASPICE SWE.1–6 + ISO 26262-6 §6–9。狀態：✅ 有 / 🟡 部分 / ❌ 缺 / ⬜ 範圍外。

## 標準對照

| 流程 / 條款 | 文件 | 狀態 | 說明 |
|---|---|---|---|
| ASPICE SWE.1（需求）/ 26262-6 §6 | 01 | ✅ | 15 條 SR |
| ASPICE SWE.2（架構）/ §7 | 02 | ✅ | 22 ARC + 14 IF + mermaid |
| 資料流 / §7–8 | 03 | ✅ | 7 DF + 信任邊界 |
| ASPICE SWE.3（詳細設計）/ §8 | 04 | 🟡 | 無獨立 04；設計涵蓋於 02/03 與程式 docstring |
| ASPICE SWE.4（單元驗證）/ §9 | 05,06 | ✅ | 49 TC/TR 全 pass；🟡 節點封裝層僅 on-device smoke |
| 追溯 | 07 | ✅ | 雙向；3 處 partial |
| ASPICE SWE.5（整合）/ §10 | — | ⬜ | 範圍外（on-device smoke 部分覆蓋閉環） |
| ASPICE SWE.6（合格）/ §11 | — | ⬜ | 範圍外（無實機合格測試） |
| 26262-6 §5（規劃）| 08 | 🟡 | 以開發歷程/決策記錄代替正式計畫 |

## 缺口清單（依風險）

1. **(中) SR-014 憑證不外洩無自動化測試** —— 本週期已實際發生 GitHub PAT 外洩（已撤銷+改 SSH key）。建議加 pre-commit/CI secret 掃描。另 **GitLab `glpat-` 仍待輪換**（帳號層）。
2. **(中) ROS 節點封裝層 (*_node.py) 無 host 單元測試** —— 核心邏輯已抽純函式並測；節點僅 on-device smoke。建議加 launch_testing。
3. **(低-中) SR-013 obs/det 時效守衛無直接 TC** —— 僅空防護 TC-004。可將 staleness 判斷抽純函式補測。
4. **(低) SR-012 驗證 GUI 無 host TC** —— UI/HTTP 層以 on-device smoke 覆蓋。
5. **(範圍外) SWE.5/6 整合與合格測試** —— 實機閉環/夾取/PREEMPT_RT 未驗。
6. **(外部限制) 真機 API 偵測/3D demo 受 token 配額(429)** —— 管線/數學已由 TC+smoke 驗證，待有配額金鑰實跑。

## 就緒度

**範圍內（SWE.1–4 + 追溯）約 85%**：需求/架構/資料流/單元測試/追溯齊備且 49 測試全綠；扣分於詳細設計無獨立文件、節點層無 host 測試、3 處 partial 追溯。整合/合格（SWE.5/6）為範圍外、屬下一階段。

無安全相關失敗測試。最高優先後續：secret 掃描自動化 + GitLab token 輪換 + 節點層 launch_testing。
