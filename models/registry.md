# Model Registry v0.1

## Active Models (正式模型)

### 1. simple_policy.onnx
| 項目 | 值 |
|------|-----|
| Name | Simple Locomotion Policy |
| Version | v0.2 (BC-trained) |
| Type | MLP (13→64→64→32→32, Tanh) |
| Input Shape | (batch, 13) |
| Output Shape | (batch, 32) |
| Purpose | Locomotion / joint position control |
| Input Schema | [quat(4), gyro(3), accel(3), det_cx, det_cy, det_score] — see `policy/obs_utils.py` |
| Output Schema | 32 joint position targets ∈ [-1, 1] |
| Latency Budget | < 10ms (ONNX Runtime CPU) |
| Framework | PyTorch |
| ONNX Opset | 13 |
| Training | Behavior Cloning vs `ScriptedExpert` (`policy/scripted_expert.py`); MSE on (obs,act) pairs. **No longer random-initialised.** |
| Provenance | dataset `data/bc/dataset_*.npz` → `models/train_policy.py` → `models/candidate/` → promote |

> ⚠️ **晉升流程 (promote-after-review)**：`train_policy.py` 輸出到 `models/candidate/`（含 `.onnx` 與 `.pt`）。
> 人工確認 `scripts/eval_policy.py` 通過後，才覆蓋 active：
> ```bash
> cp models/candidate/simple_policy_bc.onnx models/active/simple_policy.onnx
> rm -f models/active/simple_policy.onnx.data   # 刪舊 external-data，否則會載到舊權重
> ```

### 2. detection.onnx
| 項目 | 值 |
|------|-----|
| Name | Simple Object Detection |
| Version | v0.1 |
| Type | CNN |
| Input Shape | (batch, 3, 224, 224) |
| Output Shape | (batch, 5) |
| Purpose | Object detection |
| Input Schema | RGB image |
| Output Schema | [bbox_x, bbox_y, width, height, confidence] |
| Latency Budget | < 50ms |
| Framework | PyTorch 2.11.0 |
| ONNX Opset | 18 |

## Fallback Models (備援模型)

Currently empty - 待建立備援版本。

## 待部署模型

| Model | Priority | Status |
|-------|----------|--------|
| simple_policy | P0 | ✅ Ready |
| detection | P0 | ✅ Ready |
| tracking | P1 | TODO |
| segmentation | P1 | TODO |
| anomaly_detection | P2 | TODO |

## 模型生成 / 訓練

```bash
# (舊) 生成隨機初始化 policy — 僅供結構參考，勿部署
python3 models/generate_simple_policy.py

# (新) Behavior Cloning 訓練閉環 — 取代隨機權重
export PYTHONPATH="$PWD"
python3 scripts/collect_bc_dataset.py --steps 20000 --seed 0 --out data/bc   # 或在 Orin 用 expert_node+recorder 錄真實 ROS2 資料
python3 models/build_dataset.py --in data/bc --out data/bc
python3 models/train_policy.py --train data/bc/dataset_train.npz --val data/bc/dataset_val.npz --epochs 50 --out models/candidate
python3 scripts/eval_policy.py --model models/candidate/simple_policy_bc.pt   # trained vs random vs expert

# Generate detection model
python3 models/generate_detection.py

# Test inference
python3 models/test_inference.py
```

## 模型驗證

```bash
# Check model files
ls -la models/active/

# Run inference test
python3 models/test_inference.py models/active/simple_policy.onnx
```