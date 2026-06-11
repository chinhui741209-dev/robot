# 05 單元測試規格（TC）

ASPICE SWE.4 / ISO 26262-6 §9。純邏輯單元測試（host 可跑，無需 ROS/網路）。

| TC | 測試 | 被測單元 (file::symbol) | SR |
|---|---|---|---|
| TC-001 | obs 13 維佈局/型別 | obs_utils::assemble_obs13 | SR-002 |
| TC-002 | quat→roll/pitch 單位四元數=0 | obs_utils::quat_to_roll_pitch | SR-002 |
| TC-003 | 取最高分偵測 | obs_utils::best_detection | SR-002 |
| TC-004 | 空 detections 防護 | obs_utils::best_detection | SR-013 |
| TC-005 | 專家輸出形狀/範圍[-1,1] | scripted_expert::ScriptedExpert.act | SR-001 |
| TC-006 | 低分關閉轉向 | scripted_expert::act | SR-001 |
| TC-007 | 朝目標方向正確 | scripted_expert::act | SR-001 |
| TC-008 | 姿態回正方向 | scripted_expert::act | SR-001 |
| TC-009 | 資料集切分維度/數量 | build_dataset::main | SR-015 |
| TC-010 | ONNX 匯出 13→32 形狀 | generate_simple_policy::export_onnx | SR-001,SR-002 |
| TC-011 | 追蹤需 confirm_frames | tracker::ObjectTracker | SR-007 |
| TC-012 | 追蹤逾時消失 | tracker::ObjectTracker | SR-007 |
| TC-013 | present_classes/snapshot | tracker::ObjectTracker | SR-007 |
| TC-014 | 每類保留最高分 | tracker::ObjectTracker | SR-007 |
| TC-015 | 步驟前置映射 | step_logic::step_precondition | SR-006 |
| TC-016 | 前置滿足才前進 | step_logic::StepSequencer | SR-006 |
| TC-017 | 前置不足則等待 | step_logic::StepSequencer | SR-006 |
| TC-018 | 完成轉 COMPLETED | step_logic::StepSequencer | SR-006 |
| TC-019 | 重試耗盡轉 FAILED | step_logic::StepSequencer | SR-006 |
| TC-020 | 無前置步驟 dwell 前進 | step_logic::StepSequencer | SR-006 |
| TC-021 | 仲裁模式選擇 | arbiter_logic::arbitrate | SR-008 |
| TC-022 | YOLOv8 解碼 + NMS | detection_utils::decode_yolov8 | SR-003 |
| TC-023 | 兩種輸出方向 | detection_utils::decode_yolov8 | SR-003 |
| TC-024 | 座標縮放至 frame | detection_utils::decode_yolov8 | SR-003 |
| TC-025 | 信心門檻 | detection_utils::decode_yolov8 | SR-003 |
| TC-026 | NMS 保留不重疊/壓制重疊 | detection_utils::_nms_numpy | SR-003 |
| TC-027 | channels-first 轉置 | detection_utils::_to_anchors_by_channels | SR-003 |
| TC-028 | 類別 env 覆寫/fallback | classes::get_class_names | SR-004 |
| TC-029 | 偵測 normalized→pixel | api_backend::parse_detections | SR-005 |
| TC-030 | 低信心過濾 | api_backend::parse_detections | SR-005 |
| TC-031 | clamp/略過壞列 | api_backend::parse_detections | SR-005 |
| TC-032 | depth_m 解析（含無效） | api_backend::parse_detections | SR-005,SR-009 |
| TC-033 | 空/畸形輸入 | api_backend::parse_detections | SR-005 |
| TC-034 | 計畫正規化 | vla_brain::parse_plan | SR-011 |
| TC-035 | 計畫須有 steps | vla_brain::parse_plan | SR-011 |
| TC-036 | 計畫 intent 預設 | vla_brain::parse_plan | SR-011 |
| TC-037 | from_fov 主點/中心 | projection::from_fov,backproject | SR-009 |
| TC-038 | 反投影已知值 | projection::backproject | SR-009 |
| TC-039 | 投影↔反投影 round-trip | projection::project,backproject | SR-009 |
| TC-040 | 投影需 z>0 | projection::project | SR-009 |
| TC-041 | GT 定位誤差 <1e-6 | projection::project,backproject | SR-009 |
| TC-042 | 中文 pick_and_place | language_backend::parse_rule | SR-010 |
| TC-043 | 泛化超出寫死命令 | language_backend::parse_rule | SR-010 |
| TC-044 | 英文指令 | language_backend::parse_rule | SR-010 |
| TC-045 | 純抓取 | language_backend::parse_rule | SR-010 |
| TC-046 | 依位置定 source/target | language_backend::parse_rule | SR-010 |
| TC-047 | 無法解析回 None | language_backend::parse_rule | SR-010 |
| TC-048 | 步驟→模式映射 | step_logic::mode_for_step | SR-008 |
| TC-049 | 雙腦權限序列 | mode_for_step + arbitrate | SR-008,SR-010 |

**覆蓋盤點**：純邏輯核心（obs/expert/dataset/tracker/sequencer/arbiter/decoder/projection/language）皆有 TC。ROS 節點封裝層（*_node.py）以 on-device smoke 驗證（見 06），未納入 host TC；C++ RT 層、整合/合格測試為範圍外。
