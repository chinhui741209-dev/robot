# Single-Camera VLA POC 開發計劃（Linux + ROS 2 為底）

## 1. 文件目的
本文件定義一個以 **Linux + ROS 2** 為底的單鏡頭 VLA（Vision-Language-Action）POC。目標是在一台機器人、一顆 camera、固定場景下，展示從視覺辨識、語意理解、任務拆解、動作執行、GUI 可視化到任務完成的完整鏈路。

本 POC 重點不是做研究型 end-to-end 黑盒模型，而是做出一個：
- 可部署
- 可執行
- 可展示
- 可解釋
- 可延伸到產品級架構

## 2. POC 目標
### 2.1 展示場景
場景中有：
- 一顆蘋果
- 一個盒子
- 一台機器人
- 一顆 camera

使用者輸入指令：
> 把蘋果放到盒子中

系統需要完成以下展示：
1. camera 畫面顯示蘋果與盒子
2. GUI 顯示物件辨識結果
3. GUI 顯示語意理解結果
4. GUI 顯示任務拆解步驟
5. GUI 顯示目前執行中的步驟
6. GUI 顯示對應啟動中的馬達 / 關節
7. 機器人完成 pick-and-place
8. GUI 顯示完成狀態

### 2.2 POC 核心價值
本 POC 的價值在於同時展示：
- Vision：看見蘋果與盒子
- Language：理解「把蘋果放到盒子中」
- Action：把高階語意轉成機器人可執行步驟
- Explainability：GUI 清楚呈現物件、步驟、關節/馬達狀態

## 3. 系統設計原則
### 3.1 Linux + ROS 2 為底
本 POC 以 Linux + ROS 2 作為應用與整合底座，用於：
- camera 資料流整合
- perception module 串接
- 任務狀態管理
- GUI 資訊同步
- planner 與 robot control bridge 整合
- 日誌與後續擴展

### 3.2 分層式 VLA，而非全黑盒
本 POC 採分層式架構：
1. Vision Layer：物件辨識、目標定位、場景狀態建立
2. Language Layer：把文字指令轉為結構化任務
3. Planning Layer：把任務轉為步驟與狀態機
4. Action Layer：將步驟映射到機器人控制命令
5. GUI Layer：可視化物件、步驟、關節/馬達狀態

### 3.3 POC 要能延伸到產品
因此本設計要求：
- 模組邊界清楚
- ROS 2 topic / service / action 有固定定義
- GUI 與控制鏈路分離
- 感知與控制可替換
- 後續可改成多鏡頭 / 多物件 / 多任務版本

## 4. POC 展示流程
1. 系統啟動 Linux 與 ROS 2 基礎服務
2. camera node 開始送出影像
3. perception node 偵測 apple 與 box
4. GUI 顯示辨識框與物件名稱
5. 使用者輸入指令：「把蘋果放到盒子中」
6. task parser 將指令轉成結構化任務
7. planner 產生 pick-and-place 步驟
8. GUI 顯示步驟列表與目前執行狀態
9. control bridge 根據步驟下發控制命令
10. robot 執行動作
11. GUI 即時顯示關節 / 馬達啟動狀態
12. apple 放入 box 後，GUI 顯示任務完成

## 5. Linux + ROS 2 系統架構
### 5.1 系統分層
#### Layer 1：作業系統層
- Ubuntu / Linux
- systemd
- 網路 / 裝置管理
- 相機驅動
- 機器人控制介面驅動

#### Layer 2：ROS 2 Middleware 層
- ROS 2 nodes
- ROS 2 topics
- ROS 2 services
- ROS 2 actions
- parameter management
- launch system

#### Layer 3：POC 功能模組層
- camera node
- perception node
- task parser node
- planner node
- robot control bridge node
- robot state monitor node
- GUI node

#### Layer 4：展示應用層
- 物件辨識展示
- 任務步驟展示
- 馬達 / 關節狀態展示
- 任務完成展示

## 6. 模組設計
### 6.1 Camera Node
功能：
- 讀取單顆 camera 影像
- 發布 image topic
- 提供時間戳與基本狀態

輸出：
- `/camera/image_raw`
- `/camera/status`

### 6.2 Perception Node
功能：
- 偵測 apple
- 偵測 box
- 輸出物件位置與信心值
- 建立最小 scene state

輸入：
- `/camera/image_raw`

輸出：
- `/perception/detections`
- `/perception/scene_state`
- `/perception/debug_image`

