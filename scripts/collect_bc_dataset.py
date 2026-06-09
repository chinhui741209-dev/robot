#!/usr/bin/env python3
"""
Offline Behavior-Cloning data collector (host / Mac, no ROS 2 required).

Generates synthetic 13-dim observations (plausible IMU motion + a detection
target sweeping across the frame) and labels each with the ScriptedExpert's
32-dim action, saving (obs, act) to a .npz. This is the fast off-device path to
validate the BC train->eval machinery before recording the real ROS 2 dataset
on the Orin (see policy/expert_node.py + middleware/recorder_node.py).

Usage:
    python3 scripts/collect_bc_dataset.py --steps 20000 --seed 0 --out data/bc
"""

import argparse
import os
import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy.obs_utils import assemble_obs13, OBS_DIM, ACT_DIM, DEFAULT_IMG_W, DEFAULT_IMG_H
from policy.scripted_expert import ScriptedExpert, EXPERT_VERSION, OBS_SCHEMA


class SimObsSource:
    """Synthetic observation generator (numpy only).

    Body slowly oscillates in roll/pitch (quaternion), gyro tracks the rate,
    accel = gravity + noise, and a detection target sweeps across the image
    with occasional confidence dropouts.
    """

    def __init__(self, seed=0, img_w=DEFAULT_IMG_W, img_h=DEFAULT_IMG_H, dt=0.02):
        self.rng = np.random.default_rng(seed)
        self.img_w = img_w
        self.img_h = img_h
        self.dt = dt
        self.t = 0.0
        self._phase = self.rng.uniform(0, 2 * np.pi, size=2)
        self._freq = self.rng.uniform(0.2, 0.8, size=2)

    @staticmethod
    def _rpy_to_quat(roll, pitch, yaw=0.0):
        cr, sr = np.cos(roll / 2), np.sin(roll / 2)
        cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
        cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        w = cr * cp * cy + sr * sp * sy
        return np.array([x, y, z, w], dtype=np.float32)

    def step(self):
        self.t += self.dt
        # Oscillating roll/pitch (radians), amplitude ~0.25 rad (~14 deg).
        roll = 0.25 * np.sin(self._freq[0] * self.t + self._phase[0])
        pitch = 0.25 * np.sin(self._freq[1] * self.t + self._phase[1])
        # Gyro ~ d/dt of the angles + noise.
        gx = 0.25 * self._freq[0] * np.cos(self._freq[0] * self.t + self._phase[0])
        gy = 0.25 * self._freq[1] * np.cos(self._freq[1] * self.t + self._phase[1])
        gyro = np.array([gx, gy, 0.0]) + self.rng.normal(0, 0.01, 3)
        # Accel = gravity (z up) + small noise.
        accel = np.array([0.0, 0.0, 9.81]) + self.rng.normal(0, 0.05, 3)
        quat = self._rpy_to_quat(roll, pitch)

        # Detection target sweeping horizontally + bobbing vertically (pixels).
        cx = (0.5 + 0.4 * np.sin(0.5 * self.t)) * self.img_w
        cy = (0.5 + 0.2 * np.cos(0.3 * self.t)) * self.img_h
        # Occasional low-confidence dropout (~15%).
        score = 0.0 if self.rng.random() < 0.15 else float(self.rng.uniform(0.5, 0.95))
        det = [cx, cy, score]

        return assemble_obs13(quat, gyro, accel, det)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/bc")
    ap.add_argument("--noise", type=float, default=0.0,
                    help="expert action noise sigma (0 = deterministic)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    src = SimObsSource(seed=args.seed)
    expert = ScriptedExpert()
    rng = np.random.default_rng(args.seed + 1)

    obs_buf = np.zeros((args.steps, OBS_DIM), dtype=np.float32)
    act_buf = np.zeros((args.steps, ACT_DIM), dtype=np.float32)
    for i in range(args.steps):
        o = src.step()
        a = expert.act_noisy(o, sigma=args.noise, rng=rng) if args.noise > 0 else expert.act(o)
        obs_buf[i] = o
        act_buf[i] = a

    out_path = os.path.join(args.out, f"expert_seed{args.seed}_n{args.steps}.npz")
    np.savez(
        out_path,
        obs=obs_buf,
        act=act_buf,
        meta=np.array(
            f"source=SimObsSource;expert={EXPERT_VERSION};obs_schema={OBS_SCHEMA};"
            f"seed={args.seed};steps={args.steps};noise={args.noise}"
        ),
    )
    print(f"Wrote {args.steps} (obs,act) pairs -> {out_path}")
    print(f"  obs shape={obs_buf.shape} act shape={act_buf.shape} "
          f"act range=[{act_buf.min():.3f}, {act_buf.max():.3f}]")


if __name__ == "__main__":
    main()
