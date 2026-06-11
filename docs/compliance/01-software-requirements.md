# 01 軟體需求（SR）

ASPICE SWE.1 / ISO 26262-6 §6。本週期（Phase 0–5）的軟體需求。

| ID | 需求 | 來源/理由 |
|---|---|---|
| SR-001 | 運動策略須由**行為複製(BC)訓練**取得（模仿示範來源），禁止部署隨機初始化權重。 | Phase 1；原 policy 為隨機 MLP |
| SR-002 | 觀測為 13 維 `[quat4,gyro3,accel3,det_cx,det_cy,det_score]`、動作為 32 維 ∈[-1,1]；契約須**單一真實來源**，部署/訓練/錄製/評估共用。 | Phase 1；杜絕漂移 |
| SR-003 | 物體偵測須正確解碼 YOLOv8 輸出 `(1,4+nc,A)`，並採**per-class NMS**。 | Phase 3；舊解碼出垃圾、class-agnostic NMS 會壓制跨類別框 |
| SR-004 | 偵測類別清單與模型路徑須**可設定**（env/config/POC_ROOT），不得硬編絕對路徑。 | Phase 3；跨平台可攜 |
| SR-005 | 提供**開放詞彙**偵測之 Claude Vision API 後端；憑證僅由環境變數取得；無金鑰/失敗須優雅退回本地後端，不得崩潰。 | API 後端 |
| SR-006 | 規劃器須**事件驅動**：步驟僅在世界模型回報其前置物體 present 且連續確認後才前進；逾時重試、耗盡則 FAILED。 | Phase 2；取代開環 +1 |
| SR-007 | 世界模型須維持**持久化物體追蹤**：class present ⟺ 命中≥confirm_frames 且最近 present_timeout 內被見。 | Phase 2 |
| SR-008 | 動作鏈**仲裁器**須依模式選擇 locomotion(32-DoF policy) 或 manipulation(4-DoF skill) 之控制權。 | Phase 2/5 雙腦 |
| SR-009 | **單目 3D**：對帶深度估計之偵測以 pinhole 反投影得相機座標，發布 `/perception/objects_3d`；世界模型存 3D 位姿。不得更動 SHM 合約。 | Phase 4；RGB-only 相機 |
| SR-010 | 自然語言指令須轉為結構化任務計畫（rule 離線預設 + LLM 選用），並**泛化**至任意 source/target 組合（非寫死）。 | Phase 5 |
| SR-011 | VLA 大腦須以視覺+語言產出任務計畫並驅動規劃器（`/task/parsed_command`）。 | Phase 5 |
| SR-012 | 提供驗證儀表板顯示相機+偵測疊加與遙測；**無 IMU 時仍須顯示**相機/偵測。 | 驗證 GUI |
| SR-013 | 錄製/專家節點須以**時效檢查**配對 obs 與動作（topic 過期不配對）。 | Phase 1 / review |
| SR-014 | API 憑證僅由環境變數提供，**絕不進版控**（`.gitignore` 排除）。 | 資安 |
| SR-015 | BC 資料集 train/val 切分須**避免時序洩漏**（per-shard 連續尾段）。 | review |
