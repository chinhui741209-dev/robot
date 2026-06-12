#!/usr/bin/env python3
"""
Simulated 6-axis arm + dexterous hand model for the interactive demo studio.

This is a *presentation* simulation — it does NOT drive real hardware and is
independent of the ROS control stack (the real arm is only 4-DoF position
targets; there is no dexterous hand or per-motor telemetry on this platform).
It produces a believable reach→grasp→lift trajectory for a 16-DoF rig and the
per-motor telemetry (angle / velocity / torque / current / temperature / load)
the web UI streams.

Pure Python (math + dataclasses only) so it is host-testable without ROS,
numpy, torch or a camera.

Frames: arm operates in a vertical plane rotated by shoulder_yaw about +Z (up).
All joint angles are in DEGREES at the API boundary; FK converts to radians.
"""

import math
from dataclasses import dataclass, field

# ---- phases ---------------------------------------------------------------
IDLE = "IDLE"
LOCATING = "LOCATING"        # waiting for the (open-vocab) detector to lock
LOCKED = "LOCKED"
REACHING = "REACHING"
GRASPING = "GRASPING"
LIFTING = "LIFTING"
DONE = "DONE"

# Link geometry (metres) for the arm chain (used by FK + the 3D renderer).
# NOTE: link lengths are approximate (presentation only) — pending exact values
# from the g1_description URDF. Joint *limits* and *torque_max* below ARE the
# real Unitree G1 (EDU, 29-DOF) values from g1_29dof.urdf, so motor telemetry
# (angle range / torque / load%) is faithful even though geometry is approximate.
L_BASE = 0.10
L_UPPER = 0.30
L_FORE = 0.25
L_WRIST = 0.10


@dataclass(frozen=True)
class Joint:
    name: str
    group: str          # "arm" | "hand"
    lo: float           # deg
    hi: float           # deg
    home: float         # deg
    link: float = 0.0   # metres (arm FK only)
    torque_max: float = 4.0   # N·m, for load%/current scaling


# Unitree G1 (EDU 29-DOF) single arm = 7-DoF + Dex2/5 dexterous hand = 10-DoF
# (thumb 2 + 4 fingers x 2) -> 17 motors total for this single-arm demo rig.
#
# Arm joint limits/torque are the real G1 values converted from g1_29dof.urdf
# (rad -> deg; torque_max = URDF <limit effort>):
#   shoulder_pitch −3.0892..2.6704 | 25      wrist_roll  ±1.9722        | 25
#   shoulder_roll  −1.5882..2.2515 | 25      wrist_pitch ±1.6144        |  5
#   shoulder_yaw   ±2.618          | 25      wrist_yaw   ±1.6144        |  5
#   elbow          −1.0472..2.0944 | 25
# Hand limits are the Unitree Dex2/5 (10-DoF, 2 active) finger ranges.
# NOTE: joint *sign conventions* here are presentation-only; the real robot uses
# unitree_hg / URDF axis conventions. The planar 2-link IK drives shoulder_pitch
# + elbow + wrist_pitch (+ shoulder_yaw for azimuth); shoulder_roll / wrist_roll
# / wrist_yaw stay at home and appear in telemetry only.
JOINTS = [
    Joint("shoulder_pitch", "arm", -177, 153, 20.0, L_UPPER, 25.0),
    Joint("shoulder_roll",  "arm",  -91, 129,  0.0, 0.0,     25.0),
    Joint("shoulder_yaw",   "arm", -150, 150,  0.0, L_BASE,  25.0),
    Joint("elbow",          "arm",  -60, 120, -30.0, L_FORE, 25.0),
    Joint("wrist_roll",     "arm", -113, 113,  0.0, 0.0,     25.0),
    Joint("wrist_pitch",    "arm",  -92.5, 92.5, 0.0, L_WRIST, 5.0),
    Joint("wrist_yaw",      "arm",  -92.5, 92.5, 0.0, 0.0,     5.0),
    # Dex2/5 hand: thumb j0 0-42 / j1 0-105 ; four fingers j0 0-88 / j1 0-105.
    Joint("thumb_j0",       "hand",   0,  42,  5.0, 0.0,     1.0),
    Joint("thumb_j1",       "hand",   0, 105,  5.0, 0.0,     0.8),
    Joint("index_j0",       "hand",   0,  88,  5.0, 0.0,     0.8),
    Joint("index_j1",       "hand",   0, 105,  5.0, 0.0,     0.6),
    Joint("middle_j0",      "hand",   0,  88,  5.0, 0.0,     0.8),
    Joint("middle_j1",      "hand",   0, 105,  5.0, 0.0,     0.6),
    Joint("ring_j0",        "hand",   0,  88,  5.0, 0.0,     0.7),
    Joint("ring_j1",        "hand",   0, 105,  5.0, 0.0,     0.5),
    Joint("pinky_j0",       "hand",   0,  88,  5.0, 0.0,     0.6),
    Joint("pinky_j1",       "hand",   0, 105,  5.0, 0.0,     0.4),
]
JOINT_INDEX = {j.name: i for i, j in enumerate(JOINTS)}
ARM_JOINTS = [j.name for j in JOINTS if j.group == "arm"]
HAND_JOINTS = [j.name for j in JOINTS if j.group == "hand"]


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def home_pose():
    return {j.name: j.home for j in JOINTS}


