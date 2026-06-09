#!/usr/bin/env python3
"""
Scripted expert policy — the demonstration/label source for Behavior Cloning.

In pure simulation there is no human teleoperation, so we synthesise a
deterministic, *interpretable* rule-based controller that maps the 13-dim
observation to 32-dim joint targets in [-1, 1]. The BC network is then trained
to imitate this expert. This is intentionally a toy teaching signal for the
POC; it is the piece that would later be replaced by recorded human demos or a
higher-fidelity controller.

Behaviour (documented for the unit-test spec, ASPICE SWE.4):
  - Posture hold: a few designated joints counteract body roll/pitch (P term on
    quaternion-derived angles) with a damping term on gyro.
  - Turn-to-target: when the best detection is confident (score >= threshold),
    a "yaw" joint turns toward the target's horizontal pixel offset and a
    "reach" joint responds to its vertical offset; below threshold these are
    disabled (no chasing of noise).
  - All other joints rest at neutral (0).
  - Output is clipped to [-1, 1] to match the policy's Tanh range.

Pure numpy — no ROS / torch dependency, so it is unit-testable off-device and
reusable by the offline evaluator.
"""

import numpy as np

from policy.obs_utils import (
    ACT_DIM, GYRO, I_DET_CX, I_DET_CY, I_DET_SCORE,
    DEFAULT_IMG_W, DEFAULT_IMG_H, quat_to_roll_pitch, OBS_SCHEMA,
)

# Designated joint indices driven by the expert (rest stay at neutral 0).
J_ROLL = 0
J_PITCH = 1
J_YAW = 2
J_REACH = 3


class ScriptedExpert:
    def __init__(self, img_w=DEFAULT_IMG_W, img_h=DEFAULT_IMG_H,
                 score_thresh=0.3, kp_roll=1.2, kp_pitch=1.2, kd_gyro=0.05,
                 k_yaw=1.0, k_reach=1.0):
        self.img_w = float(img_w)
        self.img_h = float(img_h)
        self.score_thresh = float(score_thresh)
        self.kp_roll = float(kp_roll)
        self.kp_pitch = float(kp_pitch)
        self.kd_gyro = float(kd_gyro)
        self.k_yaw = float(k_yaw)
        self.k_reach = float(k_reach)

    def act(self, obs):
        """obs: (13,) array -> action: (32,) array in [-1, 1]."""
        obs = np.asarray(obs, dtype=np.float32).ravel()
        action = np.zeros(ACT_DIM, dtype=np.float32)

        # --- Posture hold from orientation + gyro damping ---
        roll, pitch = quat_to_roll_pitch(obs[0:4])
        gyro = obs[GYRO]
        action[J_ROLL] = -self.kp_roll * roll - self.kd_gyro * float(gyro[0])
        action[J_PITCH] = -self.kp_pitch * pitch - self.kd_gyro * float(gyro[1])

        # --- Turn-to-target, gated on detection confidence ---
        score = float(obs[I_DET_SCORE])
        if score >= self.score_thresh:
            # Normalised pixel offsets in [-1, 1] (centre of image = 0).
            e_x = (float(obs[I_DET_CX]) - self.img_w / 2.0) / (self.img_w / 2.0)
            e_y = (float(obs[I_DET_CY]) - self.img_h / 2.0) / (self.img_h / 2.0)
            action[J_YAW] = -self.k_yaw * e_x        # turn toward target
            action[J_REACH] = -self.k_reach * e_y    # reach up/down toward target

        return np.clip(action, -1.0, 1.0).astype(np.float32)

    def act_noisy(self, obs, sigma=0.02, rng=None):
        """Expert action with small Gaussian noise (for data augmentation / DAgger)."""
        rng = rng if rng is not None else np.random
        a = self.act(obs) + rng.normal(0.0, sigma, size=ACT_DIM).astype(np.float32)
        return np.clip(a, -1.0, 1.0).astype(np.float32)


# Metadata recorded into datasets for traceability.
# OBS_SCHEMA is re-exported from obs_utils (single source of truth) so callers
# can import either the expert version or the obs schema from here.
EXPERT_VERSION = "scripted_expert/v1"
__all__ = ["ScriptedExpert", "EXPERT_VERSION", "OBS_SCHEMA",
           "J_ROLL", "J_PITCH", "J_YAW", "J_REACH"]
