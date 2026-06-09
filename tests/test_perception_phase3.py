#!/usr/bin/env python3
"""
Unit tests for Phase 3 perception: the shared YOLOv8 decoder + class config.
Pure numpy (no cv2/ROS). Run: PYTHONPATH=. pytest tests/test_perception_phase3.py -v
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.detection_utils import decode_yolov8, _nms_numpy, _to_anchors_by_channels
from perception import classes as C


def _fake_yolo_output():
    """10 anchors, nc=2. anchor0=pen@(112,112); anchor1 overlaps anchor0 (NMS);
    anchor2=box@(20,20); rest low-confidence."""
    A = np.zeros((10, 6), np.float32)
    A[0] = [112, 112, 40, 40, 0.9, 0.1]   # pen
    A[1] = [114, 112, 40, 40, 0.8, 0.1]   # overlaps anchor0 -> suppressed
    A[2] = [20, 20, 10, 10, 0.1, 0.7]     # box, far away
    return A  # (anchors, 4+nc)


def test_decode_basic_and_nms():
    A = _fake_yolo_output()
    out = A.T[None]                        # (1, 6, 10) channels-first like YOLOv8 export
    dets = decode_yolov8(out, 224, 224, input_size=224,
                         conf_thresh=0.5, iou_thresh=0.45, class_names=["pen", "box"])
    classes = sorted(d["class"] for d in dets)
    assert classes == ["box", "pen"]      # anchor1 suppressed by NMS -> exactly 2
    pen = [d for d in dets if d["class"] == "pen"][0]
    assert abs(pen["cx"] - 112) < 1 and abs(pen["cy"] - 112) < 1
    assert abs(pen["score"] - 0.9) < 1e-5


def test_decode_handles_both_orientations():
    A = _fake_yolo_output()
    d1 = decode_yolov8(A.T[None], 224, 224, class_names=["pen", "box"])     # (1,6,A)
    d2 = decode_yolov8(A, 224, 224, class_names=["pen", "box"])              # (A,6)
    assert len(d1) == len(d2) == 2


def test_decode_scales_to_frame():
    A = _fake_yolo_output()
    dets = decode_yolov8(A.T[None], 448, 448, input_size=224, class_names=["pen", "box"])
    pen = [d for d in dets if d["class"] == "pen"][0]
    assert abs(pen["cx"] - 224) < 2        # 112 px in 224-input -> 224 px in 448 frame

def test_decode_conf_threshold():
    A = _fake_yolo_output()
    assert decode_yolov8(A.T[None], 224, 224, conf_thresh=0.95) == []  # nothing passes


def test_nms_keeps_disjoint_drops_overlap():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [100, 100, 110, 110]], np.float32)
    scores = np.array([0.9, 0.8, 0.7], np.float32)
    keep = _nms_numpy(boxes, scores, 0.45)
    assert 0 in keep and 2 in keep and 1 not in keep


def test_to_anchors_transposes_channels_first():
    a = _to_anchors_by_channels(np.zeros((1, 6, 1029)))
    assert a.shape == (1029, 6)


def test_class_config_env_override(monkeypatch):
    monkeypatch.setenv("POC_CLASSES", "pen, box, apple, orange")
    assert C.get_class_names() == ["pen", "box", "apple", "orange"]
    monkeypatch.delenv("POC_CLASSES")
    assert C.get_class_names() == C.DEFAULT_CLASSES