第一版建議：
- 使用輕量 object detection model
- 類別只需支援 apple、box

輸出資料範例：
```json
{
  "objects": [
    {"label": "apple", "bbox": [100, 120, 180, 210], "score": 0.95},
    {"label": "box", "bbox": [300, 100, 420, 260], "score": 0.97}
  ]
}
```

### 6.3 Task Parser Node
功能：
- 接收文字指令
- 將語意轉成結構化任務
- 產生標準化任務格式

輸入：
- `/ui/user_command`

輸出：
- `/task/parsed_command`

第一版建議採用 rule-based parser。

範例輸出：
```json
{
  "intent": "pick_and_place",
  "source_object": "apple",
  "target_object": "box"
}
```

### 6.4 Planner Node
功能：
- 根據 parsed task 與 scene state 產生可執行步驟
- 管理 step-by-step 狀態機

輸入：
- `/task/parsed_command`
- `/perception/scene_state`
- `/robot/state`

輸出：
- `/planner/task_plan`
- `/planner/current_step`
- `/planner/action_command`

建議步驟模板：
1. locate apple
2. locate box
3. move to pre-grasp pose
4. move to grasp pose
5. close gripper
6. lift apple
7. move to box
8. open gripper
9. retreat
10. done

### 6.5 Robot Control Bridge Node
功能：
- 接收 planner 下發的動作命令
- 轉換成 robot controller 可接受的控制命令
- 回讀機器人狀態
- 回報 step 完成狀態

輸入：
- `/planner/action_command`

輸出：
- `/robot/cmd`
- `/robot/state`
- `/robot/joint_state`
- `/robot/motor_status`

第一版建議：
- 預先定義 pose library
- 預先定義 motion sequence
- step 對應到固定動作

### 6.6 Robot State Monitor Node
功能：
- 收集機器人關節狀態
- 整理馬達啟動狀態
- 提供 GUI 顯示使用

輸入：
- `/robot/joint_state`
- `/robot/motor_status`
- `/robot/state`

輸出：
- `/robot/gui_status`

### 6.7 GUI Node
顯示區塊建議：
- Camera 視覺區：原始畫面、apple/box 偵測框、目標高亮
- 語意理解區：使用者輸入、intent、source object、target object
- 任務步驟區：全部步��列表與狀態
- 馬達 / 關節狀態區：目前啟動中的關節、馬達狀態、gripper 狀態

GUI 技術建議：
- 快速 POC：Streamlit
- 偏產品型展示：PySide6 / Qt
- 若重視展示質感與後續產品化，建議 PySide6

## 7. ROS 2 Topic / Service / Action 規劃
### 7.1 Topics
Camera / Perception：
- `/camera/image_raw`
- `/camera/status`
- `/perception/detections`
- `/perception/scene_state`
- `/perception/debug_image`

Task / Planner：
- `/ui/user_command`
- `/task/parsed_command`
- `/planner/task_plan`
- `/planner/current_step`
- `/planner/action_command`

Robot：
- `/robot/cmd`
- `/robot/state`
- `/robot/joint_state`
- `/robot/motor_status`
- `/robot/gui_status`

GUI：
- `/gui/display_state`
- `/gui/task_status`

### 7.2 Services
- `/task/start`
- `/task/stop`
- `/task/reset`
- `/robot/go_home`
- `/robot/enable`
- `/robot/disable`

### 7.3 Actions
後續可把 pick-and-place 規劃為 action：
- `/task/pick_and_place`

Action feedback 可回傳：
- current step
- percent complete
- error code

第一版可先用 topic + service 實作。

## 8. 模型規劃
### 8.1 第一版必要模型
A. Object Detection Model
- 用途：偵測 apple、box
- 部署位置：Orin
- 建議：TensorRT 優化，只做少數類別，先求穩定與速度

B. 可選：簡單目標追蹤
- 用途：保持 GUI target 一致性、降低畫面抖動

### 8.2 第一版不建議直接導入
- 大型 VLM
- 大型 LLM
- end-to-end 黑盒控制模型
- 複雜 world model

## 9. 控制設計建議
### 9.1 第一版控制策略
建議採：
- 固定 task template
- 固定 motion sequence
- 固定 pose library
- step-by-step control

### 9.2 關節 / 馬達顯示建議
GUI 需能顯示 Step 與 motor group mapping，例如：
- move to pre-grasp -> shoulder / elbow / wrist
- close gripper -> gripper motor
- move to box -> shoulder / elbow / wrist / base

