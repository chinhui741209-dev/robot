#!/usr/bin/env python3
"""
Unit tests for the Behavior-Cloning pipeline (ASPICE SWE.4 / ISO 26262-6 §9).

Covers the pure, off-device pieces: the obs contract, the scripted expert's
documented behaviour, dataset building, and ONNX export shape/opset. No ROS 2
required. Run: PYTHONPATH=. pytest tests/test_bc_pipeline.py -v
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy.obs_utils import (
    assemble_obs13, build_obs13_from_msgs, best_detection,
    quat_to_roll_pitch, OBS_DIM, ACT_DIM, I_DET_CX, I_DET_SCORE,
)
from policy.scripted_expert import ScriptedExpert, J_YAW, J_ROLL


# ---- obs_utils ------------------------------------------------------------

def test_assemble_obs13_layout():
    obs = assemble_obs13([1, 2, 3, 4], [5, 6, 7], [8, 9, 10], [11, 12, 0.5])
    assert obs.shape == (OBS_DIM,)
    assert obs.dtype == np.float32
    assert list(obs[:4]) == [1, 2, 3, 4]
    assert list(obs[4:7]) == [5, 6, 7]
    assert list(obs[7:10]) == [8, 9, 10]
    assert obs[I_DET_CX] == 11 and obs[I_DET_SCORE] == 0.5


def test_quat_to_roll_pitch_identity():
    roll, pitch = quat_to_roll_pitch([0, 0, 0, 1])  # identity quaternion
    assert abs(roll) < 1e-6 and abs(pitch) < 1e-6


class _Hyp:
    def __init__(self, score): self.score = score
class _Res:
    def __init__(self, score): self.hypothesis = _Hyp(score)
class _Pos:
    def __init__(self, x, y): self.x, self.y = x, y
class _Center:
    def __init__(self, x, y): self.position = _Pos(x, y)
class _BBox:
    def __init__(self, x, y): self.center = _Center(x, y)
class _Det:
    def __init__(self, x, y, score):
        self.bbox = _BBox(x, y); self.results = [_Res(score)]
class _DetArray:
    def __init__(self, dets): self.detections = dets


def test_best_detection_picks_highest_score():
    arr = _DetArray([_Det(10, 20, 0.4), _Det(30, 40, 0.9), _Det(50, 60, 0.7)])
    assert best_detection(arr) == [30.0, 40.0, 0.9]


def test_best_detection_empty():
    assert best_detection(_DetArray([])) == [0.0, 0.0, 0.0]
    assert best_detection(None) == [0.0, 0.0, 0.0]


# ---- ScriptedExpert -------------------------------------------------------

def test_expert_output_shape_and_range():
    e = ScriptedExpert()
    for _ in range(100):
        obs = np.random.randn(OBS_DIM).astype(np.float32)
        obs[3] = 1.0  # plausible quat w
        a = e.act(obs)
        assert a.shape == (ACT_DIM,)
        assert a.min() >= -1.0 and a.max() <= 1.0


def test_expert_low_score_disables_turn():
    e = ScriptedExpert(score_thresh=0.3)
    obs = assemble_obs13([0, 0, 0, 1], [0, 0, 0], [0, 0, 9.81], [600, 50, 0.1])
    assert e.act(obs)[J_YAW] == 0.0  # below threshold -> no chasing noise


def test_expert_turns_toward_target():
    e = ScriptedExpert(img_w=640)
    # Target on the RIGHT (cx > centre) -> negative yaw command (turn right).
    right = assemble_obs13([0, 0, 0, 1], [0, 0, 0], [0, 0, 9.81], [600, 240, 0.9])
    left = assemble_obs13([0, 0, 0, 1], [0, 0, 0], [0, 0, 9.81], [40, 240, 0.9])
    assert e.act(right)[J_YAW] < 0 < e.act(left)[J_YAW]


def test_expert_posture_corrects_roll():
    e = ScriptedExpert()
    # Positive roll should drive J_ROLL negative (restoring).
    roll_quat = [np.sin(0.2 / 2), 0, 0, np.cos(0.2 / 2)]  # +0.2 rad roll
    obs = assemble_obs13(roll_quat, [0, 0, 0], [0, 0, 9.81], [0, 0, 0.0])
    assert e.act(obs)[J_ROLL] < 0


# ---- build_dataset --------------------------------------------------------

def test_build_dataset_split(tmp_path):
    from models.build_dataset import main as build_main
    rng = np.random.default_rng(0)
    obs = rng.standard_normal((200, OBS_DIM)).astype(np.float32)
    act = rng.standard_normal((200, ACT_DIM)).astype(np.float32)
    np.savez(tmp_path / "shard.npz", obs=obs, act=act, meta=np.array("test"))
    sys.argv = ["build_dataset", "--in", str(tmp_path), "--out", str(tmp_path),
                "--val-frac", "0.1", "--seed", "0"]
    build_main()
    tr = np.load(tmp_path / "dataset_train.npz")
    val = np.load(tmp_path / "dataset_val.npz")
    assert tr["obs"].shape[1] == OBS_DIM and tr["act"].shape[1] == ACT_DIM
    assert len(tr["obs"]) + len(val["obs"]) == 200
    assert len(val["obs"]) == 20


# ---- ONNX export ----------------------------------------------------------

def test_export_onnx_shape():
    torch = pytest.importorskip("torch")
    pytest.importorskip("onnx")
    from models.generate_simple_policy import SimpleLocomotionPolicy, export_onnx
    import tempfile
    model = SimpleLocomotionPolicy(input_dim=OBS_DIM, hidden_dim=32, output_dim=ACT_DIM)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m.onnx")
        export_onnx(model, path, input_dim=OBS_DIM)
        import onnx
        m = onnx.load(path)
        onnx.checker.check_model(m)
        inp = m.graph.input[0].type.tensor_type.shape.dim
        out = m.graph.output[0].type.tensor_type.shape.dim
        assert inp[1].dim_value == OBS_DIM
        assert out[1].dim_value == ACT_DIM
