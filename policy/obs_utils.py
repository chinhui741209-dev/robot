#!/usr/bin/env python3
"""
Shared observation/action contract for the policy + BC training pipeline.

This is the SINGLE SOURCE OF TRUTH for the 13-dim observation layout so that
policy_node (deployment), expert_node (BC label source), recorder_node
(dataset capture) and the offline trainer/evaluator can never drift apart.

13-dim observation (matches policy/policy_node.py):
    [ quat_x, quat_y, quat_z, quat_w,        # 0..3  orientation
      gyro_x, gyro_y, gyro_z,                # 4..6  angular velocity (rad/s)
      accel_x, accel_y, accel_z,             # 7..9  linear acceleration (m/s^2)
      det_cx, det_cy, det_score ]            # 10..12 best detection (PIXELS, score 0..1)

32-dim action: joint position targets, normalised to [-1, 1] (policy Tanh output).

The low-level assemble/normalise helpers take plain numbers/arrays so they can be
unit-tested on a host without ROS 2 / rclpy installed. The *_from_msgs helper
extracts from ROS 2 messages and is only used on-device.
"""

import numpy as np

OBS_DIM = 13
ACT_DIM = 32

# Canonical string describing the 13-dim observation layout (recorded into
# dataset metadata for traceability). Single source of truth.
OBS_SCHEMA = "quat4_gyro3_accel3_detcxcyscore3"

# Observation slice indices (for readability / tests).
QUAT = slice(0, 4)
GYRO = slice(4, 7)
ACCEL = slice(7, 10)
DET = slice(10, 13)
I_DET_CX, I_DET_CY, I_DET_SCORE = 10, 11, 12

# Default detection image geometry (perception publishes bbox centre in pixels).
DEFAULT_IMG_W = 640
DEFAULT_IMG_H = 480


def assemble_obs13(quat, gyro, accel, det):
    """Build a (13,) float32 observation from raw components.

    quat: (4,) [x,y,z,w]; gyro: (3,); accel: (3,); det: (3,) [cx, cy, score].
    Pure function — no ROS dependency. Safe to unit-test off-device.
    """
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    obs[QUAT] = np.asarray(quat, dtype=np.float32).ravel()[:4]
    obs[GYRO] = np.asarray(gyro, dtype=np.float32).ravel()[:3]
    obs[ACCEL] = np.asarray(accel, dtype=np.float32).ravel()[:3]
    obs[DET] = np.asarray(det, dtype=np.float32).ravel()[:3]
    return obs


def best_detection(det_msg):
    """Return [cx, cy, score] of the highest-score detection, or zeros.

    Mirrors policy_node.py L123-131 exactly so deployment and training agree.
    """
    if det_msg is not None:
        # Guard against detections with an empty results list (real perception
        # nodes can publish bbox-only detections) — indexing d.results[0] there
        # would raise IndexError inside the subscriber callback.
        cand = [d for d in det_msg.detections if d.results]
        if cand:
            best = max(cand, key=lambda d: d.results[0].hypothesis.score)
            return [
                float(best.bbox.center.position.x),
                float(best.bbox.center.position.y),
                float(best.results[0].hypothesis.score),
            ]
    return [0.0, 0.0, 0.0]


def build_obs13_from_msgs(imu_msg, det_msg):
    """Assemble the 13-dim observation from ROS 2 messages (on-device).

    imu_msg: sensor_msgs/Imu, det_msg: vision_msgs/Detection2DArray (or None).
    Returns (13,) float32 — identical layout to policy_node's inference input.
    """
    quat = [imu_msg.orientation.x, imu_msg.orientation.y,
            imu_msg.orientation.z, imu_msg.orientation.w]
    gyro = [imu_msg.angular_velocity.x, imu_msg.angular_velocity.y,
            imu_msg.angular_velocity.z]
    accel = [imu_msg.linear_acceleration.x, imu_msg.linear_acceleration.y,
             imu_msg.linear_acceleration.z]
    return assemble_obs13(quat, gyro, accel, best_detection(det_msg))


def quat_to_roll_pitch(quat):
    """Convert quaternion [x,y,z,w] to (roll, pitch) in radians. Pure helper."""
    x, y, z, w = (float(quat[0]), float(quat[1]), float(quat[2]), float(quat[3]))
    # roll (x-axis)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)
    # pitch (y-axis)
    sinp = 2.0 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = np.arcsin(sinp)
    return float(roll), float(pitch)
