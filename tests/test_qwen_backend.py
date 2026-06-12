#!/usr/bin/env python3
"""
本地 Qwen2.5-VL 後端的純解析器單元測試（Robot_C Phase A1）。

純測試：無 GPU / 無 torch / 無 transformers / 無網路。驗證提示組裝與「Qwen 文字輸出 ->
與 Claude/Gemini 後端相同的像素偵測 dict」（重用 parse_detections）。重型相依在 detect()
才延遲匯入，因此本測試可在開發機直接跑。

執行：PYTHONPATH=. pytest tests/test_qwen_backend.py -v
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.qwen_backend import build_prompt, parse_qwen_text, _extract_json


def test_build_prompt_includes_hints_and_contract():
    p = build_prompt(["mouse", "滑鼠"])
    assert "mouse" in p and "滑鼠" in p
    assert '"detections"' in p and '"depth_m"' in p


def test_build_prompt_default_hint():
    assert "any nameable object" in build_prompt(None)
    assert "any nameable object" in build_prompt([])


def _txt(detections):
    return json.dumps({"detections": detections})


def test_parse_normalized_to_pixels():
    raw = _txt([{"label": "Mouse", "confidence": 0.88,
                 "cx": 0.5, "cy": 0.25, "w": 0.2, "h": 0.1, "depth_m": 0.5}])
    out = parse_qwen_text(raw, 640, 480, conf_thresh=0.3)
    assert len(out) == 1 and out[0]["class"] == "mouse"        # lowercased
    assert abs(out[0]["cx"] - 320) < 1e-6 and abs(out[0]["cy"] - 120) < 1e-6
    assert out[0]["depth"] == 0.5


def test_parse_strips_markdown_fence():
    raw = "```json\n" + _txt([{"label": "cup", "confidence": 0.9, "cx": 0.25,
                               "cy": 0.25, "w": 0.1, "h": 0.1, "depth_m": 0.4}]) + "\n```"
    out = parse_qwen_text(raw, 640, 480)
    assert out and out[0]["class"] == "cup"


def test_parse_tolerates_trailing_prose():
    raw = ("Here are the detections I found:\n"
           + _txt([{"label": "pen", "confidence": 0.7, "cx": 0.5, "cy": 0.5,
                    "w": 0.1, "h": 0.1, "depth_m": 0.3}])
           + "\nThat is all.")
    out = parse_qwen_text(raw, 320, 240)
    assert out and out[0]["class"] == "pen"


def test_parse_filters_low_conf_and_malformed():
    raw = _txt([{"label": "x", "confidence": 0.1, "cx": .5, "cy": .5,
                 "w": .1, "h": .1, "depth_m": 1.0}])
    assert parse_qwen_text(raw, 640, 480, conf_thresh=0.3) == []
    assert parse_qwen_text("not json at all", 640, 480) == []
    assert parse_qwen_text("", 640, 480) == []


def test_extract_json_helper():
    assert _extract_json('{"a": 1}') == {"a": 1}
    assert _extract_json("```json\n{\"a\": 2}\n```") == {"a": 2}
    assert _extract_json("garbage") is None
    assert _extract_json(None) is None
