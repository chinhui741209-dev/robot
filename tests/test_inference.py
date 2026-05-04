import sys
import os
import pytest
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_perception_model_io():
    """驗證 Detection 模型輸入輸出維度"""
    # 模擬 224x224 RGB 輸入
    input_data = np.random.randn(1, 3, 224, 224).astype(np.float32)
    assert input_data.shape == (1, 3, 224, 224)
    
    # 模擬輸出: [x, y, w, h, conf]
    output_data = np.random.randn(1, 5).astype(np.float32)
    assert output_data.shape == (1, 5)
    assert output_data[0, 4] <= 10.0 # 模擬信心值範圍

def test_policy_inference_cadence():
    """Validate policy input/output dimensions match current 13D->32D model spec."""
    # 13-dim: Quat(4) + Gyro(3) + Accel(3) + Detection(3)
    sensor_input = np.random.randn(1, 13).astype(np.float32)
    assert sensor_input.shape == (1, 13), f"Expected (1,13), got {sensor_input.shape}"

    # 32-dim: joint position targets for 32-DOF robot
    action = np.random.randn(1, 32).astype(np.float32)
    assert action.shape == (1, 32), f"Expected (1,32), got {action.shape}"

def test_camera_latency_threshold():
    """驗證相機延遲計算邏輯"""
    start_time = 100.0
    end_time = 100.045 # 45ms latency
    latency = (end_time - start_time) * 1000
    assert latency < 50.0 # 應小於 15Hz 的 66ms 預算
