# 08 開發歷程（DEV）

ASPICE SUP.8/SUP.10 脈絡。本週期工作（分支 `feat/bc-training`，2026-06-09 ~ 06-11）。僅追加。

| DEV | 內容 | commit |
|---|---|---|
| DEV-2026-06-09-1 | Phase 0：Orin 同步至 73840af（純落後 36 commit，先備份 `orin-backup-20260609` 再 ff），確認 runtime CPU-only（torch 2.1 no-CUDA、ORT CPU、TRT 綁定壞 cudlaDeviceGetCount）。 | — |
| DEV-2026-06-09-2 | Phase 1：BC 訓練閉環。新增 obs_utils/scripted_expert/collect/build/train/eval + expert_node + 修 recorder_node + 抽 export_onnx。Mac+Orin 跑通，trained 比隨機好 164×，晉升 active。 | 8b499fb |
| DEV-2026-06-09-3 | 驗證 Web GUI（stdlib http.server + MJPEG + 遙測），相機 /dev/video1 確認可用。 | 6e3a8c4 |
| DEV-2026-06-09-4 | Phase 2：事件驅動 planner + 物體追蹤 world_model + 動作鏈仲裁；ROS2 閉環驗證（等 box 出現才前進）。 | cd27781 |
| DEV-2026-06-09-5 | Phase 3：修 YOLOv8 解碼 bug（共用 detection_utils）、類別/路徑 config 化、合成資料多類別。 | addf338 |
| DEV-2026-06-09-6 | 決策：移除 GitHub Actions 自動部署，改直接 SSH 開發；停用 self-hosted runner。 | 98f1b2f |
| DEV-2026-06-09-7 | 資安：外洩 GitHub PAT —— 撤銷 + 改 per-repo SSH deploy key，remote 清除 token。⚠️ GitLab `glpat-` 仍待輪換。 | — |
| DEV-2026-06-10-1 | Claude Vision API 後端（偵測 + VLA 大腦），憑證僅 env，無金鑰退回本地；驗證 OAuth 有效但 token 限流過低（429）。 | 8b3b84f |
| DEV-2026-06-10-2 | Code review（3 finder agents）→ 11 修正（best_detection 防空、API republish、per-class NMS、expert 不重複寫、GUI 無 IMU/stride、recorder/expert/arbiter 時效、val 防洩漏、classes 對齊）+ 移除 OpenVLA。 | 6dd26ec |
| DEV-2026-06-10-3 | 積極清理：移除 Gemini skills、舊偵測模型、Python/LCM 路徑、W1/W2 POC。**過程中發現並還原誤刪的 live demo（w3_launch/launch_demo），改以 build-graph + import 驗證後才刪。** | d291540, 588230d, d3a9dbf |
| DEV-2026-06-11-1 | Phase 4：單目 3D（projection 反投影、偵測帶 depth、Claude 估距離、/perception/objects_3d、world_model 存 3D）。 | 7d18113 |
| DEV-2026-06-11-2 | Phase 5：語言驅動（RuleBackend + LLMBackend、task_parser 改寫）+ 雙腦協調（mode_for_step 純函式串 arbiter）。 | be1d523 |
| DEV-2026-06-11-3 | Phase 6：建立 `docs/compliance/` 全套（01–09）+ 追溯矩陣 + 稽核（本提交）。 | (本次) |

**關鍵決策**：(1) CPU-only → 一律 ONNX CPU、單目 3D（無深度硬體）。(2) API 主力、本地為 fallback、契約不變使下游零改動。(3) 不動 SHM 合約，視覺/3D 走 DDS。(4) live demo = `bringup_all→launch_demo→w3_launch`，刪除前必先驗證 runtime。