# ---- forward kinematics (for targeting + tests) ---------------------------

def arm_fk(pose):
    """End-effector (x,y,z) in metres for the arm joints in `pose` (deg).

    Azimuth uses G1 `shoulder_yaw`; the planar reach uses shoulder_pitch +
    elbow + wrist_pitch. The other G1 arm joints do not affect this FK.
    """
    yaw = math.radians(pose["shoulder_yaw"])
    a1 = math.radians(pose["shoulder_pitch"])
    a2 = a1 + math.radians(pose["elbow"])
    a3 = a2 + math.radians(pose["wrist_pitch"])
    r = L_UPPER * math.cos(a1) + L_FORE * math.cos(a2) + L_WRIST * math.cos(a3)
    z = L_BASE + L_UPPER * math.sin(a1) + L_FORE * math.sin(a2) + L_WRIST * math.sin(a3)
    return (r * math.cos(yaw), r * math.sin(yaw), z)


def reach_ik(cx, cy, w, h, img_w, img_h):
    """Map a locked pixel bbox to believable arm joint angles (deg).

    Azimuth from horizontal pixel offset; target height from vertical offset;
    reach distance from bbox size (bigger box -> closer). Solves a 2-link
    (upper+fore) planar IK for shoulder/elbow so the elbow bends naturally.
    """
    az = (cx / max(img_w, 1) - 0.5) * 70.0            # deg, +right
    bbox_frac = (w * h) / float(max(img_w * img_h, 1))
    dist = clamp(0.58 - 1.2 * bbox_frac, 0.26, 0.58)  # m, bigger box -> closer
    z_t = 0.10 - (cy / max(img_h, 1) - 0.5) * 0.32    # m, target height vs base

    r_t = dist
    # 2-link IK in the (r, z) plane relative to the shoulder base.
    dr, dz = r_t, z_t - L_BASE
    reach = math.hypot(dr, dz)
    reach = clamp(reach, abs(L_UPPER - L_FORE) + 1e-3, L_UPPER + L_FORE - 1e-3)
    cos_e = (reach * reach - L_UPPER * L_UPPER - L_FORE * L_FORE) / (2 * L_UPPER * L_FORE)
    elbow = math.acos(clamp(cos_e, -1.0, 1.0))        # interior angle
    shoulder = math.atan2(dz, dr) - math.atan2(L_FORE * math.sin(elbow),
                                               L_UPPER + L_FORE * math.cos(elbow))
    pose = home_pose()
    pose["shoulder_yaw"] = clamp(az, -150, 150)
    pose["shoulder_pitch"] = clamp(math.degrees(shoulder), -177, 153)
    pose["elbow"] = clamp(-math.degrees(elbow), -60, 120)
    pose["wrist_pitch"] = clamp(-(pose["shoulder_pitch"] + pose["elbow"]), -92.5, 92.5)
    return pose


