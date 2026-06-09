#!/usr/bin/env python3
"""
Behavior-Cloning trainer for the locomotion policy.

Replaces the random-initialised simple_policy.onnx with a network trained to
imitate the ScriptedExpert (supervised MSE on obs->act pairs). Reuses the
deployment model class (SimpleLocomotionPolicy) and ONNX export settings so the
trained artifact drops straight into policy_node with no shape/opset drift.

Runs on CPU or CUDA (Orin is currently CPU-only; the MLP is tiny). The trained
ONNX is written to models/candidate/ (promote-after-review), NOT models/active/.

Usage:
    python3 models/train_policy.py --train data/bc/dataset_train.npz \
        --val data/bc/dataset_val.npz --epochs 50 --out models/candidate
"""

import argparse
import os
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

from models.generate_simple_policy import SimpleLocomotionPolicy, export_onnx
from policy.obs_utils import OBS_DIM, ACT_DIM


def load_npz(path):
    d = np.load(path, allow_pickle=True)
    return (torch.from_numpy(d["obs"].astype(np.float32)),
            torch.from_numpy(d["act"].astype(np.float32)))


def evaluate(model, loader, device, loss_fn):
    model.eval()
    total, n = 0.0, 0
    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            total += loss_fn(model(xb), yb).item() * len(xb)
            n += len(xb)
    return total / max(n, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default="data/bc/dataset_train.npz")
    ap.add_argument("--val", default="data/bc/dataset_val.npz")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="models/candidate")
    ap.add_argument("--tag", default="bc")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}")

    tr_x, tr_y = load_npz(args.train)
    val_x, val_y = load_npz(args.val)
    assert tr_x.shape[1] == OBS_DIM and tr_y.shape[1] == ACT_DIM

    tr_loader = DataLoader(TensorDataset(tr_x, tr_y), batch_size=args.batch, shuffle=True)
    val_loader = DataLoader(TensorDataset(val_x, val_y), batch_size=args.batch)

    model = SimpleLocomotionPolicy(input_dim=OBS_DIM, hidden_dim=args.hidden,
                                   output_dim=ACT_DIM).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = torch.nn.MSELoss()

    best_val = float("inf")
    best_state = None
    for ep in range(1, args.epochs + 1):
        model.train()
        run, n = 0.0, 0
        for xb, yb in tr_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            run += loss.item() * len(xb)
            n += len(xb)
        train_mse = run / max(n, 1)
        val_mse = evaluate(model, val_loader, device, loss_fn)
        if val_mse < best_val:
            best_val = val_mse
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if ep == 1 or ep % 5 == 0 or ep == args.epochs:
            print(f"epoch {ep:3d}  train_mse={train_mse:.5f}  val_mse={val_mse:.5f}")

    print(f"best val_mse={best_val:.5f}")
    model.load_state_dict(best_state)

    os.makedirs(args.out, exist_ok=True)
    onnx_path = os.path.join(args.out, f"simple_policy_{args.tag}.onnx")
    export_onnx(model.cpu(), onnx_path, input_dim=OBS_DIM)

    # Also save a torch checkpoint for evaluation / reproducibility (eval_policy
    # loads this so it runs without onnxruntime, e.g. on the dev host).
    pt_path = os.path.join(args.out, f"simple_policy_{args.tag}.pt")
    torch.save({"state_dict": model.state_dict(), "hidden": args.hidden,
                "obs_dim": OBS_DIM, "act_dim": ACT_DIM, "best_val_mse": best_val},
               pt_path)
    print(f"checkpoint saved: {pt_path}")

    # Numerical parity check torch-vs-onnx if onnxruntime is available.
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(onnx_path)
        x = val_x[: min(8, len(val_x))].numpy()
        torch_out = model(torch.from_numpy(x)).detach().numpy()
        onnx_out = sess.run(None, {sess.get_inputs()[0].name: x})[0]
        max_diff = float(np.abs(torch_out - onnx_out).max())
        print(f"torch-vs-onnx max abs diff = {max_diff:.2e}")
    except Exception as e:
        print(f"(skipped onnx parity check: {e})")


if __name__ == "__main__":
    main()
