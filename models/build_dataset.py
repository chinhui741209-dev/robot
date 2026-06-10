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

    # Split each shard contiguously (head -> train, tail -> val). A global shuffle
    # + front-slice would leak temporally-adjacent frames across train/val (50 Hz
    # trajectories are highly correlated), inflating val performance.
    tr_o, tr_a, va_o, va_a = [], [], [], []
    for f in shards:
        d = np.load(f, allow_pickle=True)
        o = d["obs"].astype(np.float32); a = d["act"].astype(np.float32)
        n = len(o)
        nv = max(1, int(n * args.val_frac)) if n > 1 else 0
        if 0 < nv < n:
            tr_o.append(o[:-nv]); tr_a.append(a[:-nv])
            va_o.append(o[-nv:]); va_a.append(a[-nv:])
        else:
            tr_o.append(o); tr_a.append(a)
        print(f"  loaded {f}: obs={o.shape} act={a.shape} (val tail {nv})")

    tr_obs = np.concatenate(tr_o, axis=0)
    tr_act = np.concatenate(tr_a, axis=0)
    val_obs = np.concatenate(va_o, axis=0) if va_o else np.empty((0, OBS_DIM), np.float32)
    val_act = np.concatenate(va_a, axis=0) if va_a else np.empty((0, ACT_DIM), np.float32)
    assert tr_obs.shape[1] == OBS_DIM, f"obs dim {tr_obs.shape[1]} != {OBS_DIM}"
    assert tr_act.shape[1] == ACT_DIM, f"act dim {tr_act.shape[1]} != {ACT_DIM}"

    # Drop rows with NaN/Inf in either obs or act.
    def _finite(o, a):
        good = np.isfinite(o).all(axis=1) & np.isfinite(a).all(axis=1)
        return o[good], a[good], int((~good).sum())
    tr_obs, tr_act, d1 = _finite(tr_obs, tr_act)
    val_obs, val_act, d2 = _finite(val_obs, val_act)
    if d1 + d2:
        print(f"  dropped {d1 + d2} non-finite rows")

    # Shuffle TRAIN only (val order is irrelevant).
    rng = np.random.default_rng(args.seed)
    perm = rng.permutation(len(tr_obs))
    tr_obs, tr_act = tr_obs[perm], tr_act[perm]

    os.makedirs(args.out, exist_ok=True)
    tr_path = os.path.join(args.out, "dataset_train.npz")
    val_path = os.path.join(args.out, "dataset_val.npz")
    np.savez(tr_path, obs=tr_obs, act=tr_act)
    np.savez(val_path, obs=val_obs, act=val_act)
    print(f"train: {tr_obs.shape[0]} -> {tr_path}")
    print(f"val:   {val_obs.shape[0]} -> {val_path}")


if __name__ == "__main__":
    main()
