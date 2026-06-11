#!/usr/bin/env python3
"""
Unit tests for Phase 5: language parsing (RuleBackend) + dual-brain coordination.
Pure (no ROS/network). Run: PYTHONPATH=. pytest tests/test_language_backend.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_parser.language_backend import parse_rule, RuleBackend
from planner.step_logic import mode_for_step
from arbiter.arbiter_logic import arbitrate


# ---- RuleBackend slot extraction ------------------------------------------

def test_rule_zh_pick_and_place():
    p = parse_rule("把筆放到盒子中")
    assert p["intent"] == "pick_and_place"
    assert p["source"] == "pen" and p["target"] == "box"
    assert p["steps"] == ["locate_pen", "grasp_pen", "move_to_box", "release_pen"]

def test_rule_generalizes_beyond_hardcoded():
    p = parse_rule("把蘋果放到盒子裡")           # apple was never a hardcoded command
    assert (p["source"], p["target"]) == ("apple", "box")
    p2 = parse_rule("把橘子放進杯子")
    assert (p2["source"], p2["target"]) == ("orange", "cup")

def test_rule_english():
    p = parse_rule("put the pen into the box")
    assert p["intent"] == "pick_and_place" and (p["source"], p["target"]) == ("pen", "box")

def test_rule_pick_only():
    p = parse_rule("grab the cup")
    assert p["intent"] == "pick" and p["source"] == "cup" and p["target"] == ""
    assert p["steps"] == ["locate_cup", "grasp_cup"]

def test_rule_order_by_position():
    p = parse_rule("把橘子放進盒子")              # orange before box
    assert p["source"] == "orange" and p["target"] == "box"

def test_rule_unparseable_returns_none():
    assert parse_rule("做點什麼有趣的事") is None
    assert parse_rule("") is None
    assert RuleBackend().parse("hello world") is None


# ---- Dual-brain coordination: step -> mode -> arbiter authority -----------

def test_mode_for_step():
    assert mode_for_step("locate_pen") == "LOCOMOTION"
    assert mode_for_step("grasp_pen") == "MANIPULATION"
    assert mode_for_step("move_to_box") == "MANIPULATION"
    assert mode_for_step("release_pen") == "MANIPULATION"
    assert mode_for_step(None) == "IDLE"

def test_dual_brain_authority_sequence():
    plan = parse_rule("把筆放到盒子中")
    policy_cmd, skill_cmd = [1.0] * 32, [9.0] * 4
    modes = [mode_for_step(s) for s in plan["steps"]]
    authority = [arbitrate(m, policy_cmd, skill_cmd)[0] for m in modes]
    assert modes == ["LOCOMOTION", "MANIPULATION", "MANIPULATION", "MANIPULATION"]
    # locomotion step -> 32-DoF BC policy; manipulation steps -> 4-DoF skill arm
    assert authority == ["policy", "skill", "skill", "skill"]
