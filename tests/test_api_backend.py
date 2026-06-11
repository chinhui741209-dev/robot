#!/usr/bin/env python3
"""
Unit tests for the Claude API backends' pure parsers (no SDK / no network).
Run: PYTHONPATH=. pytest tests/test_api_backend.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.api_backend import parse_detections
from policy.vla_brain import parse_plan


# ---- parse_detections (normalized -> pixels) ------------------------------

def test_parse_detections_scales_to_pixels():
    ti = {"detections": [
        {"label": "Apple", "confidence": 0.9, "cx": 0.5, "cy": 0.25, "w": 0.1, "h": 0.2},
    ]}
    out = parse_detections(ti, 640, 480, conf_thresh=0.3)
    assert len(out) == 1
    d = out[0]
    assert d["class"] == "apple"            # lowercased
    assert abs(d["cx"] - 320) < 1e-6 and abs(d["cy"] - 120) < 1e-6
    assert abs(d["w"] - 64) < 1e-6 and abs(d["h"] - 96) < 1e-6
    assert d["score"] == 0.9

def test_parse_detections_filters_low_conf():
    ti = {"detections": [{"label": "pen", "confidence": 0.1, "cx": 0.5, "cy": 0.5, "w": 0.1, "h": 0.1}]}
    assert parse_detections(ti, 640, 480, conf_thresh=0.3) == []

def test_parse_detections_clamps_and_skips_bad_rows():
    ti = {"detections": [
        {"label": "box", "confidence": 0.8, "cx": 1.5, "cy": -0.2, "w": 0.3, "h": 0.3},  # clamped
        {"label": "", "confidence": 0.9, "cx": 0.5, "cy": 0.5, "w": 0.1, "h": 0.1},        # empty label -> skip
        {"label": "bad", "confidence": 0.9},                                               # missing coords -> skip
    ]}
    out = parse_detections(ti, 100, 100, conf_thresh=0.3)
    assert len(out) == 1 and out[0]["class"] == "box"
    assert out[0]["cx"] == 100 and out[0]["cy"] == 0   # clamped to [0,1]*dim

def test_parse_detections_depth():
    ti = {"detections": [
        {"label": "cup", "confidence": 0.8, "cx": 0.5, "cy": 0.5, "w": 0.1, "h": 0.1, "depth_m": 1.5},
        {"label": "pen", "confidence": 0.8, "cx": 0.2, "cy": 0.2, "w": 0.1, "h": 0.1, "depth_m": -3},  # invalid -> None
        {"label": "box", "confidence": 0.8, "cx": 0.3, "cy": 0.3, "w": 0.1, "h": 0.1},                 # absent -> None
    ]}
    out = parse_detections(ti, 640, 480, conf_thresh=0.3)
    by = {d["class"]: d for d in out}
    assert by["cup"]["depth"] == 1.5
    assert by["pen"]["depth"] is None
    assert by["box"]["depth"] is None


def test_parse_detections_empty_and_malformed():
    assert parse_detections({}, 640, 480) == []
    assert parse_detections({"detections": []}, 640, 480) == []
    assert parse_detections(None, 640, 480) == []
    assert parse_detections("nonsense", 640, 480) == []


# ---- parse_plan -----------------------------------------------------------

def test_parse_plan_normalizes():
    ti = {"intent": "Pick_And_Place", "source": "Pen", "target": "BOX",
          "steps": ["locate_pen", " grasp_pen ", "move_to_box", "release_pen"]}
    p = parse_plan(ti)
    assert p["intent"] == "Pick_And_Place"
    assert p["source"] == "pen" and p["target"] == "box"
    assert p["steps"] == ["locate_pen", "grasp_pen", "move_to_box", "release_pen"]

def test_parse_plan_requires_steps():
    assert parse_plan({"intent": "x", "source": "a", "target": "b", "steps": []}) is None
    assert parse_plan({"intent": "x"}) is None
    assert parse_plan(None) is None

def test_parse_plan_defaults_intent():
    p = parse_plan({"source": "", "target": "", "steps": ["wave"]})
    assert p["intent"] == "task" and p["steps"] == ["wave"]