def open_hand(pose):
    p = dict(pose)
    for n in HAND_JOINTS:
        p[n] = 2.0  # fingers nearly fully open
    return p


def closed_hand(pose, amount=1.0):
    """Curl the fingers to `amount` (0=open .. 1=full grasp)."""
    p = dict(pose)
    for n in HAND_JOINTS:
        j = JOINTS[JOINT_INDEX[n]]
        p[n] = j.lo + amount * (j.hi - j.lo) * 0.75
    return p


# ---- grasp trajectory (keyframes in joint space) --------------------------

@dataclass
class GraspPlan:
    """Keyframed reach->grasp->lift for a locked target. Times are seconds."""
    target_pose: dict
    keys: list = field(default_factory=list)  # [(t, phase, pose), ...]
    duration: float = 0.0

    @classmethod
    def build(cls, cx, cy, w, h, img_w, img_h):
        home = home_pose()
        reach = reach_ik(cx, cy, w, h, img_w, img_h)
        reach_open = open_hand(reach)
        grasp = closed_hand(reach, 1.0)
        lift = dict(grasp)
        lift["shoulder_pitch"] = clamp(grasp["shoulder_pitch"] + 25.0, -177, 153)
        lift["elbow"] = clamp(grasp["elbow"] + 10.0, -60, 120)
        keys = [
            (0.0, REACHING, home),
            (1.6, REACHING, reach_open),
            (2.2, GRASPING, reach_open),
            (3.2, GRASPING, grasp),
            (3.6, LIFTING, grasp),
            (4.6, LIFTING, lift),
            (5.4, DONE, lift),
        ]
        return cls(target_pose=reach, keys=keys, duration=keys[-1][0])

    def sample(self, t):
        """Return (phase, pose-dict) at time t by eased interpolation."""
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1], dict(ks[0][2])
        if t >= ks[-1][0]:
            return DONE, dict(ks[-1][2])
        for i in range(1, len(ks)):
            t0, ph0, p0 = ks[i - 1]
            t1, ph1, p1 = ks[i]
            if t <= t1:
                u = (t - t0) / max(t1 - t0, 1e-6)
                u = u * u * (3 - 2 * u)              # smoothstep ease
                pose = {n: p0[n] + (p1[n] - p0[n]) * u for n in p0}
                return ph1, pose
        return DONE, dict(ks[-1][2])


# ---- per-motor telemetry simulation ---------------------------------------

AMBIENT_C = 32.0


@dataclass
class MotorState:
    target: float = 0.0      # deg
    actual: float = 0.0      # deg
    vel: float = 0.0         # deg/s
    torque: float = 0.0      # N·m
    current: float = 0.0     # A
    temp: float = AMBIENT_C  # °C
    load: float = 0.0        # %


