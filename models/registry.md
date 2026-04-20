# Model Registry v0.1

## Active Models (正式模型)

### 1. simple_policy.onnx
| 項目 | 值 |
|------|-----|
| Name | Simple Locomotion Policy |
| Version | v0.1 |
| Type | MLP |
| Input Shape | (batch, 10) |
| Output Shape | (batch, 6) |
| Purpose | Locomotion control |
| Input Schema | [imu_accel(3), imu_gyro(3), joint_pos(2), joint_vel(2)] |
| Output Schema | [linear.xyz(3), angular.xyz(3)] |
| Latency Budget | < 10ms |
| Framework | PyTorch 2.11.0 |
| ONNX Opset | 18 |

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

## 模型生成

```bash
# Generate policy model
python3 models/generate_simple_policy.py

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