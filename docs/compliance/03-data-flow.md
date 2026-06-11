# 03 資料流（DF）

ASPICE SWE.2/SWE.3 / ISO 26262-6 §7–8。

## 資料流 (DF)

| ID | 流 | 路徑 | 資料項 |
|---|---|---|---|
| DF-001 | 偵測 | camera → perception(decode_yolov8 / ClaudeVisionDetector) → `/perception/objects` | bbox 像素中心、class、score |
| DF-002 | 單目 3D | 帶 depth 之偵測 → `projection.backproject(u,v,Z)` → `/perception/objects_3d` | 相機座標 (X,Y,Z) m |
| DF-003 | 策略推論 | `/buddy/imu` + `/perception/objects` → `build_obs13` → policy ONNX / expert → `/policy/joint_commands` | obs13、act32∈[-1,1] |
| DF-004 | 場景圖 | `/perception/objects(_3d)` → ObjectTracker → `/world_model/state` | present_classes、objects、objects_3d |
| DF-005 | 語言規劃 | `/ui/user_command` → task_parser/vla → `/task/parsed_command` → planner（讀 world state）→ `/planner/current_step` + `/arbiter/mode` | intent/source/target/steps、step idx、mode |
| DF-006 | 動作仲裁 | `/arbiter/mode` + `/policy/joint_commands` + `/control/target` → arbitrate → `/control/arbitrated_command` | authority(policy/skill/idle) |
| DF-007 | BC 訓練 | sim/錄製 → `data/bc/*.npz` → build_dataset → train_policy → `models/candidate/*.onnx` → 晉升 active | (obs,act) pairs |

## 信任邊界與輸入驗證

| 邊界 | 風險 | 緩解 |
|---|---|---|
| Claude API 回應（DF-001/005/外部）| 不可信結構/數值 | `parse_detections`/`parse_plan` 嚴格驗證、clip、過濾、缺欄回 None；strict tool schema |
| 相機影像 | row stride/編碼差異、空幀 | 依 `msg.step` 解碼、空幀略過 |
| 偵測 results[] | 空 hypothesis → IndexError | `best_detection`/`postprocess` 防空 |
| obs/det 時效（DF-003/錄製）| stale topic 配錯標籤 | recorder/expert `max_obs_age` 守衛 |
| 動作來源時效（DF-006）| 跨任務重發舊指令 | arbiter `max_cmd_age` 守衛 |
| 憑證（IF-014）| 金鑰外洩 | 僅 env、`.gitignore` 排除、不印出 |
| API 限流/中斷 | 節點崩潰 | except → 回 []/None + 退回本地後端 |
| 高頻 RT 路徑 | 視覺/3D 汙染 1kHz SHM | 視覺/3D 一律走 DDS，**不動 SHM 合約** |
