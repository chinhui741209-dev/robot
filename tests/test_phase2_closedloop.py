#!/usr/bin/env python3
"""
Unit tests for the Phase 2 closed-loop orchestration logic (ASPICE SWE.4).

Pure logic only (no ROS 2): ObjectTracker persistence, StepSequencer event-driven
advancement / retry / fail, step preconditions, and the action-chain arbiter.
Run: PYTHONPATH=. pytest tests/test_phase2_closedloop.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world_model.tracker import ObjectTracker
from planner.step_logic import (
    StepSequencer, step_precondition, RUNNING, COMPLETED, FAILED,
)
from arbiter.arbiter_logic import arbitrate


# ---- ObjectTracker --------------------------------------------------------

def _det(cls, conf=0.9, cx=100, cy=100):
    return {"class": cls, "confidence": conf, "cx": cx, "cy": cy}

def test_tracker_needs_confirm_frames():
    tr = ObjectTracker(present_timeout=1.0, confirm_frames=2)
    tr.update([_det("pen")], now=0.0)
    assert not tr.is_present("pen", 0.0)          # 1 hit < 2
    tr.update([_det("pen")], now=0.1)
    assert tr.is_present("pen", 0.1)              # 2 hits

def test_tracker_times_out():
    tr = ObjectTracker(present_timeout=1.0, confirm_frames=1)
    tr.update([_det("box")], now=0.0)
    assert tr.is_present("box", 0.5)
    assert not tr.is_present("box", 2.0)          # last_seen too old

def test_tracker_present_classes_and_snapshot():
    tr = ObjectTracker(confirm_frames=1)
    tr.update([_det("pen"), _det("box")], now=0.0)
    assert tr.present_classes(0.0) == ["box", "pen"]
    snap = tr.snapshot(0.0)
    assert all(o["present"] for o in snap)

def test_tracker_keeps_highest_confidence_per_class():
    tr = ObjectTracker(confirm_frames=1)
    tr.update([_det("pen", conf=0.3, cx=10), _det("pen", conf=0.8, cx=99)], now=0.0)
    snap = {o["class"]: o for o in tr.snapshot(0.0)}
    assert snap["pen"]["confidence"] == 0.8 and snap["pen"]["pos"]["x"] == 99


# ---- step_precondition ----------------------------------------------------

def test_step_precondition_mapping():
    assert step_precondition("locate_pen", "pen", "box") == "pen"
    assert step_precondition("grasp_pen", "pen", "box") == "pen"
    assert step_precondition("move_to_box", "pen", "box") == "box"
    assert step_precondition("release_pen", "pen", "box") == "box"  # release happens at target
    assert step_precondition("wait", "pen", "box") is None


# ---- StepSequencer --------------------------------------------------------

def test_sequencer_advances_when_precondition_met():
    seq = StepSequencer(["locate_pen", "grasp_pen"], source="pen", target="box",
                        confirm_needed=2)
    seq.update(["pen"], now=0.0)
    ev = seq.update(["pen"], now=0.1)
    assert ev["advanced"] and ev["idx"] == 1 and ev["state"] == RUNNING

def test_sequencer_waits_when_precondition_absent():
    seq = StepSequencer(["locate_pen"], source="pen", target="box", confirm_needed=1)
    ev = seq.update([], now=0.0)               # pen not present
    assert not ev["advanced"] and ev["state"] == RUNNING and ev["precondition"] == "pen"

def test_sequencer_completes():
    seq = StepSequencer(["locate_pen"], source="pen", target="box", confirm_needed=1)
    ev = seq.update(["pen"], now=0.0)
    assert ev["state"] == COMPLETED

def test_sequencer_fails_after_retries():
    seq = StepSequencer(["locate_pen"], source="pen", target="box",
                        confirm_needed=1, timeout_s=1.0, max_retries=1)
    assert seq.update([], now=0.0)["state"] == RUNNING
    assert seq.update([], now=1.5)["state"] == RUNNING   # retry 1
    assert seq.update([], now=3.0)["state"] == FAILED    # retries exhausted

def test_sequencer_dwell_only_step_advances():
    seq = StepSequencer(["wait"], confirm_needed=2)       # precondition None
    seq.update([], now=0.0)
    ev = seq.update([], now=0.1)
    assert ev["state"] == COMPLETED


# ---- arbiter --------------------------------------------------------------

def test_arbiter_modes():
    assert arbitrate("LOCOMOTION", [1.0] * 32, [0.0] * 4) == ("policy", [1.0] * 32)
    assert arbitrate("MANIPULATION", [1.0] * 32, [9.0] * 4) == ("skill", [9.0] * 4)
    assert arbitrate("IDLE", [1.0] * 32, [9.0] * 4) == ("idle", [])
    assert arbitrate("LOCOMOTION", [], [9.0] * 4) == ("idle", [])  # no policy cmd yet
