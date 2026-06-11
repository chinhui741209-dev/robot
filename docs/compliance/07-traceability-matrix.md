# 07 雙向追溯矩陣

追溯鏈 `SR → ARC → 原始碼 → TC → TR`，雙向成立。

| SR | ARC | 原始碼 (file::symbol) | TC | TR (P/F) | 備註 |
|---|---|---|---|---|---|
| SR-001 | ARC-002,003 | scripted_expert::ScriptedExpert; train_policy/export_onnx | TC-005..008,010 | P | BC 訓練取代隨機權重 |
| SR-002 | ARC-001 | obs_utils::assemble_obs13/best_detection/quat_to_roll_pitch | TC-001,002,003,010 | P | 13/32 契約 |
| SR-003 | ARC-007 | detection_utils::decode_yolov8/_nms_numpy | TC-022..027 | P | per-class NMS |
| SR-004 | ARC-008 | classes::get_class_names/resolve_path | TC-028 | P | 路徑/類別可設定 |
| SR-005 | ARC-010 | api_backend::ClaudeVisionDetector/parse_detections | TC-029..033 | P | 開放詞彙 + 優雅退回 |
| SR-006 | ARC-014,015 | step_logic::StepSequencer/step_precondition; planner_node | TC-015..020 | P | 事件驅動閉環 |
| SR-007 | ARC-012,013 | tracker::ObjectTracker; world_model_node | TC-011..014 | P | 持久化追蹤 |
| SR-008 | ARC-016 | arbiter_logic::arbitrate; step_logic::mode_for_step | TC-021,048,049 | P | 雙腦仲裁 |
| SR-009 | ARC-011,009 | projection::backproject; perception_node::_publish_3d | TC-032,037..041 | P | 單目 3D |
| SR-010 | ARC-017,018 | language_backend::parse_rule; task_parser_node | TC-042..047,049 | P | NL→計畫泛化 |
| SR-011 | ARC-019,020 | vla_brain::parse_plan/ClaudeVlaBrain; vla_inference_node | TC-034..036 | P | VLA 大腦 |
| SR-012 | ARC-021 | verify_web_gui | — | — | 🟡 僅 on-device smoke，無 host TC |
| SR-013 | ARC-004,005 | expert_node; recorder_node (max_obs_age) | TC-004 | P | 🟡 空防護有 TC；時效守衛僅 on-device 驗 |
| SR-014 | (橫切) | .gitignore; api 後端 env-only | — | — | 🟡 稽核驗證已 gitignore，無自動測試 |
| SR-015 | ARC-003 | build_dataset::main（per-shard 切分） | TC-009 | P | 防時序洩漏 |

**反向檢查**：TC-001..049 皆對應到 SR 與被測單元（見 05）；TR-001..049 皆 P。

**缺口**（見 09）：
- SR-012：驗證 GUI 無 host 單元測試（UI/HTTP 層）→ 以 on-device smoke 覆蓋。
- SR-013：obs/det 時效守衛無直接 host TC（僅空防護 TC-004）。
- SR-014：憑證不外洩無自動化測試（靠 `.gitignore` + 稽核人工驗證）。
