#!/usr/bin/env python3
"""
Build a BC training set from collected (obs, act) .npz shards.

Merges every data/bc/*.npz (from scripts/collect_bc_dataset.py on host, or
middleware/recorder_node.py on the Orin), drops NaN rows, shuffles, and splits
into train/val. Observations are intentionally NOT standardised — the policy is
fed raw observations at deployment (policy_node), so the training distribution
must match exactly to avoid a deploy-time shift.

Usage:
    python3 models/build_dataset.py --in data/bc --out data/bc --val-frac 0.1
"""

import argparse
import glob
import os
import numpy as np

from policy.obs_utils import OBS_DIM, ACT_DIM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", default="data/bc")
    ap.add_argument("--out", default="data/bc")
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    shards = sorted(
        f for f in glob.glob(os.path.join(args.indir, "*.npz"))
        if os.path.basename(f) not in ("dataset_train.npz", "dataset_val.npz")
    )
    if not shards:
        raise SystemExit(f"No .npz shards found in {args.indir}")

    obs_list, act_list = [], []
    for f in shards:
        d = np.load(f, allow_pickle=True)
        obs_list.append(d["obs"].astype(np.float32))
        act_list.append(d["act"].astype(np.float32))
        print(f"  loaded {f}: obs={d['obs'].shape} act={d['act'].shape}")

    obs = np.concatenate(obs_list, axis=0)
    act = np.concatenate(act_list, axis=0)
    assert obs.shape[1] == OBS_DIM, f"obs dim {obs.shape[1]} != {OBS_DIM}"
    assert act.shape[1] == ACT_DIM, f"act dim {act.shape[1]} != {ACT_DIM}"

    # Drop rows with NaN/Inf in either obs or act.
    good = np.isfinite(obs).all(axis=1) & np.isfinite(act).all(axis=1)
    dropped = int((~good).sum())
    obs, act = obs[good], act[good]
    if dropped:
        print(f"  dropped {dropped} non-finite rows")

    rng = np.random.default_rng(args.seed)
    perm = rng.permutation(len(obs))
    obs, act = obs[perm], act[perm]

    n_val = max(1, int(len(obs) * args.val_frac))
    val_obs, val_act = obs[:n_val], act[:n_val]
    tr_obs, tr_act = obs[n_val:], act[n_val:]

    os.makedirs(args.out, exist_ok=True)
    tr_path = os.path.join(args.out, "dataset_train.npz")
    val_path = os.path.join(args.out, "dataset_val.npz")
    np.savez(tr_path, obs=tr_obs, act=tr_act)
    np.savez(val_path, obs=val_obs, act=val_act)
    print(f"train: {tr_obs.shape[0]} -> {tr_path}")
    print(f"val:   {val_obs.shape[0]} -> {val_path}")


if __name__ == "__main__":
    main()