### 9.3 第一版成功條件
- 蘋果與盒子擺放在可控區域
- robot 能完成固定 pick-and-place
- GUI 能同步展示每一步

## 10. GUI 詳細規劃
### 10.1 主畫面配置
建議 4 區塊：
- 左上：Camera View
- 右上：Command & Semantic
- 左下：Task Steps
- 右下：Robot Status

### 10.2 視覺效果建議
- running step 高亮
- done 顯示綠色狀態
- fail 顯示紅色狀態
- moving motor / joint 高亮
- 完成時顯示 mission complete

## 11. 建議的專案目錄
```bash
single_camera_vla_poc/
├── ros2_ws/
│   ├── src/
│   │   ├── camera_pkg/
│   │   ├── perception_pkg/
│   │   ├── task_parser_pkg/
│   │   ├── planner_pkg/
│   │   ├── robot_bridge_pkg/
│   │   ├── state_monitor_pkg/
│   │   └── gui_pkg/
│   └── launch/
├── models/
│   ├── detection/
│   └── engine/
├── configs/
├── scripts/
├── logs/
├── docs/
└── assets/
```

## 12. Linux + ROS 2 部署方式建議
### 12.1 啟動順序
1. camera driver ready
2. robot controller bridge ready
3. perception node ready
4. task parser ready
5. planner ready
6. robot state monitor ready
7. GUI ready

### 12.2 建議 launch 結構
- `bringup_camera.launch.py`
- `bringup_perception.launch.py`
- `bringup_robot.launch.py`
- `bringup_gui.launch.py`
- `bringup_all.launch.py`

### 12.3 建議 systemd 整合
若要更接近產品，可建立：
- camera.service
- robot-bridge.service
- perception.service
- vla-gui.service

第一版 POC 可先用 ROS 2 launch 管理；第二版再導入 systemd。

## 13. 日誌與可觀測性
建議最少記錄：
- user command
- parsed task
- detected objects
- current step
- robot command
- joint / motor status
- task success / fail
- error reason

後續可加：
- rosbag2 record
- task replay
- failure snapshot

## 14. 驗收條件
### 14.1 功能驗收
1. GUI 可正常開啟
2. camera 畫面正常顯示
3. apple / box 可被辨識
4. 指令可輸入並成功解析
5. step list 可正確生成
6. robot 可執行對應動作
7. GUI 可同步顯示 motor / joint 狀態
8. 任務完成後 GUI 顯示成功結果

### 14.2 展示驗收
1. 操作流程清楚
2. 視覺辨識穩定
3. 任務步驟易理解
4. 關節 / 馬達顯示明確
5. 任務完成時間可接受
6. 展示過程中不需大量人工介入

### 14.3 工程驗收
1. ROS 2 modules 可獨立啟動
2. topic 定義清楚
3. GUI 與控制鏈路分離
4. 模組可替換
5. 日誌可回查

## 15. 後續擴充方向
- 感知擴充：多物件、多類別、多鏡頭、depth camera
- 語意擴充：語音輸入、small LLM parser、多種 task template
- 動作擴充：更複雜抓取、多步驟 manipulation、fallback / retry
- GUI 擴充：3D robot skeleton、motor heatmap、task timeline、replay mode
- 產品化擴充：systemd service 化、diagnostics、health monitor、remote operation、model version control

## 16. 建議的實作順序
### 階段 1：展示鏈路打通
- camera
- detection
- GUI bbox
- text command
- task parsing
- step list 顯示

### 階段 2：假控制 / 模擬控制
- planner
- motor state simulation
- GUI step 與 motor 動態同步

### 階段 3：真實機器人控制
- robot control bridge
- 固定 pick-and-place motion sequence
- 真實 joint / motor state 顯示

### 階段 4：穩定化
- logging
- failure handling
- reset flow
- repeatable demo

## 17. 結論
本案建議以 **Linux + ROS 2** 作為底座，實作一個單鏡頭 VLA POC，展示「把蘋果放到盒子中」的完整鏈路。

技術路線不採一開始就使用全黑盒 end-to-end VLA，而採：
- 單鏡頭 perception
- rule-based / structured language parsing
- step-by-step task planning
- robot control bridge
- GUI explainability

這樣可以在控制風險、提升穩定性的前提下，快速做出一個**可展示、可理解、可延伸到產品化架構**的 VLA POC。