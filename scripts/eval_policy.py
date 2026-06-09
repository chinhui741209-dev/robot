#!/usr/bin/env python3
"""
Evaluate a BC-trained policy against the expert (target) and a random baseline.

Runs all three policies over the SAME fixed-seed SimObsSource sequence so the
comparison is apples-to-apples, and reports:
  - action-MSE vs expert  (the direct BC objective; expert == 0 by definition)
  - turn-direction agreement with the expert on the J_YAW joint (task proxy:
    does the policy turn toward the detected target the way the expert does?)

Loads the trained model from a torch checkpoint (.pt from train_policy.py) so it
runs without onnxruntime on the dev host. torch-vs-onnx parity is already
checked at export time.

Usage:
    python3 scripts/eval_policy.py --model models/candidate/simple_policy_bc.pt
"""

import argparse
import os
import numpy as np
import torch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.generate_simple_policy import SimpleLocomotionPolicy
from policy.obs_utils import OBS_DIM, ACT_DIM
from policy.scripted_expert import ScriptedExpert, J_YAW
from scripts.collect_bc_dataset import SimObsSource


def load_torch_policy(pt_path):
    ckpt = torch.load(pt_path, map_location="cpu")
    model = SimpleLocomotionPolicy(input_dim=ckpt.get("obs_dim", OBS_DIM),
                                   hidden_dim=ckpt.get("hidden", 64),
                                   output_dim=ckpt.get("act_dim", ACT_DIM))
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model


def run_policy_torch(model, obs_batch):
    with torch.no_grad():
        return model(torch.from_numpy(obs_batch)).numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/candidate/simple_policy_bc.pt",
                    help="trained torch checkpoint (.pt)")
    ap.add_argument("--steps", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=123, help="eval seed (≠ train seed)")
    args = ap.parse_args()

    # Build a fresh eval observation sequence + expert labels.
    src = SimObsSource(seed=args.seed)
    expert = ScriptedExpert()
    obs = np.stack([src.step() for _ in range(args.steps)]).astype(np.float32)
    expert_act = np.stack([expert.act(o) for o in obs]).astype(np.float32)

    # Trained policy.
    trained = load_torch_policy(args.model)
    trained_act = run_policy_torch(trained, obs)

    # Random baseline (fresh untrained net — what the system shipped before BC).
    torch.manual_seed(0)
    random_model = SimpleLocomotionPolicy(input_dim=OBS_DIM, hidden_dim=64, output_dim=ACT_DIM)
    random_act = run_policy_torch(random_model, obs)

    def action_mse(a):
        return float(np.mean((a - expert_act) ** 2))

    def yaw_dir_agreement(a):
        # Fraction of confident-target steps where policy & expert agree on turn sign.
        mask = np.abs(expert_act[:, J_YAW]) > 1e-3
        if mask.sum() == 0:
            return float("nan")
        return float(np.mean(np.sign(a[mask, J_YAW]) == np.sign(expert_act[mask, J_YAW])))

    print(f"eval steps={args.steps} seed={args.seed}")
    print(f"{'policy':<10} {'action-MSE':>12} {'yaw-dir-agree':>14}")
    for name, a in (("expert", expert_act), ("trained", trained_act), ("random", random_act)):
        print(f"{name:<10} {action_mse(a):>12.5f} {yaw_dir_agreement(a):>14.3f}")

    trained_mse, random_mse = action_mse(trained_act), action_mse(random_act)
    verdict = "PASS" if trained_mse < 0.25 * random_mse else "WEAK"
    print(f"\n[{verdict}] trained action-MSE is "
          f"{random_mse / max(trained_mse, 1e-9):.1f}x lower than random.")


if __name__ == "__main__":
    main()