class MotorSim:
    """First-order joint tracking + derived torque/current/temperature.

    Deterministic (no RNG) so it is unit-testable. Temperature integrates
    current^2 with slow cooling toward ambient.
    """

    def __init__(self, pose=None, tau=0.12):
        pose = pose or home_pose()
        self.tau = tau
        self.m = {j.name: MotorState(target=pose[j.name], actual=pose[j.name])
                  for j in JOINTS}

    def step(self, target_pose, dt, gripper_load=0.0):
        for j in JOINTS:
            s = self.m[j.name]
            s.target = target_pose[j.name]
            prev = s.actual
            prev_v = s.vel
            alpha = clamp(dt / self.tau, 0.0, 1.0)
            s.actual = prev + (s.target - prev) * alpha
            s.vel = (s.actual - prev) / max(dt, 1e-6)
            accel = (s.vel - prev_v) / max(dt, 1e-6)
            # gravity term: pitch joints fight gravity most near horizontal.
            grav = 0.0
            if "pitch" in j.name or "shoulder" in j.name:
                grav = 0.9 * math.cos(math.radians(s.actual))
            # fingers carry the payload while grasping.
            payload = gripper_load * 0.6 if j.group == "hand" else gripper_load * 0.3
            inertia = 0.012 if j.group == "arm" else 0.003
            s.torque = inertia * accel + grav + payload
            s.current = 0.05 + abs(s.torque) * 0.9
            # thermal: heat ∝ current^2, cool toward ambient.
            s.temp += (0.45 * s.current * s.current - 0.06 * (s.temp - AMBIENT_C)) * dt
            s.load = clamp(abs(s.torque) / j.torque_max * 100.0, 0.0, 100.0)

    def snapshot(self):
        out = []
        for j in JOINTS:
            s = self.m[j.name]
            out.append({
                "name": j.name, "group": j.group,
                "target": round(s.target, 1), "actual": round(s.actual, 1),
                "vel": round(s.vel, 1), "torque": round(s.torque, 3),
                "current": round(s.current, 3), "temp": round(s.temp, 1),
                "load": round(s.load, 1),
            })
        return out


# ---- controller / state machine -------------------------------------------

class ArmController:
    """Drives the whole demo: lock -> reach -> grasp -> lift -> reset.

    Thread-safety is the caller's responsibility (the studio server guards
    command() and step() with a lock).
    """

    def __init__(self, img_w=640, img_h=480):
        self.img_w = img_w
        self.img_h = img_h
        self.phase = IDLE
        self.lock = None                 # {class,cx,cy,w,h,score,status}
        self.plan = None
        self.t = 0.0
        self.hold = 0.0                  # dwell timer after DONE
        self.motors = MotorSim()
        self.command_text = ""

    def set_locating(self, text):
        self.command_text = text
        self.phase = LOCATING
        self.lock = {"status": "locating", "class": "", "score": 0.0,
                     "cx": 0, "cy": 0, "w": 0, "h": 0}
        self.plan = None

    def set_lock(self, cls, cx, cy, w, h, score):
        self.lock = {"status": "locked", "class": cls, "score": round(score, 2),
                     "cx": cx, "cy": cy, "w": w, "h": h}
        self.plan = GraspPlan.build(cx, cy, w, h, self.img_w, self.img_h)
        self.phase = REACHING
        self.t = 0.0

    def fail_lock(self, reason="not found"):
        self.lock = {"status": "fallback", "class": "", "score": 0.0,
                     "cx": 0, "cy": 0, "w": 0, "h": 0, "reason": reason}
        self.phase = IDLE

    def step(self, dt):
        target = home_pose()
        gripper_load = 0.0
        if self.plan and self.phase in (REACHING, GRASPING, LIFTING, DONE):
            self.t += dt
            ph, target = self.plan.sample(self.t)
            self.phase = ph
            if ph in (GRASPING, LIFTING):
                gripper_load = 1.0
            if ph == DONE:
                self.hold += dt
                if self.hold > 2.0:      # reset to idle after a short dwell
                    self.phase = IDLE
                    self.plan = None
                    self.lock = None
                    self.hold = 0.0
        self.motors.step(target, dt, gripper_load=gripper_load)

    def gripper_fraction(self):
        # 0 = open, 1 = fully closed (mean finger curl normalised).
        vals = []
        for n in HAND_JOINTS:
            j = JOINTS[JOINT_INDEX[n]]
            s = self.motors.m[n]
            vals.append((s.actual - j.lo) / max(j.hi - j.lo, 1e-6))
        return round(sum(vals) / len(vals), 3)

    def snapshot(self):
        return {
            "phase": self.phase,
            "command": self.command_text,
            "lock": self.lock,
            "gripper": self.gripper_fraction(),
            "joints": self.motors.snapshot(),
        }
