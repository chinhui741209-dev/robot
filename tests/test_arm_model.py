#!/usr/bin/env python3
"""
Unit tests for the demo-studio arm/hand simulation (presentation layer).

Pure: no ROS / camera / API. Run: PYTHONPATH=. pytest tests/test_arm_model.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.arm_model import (
    JOINTS, JOINT_INDEX, ARM_JOINTS, HAND_JOINTS, home_pose, arm_fk, reach_ik,
    closed_hand, GraspPlan, MotorSim, ArmController, AMBIENT_C,
    REACHING, GRASPING, LIFTING, DONE, IDLE,
)


# ---- joint spec / FK ------------------------------------------------------

def test_g1_seventeen_joints_seven_arm_ten_hand():
    # G1 EDU single arm = 7-DoF; Dex2/5 hand = 10-DoF -> 17 motors.
    assert len(JOINTS) == 17
    assert len(ARM_JOINTS) == 7 and len(HAND_JOINTS) == 10


def test_home_pose_within_limits():
    pose = home_pose()
    for j in JOINTS:
        assert j.lo <= pose[j.name] <= j.hi


def test_arm_fk_home_reaches_forward_and_up():
    x, y, z = arm_fk(home_pose())
    assert x > 0.0          # reaches forward
    assert z > 0.0          # above the base plane


def test_reach_ik_stays_within_limits_and_aims():
    # Target on the right of the frame -> positive shoulder_yaw (turn right).
    pose = reach_ik(cx=520, cy=240, w=80, h=80, img_w=640, img_h=480)
    for j in JOINTS:
        assert j.lo - 1e-6 <= pose[j.name] <= j.hi + 1e-6
    assert pose["shoulder_yaw"] > 0
    left = reach_ik(cx=120, cy=240, w=80, h=80, img_w=640, img_h=480)
    assert left["shoulder_yaw"] < 0
    assert pose["elbow"] < 0     # elbow bent


def test_reach_ik_endpoint_is_finite_and_forward():
    pose = reach_ik(320, 240, 60, 60, 640, 480)
    x, y, z = arm_fk(pose)
    assert all(abs(v) < 2.0 for v in (x, y, z))


# ---- grasp plan -----------------------------------------------------------

def test_grasp_plan_phase_progression():
    plan = GraspPlan.build(320, 240, 60, 60, 640, 480)
    phases = [plan.sample(t)[0] for t in (0.1, 2.0, 3.0, 4.0, 5.5)]
    # REACHING appears before GRASPING before LIFTING before DONE.
    assert phases[0] == REACHING
    assert GRASPING in phases
    assert LIFTING in phases
    assert phases[-1] == DONE


def test_grasp_closes_fingers_over_time():
    plan = GraspPlan.build(320, 240, 60, 60, 640, 480)
    early = plan.sample(1.5)[1]    # pre-grasp, hand open
    late = plan.sample(3.2)[1]     # grasp, hand closed
    open_curl = sum(early[n] for n in HAND_JOINTS)
    closed_curl = sum(late[n] for n in HAND_JOINTS)
    assert closed_curl > open_curl + 50   # fingers clearly more curled


def test_closed_hand_within_limits():
    p = closed_hand(home_pose(), 1.0)
    for n in HAND_JOINTS:
        j = JOINTS[JOINT_INDEX[n]]
        assert j.lo <= p[n] <= j.hi


# ---- motor telemetry ------------------------------------------------------

def test_motor_tracks_target_and_velocity_sign():
    sim = MotorSim()
    tgt = home_pose()
    tgt["shoulder_yaw"] = 60.0
    for _ in range(200):
        sim.step(tgt, 0.03)
    s = sim.m["shoulder_yaw"]
    assert abs(s.actual - 60.0) < 1.0          # converges to target
    assert s.temp >= AMBIENT_C                  # never below ambient


def test_velocity_matches_finite_difference():
    sim = MotorSim()
    tgt = home_pose()
    tgt["shoulder_yaw"] = 30.0
    prev = sim.m["shoulder_yaw"].actual
    sim.step(tgt, 0.05)
    s = sim.m["shoulder_yaw"]
    assert abs(s.vel - (s.actual - prev) / 0.05) < 1e-6


def test_temperature_rises_under_sustained_load():
    sim = MotorSim()
    tgt = home_pose()
    t0 = sim.m["shoulder_pitch"].temp
    # oscillate to keep current flowing
    for k in range(300):
        tgt["shoulder_pitch"] = 20.0 + (15.0 if k % 2 else -15.0)
        sim.step(tgt, 0.03)
    assert sim.m["shoulder_pitch"].temp > t0
    for s in sim.snapshot():
        assert 0.0 <= s["load"] <= 100.0


def test_telemetry_bounds_and_fields():
    sim = MotorSim()
    sim.step(home_pose(), 0.03)
    snap = sim.snapshot()
    assert len(snap) == 17
    for row in snap:
        assert set(row) >= {"name", "group", "target", "actual", "vel",
                            "torque", "current", "temp", "load"}
        assert row["current"] >= 0.0


# ---- controller state machine ---------------------------------------------

def test_controller_full_cycle_reaches_done_then_idle():
    c = ArmController()
    c.set_locating("pick up the mouse")
    assert c.phase == "LOCATING"
    c.set_lock("mouse", 400, 220, 70, 60, 0.88)
    assert c.phase == REACHING and c.lock["class"] == "mouse"
    seen = set()
    for _ in range(400):           # ~12s at 30 ms
        c.step(0.03)
        seen.add(c.phase)
    assert {REACHING, GRASPING, LIFTING}.issubset(seen)
    assert DONE in seen
    # after the dwell it resets to IDLE and clears the lock
    assert c.phase == IDLE and c.lock is None


def test_controller_fallback_on_failed_lock():
    c = ArmController()
    c.set_locating("pick up the mouse")
    c.fail_lock("no api key")
    assert c.phase == IDLE
    assert c.lock["status"] == "fallback"


def test_snapshot_shape():
    c = ArmController()
    c.set_lock("cup", 300, 200, 50, 50, 0.9)
    c.step(0.03)
    snap = c.snapshot()
    assert set(snap) >= {"phase", "command", "lock", "gripper", "joints"}
    assert len(snap["joints"]) == 17
    assert 0.0 <= snap["gripper"] <= 1.0
