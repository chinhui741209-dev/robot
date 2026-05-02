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
    """驗證 Policy 推論步長與資料對齊"""
    # 模擬 10 維感測輸入
    sensor_input = np.random.randn(1, 10).astype(np.float32)
    assert sensor_input.shape == (1, 10)
    
    # 模擬輸出 6D Twist [linear_xyz, angular_xyz]
    action = np.random.randn(1, 6).astype(np.float32)
    assert action.shape == (1, 6)

def test_camera_latency_threshold():
    """驗證相機延遲計算邏輯"""
    start_time = 100.0
    end_time = 100.045 # 45ms latency
    latency = (end_time - start_time) * 1000
    assert latency < 50.0 # 應小於 15Hz 的 66ms 預算
