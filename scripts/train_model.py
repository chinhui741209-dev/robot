#!/usr/bin/env python3
"""
Train a YOLOv8 detector on the synthetic dataset (Phase 3, portable).

De-hardcoded: no os.chdir("/home/nvidia/..."), paths resolve against POC_ROOT,
device is selectable (auto-detects CUDA, falls back to CPU — the Orin is
currently CPU-only). Exports ONNX consumable by perception_node + the shared
YOLOv8 decoder.

Usage:
    python3 scripts/train_model.py --data dataset/dataset.yaml --epochs 30 --device auto
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from perception.classes import resolve_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="dataset/dataset.yaml")
    ap.add_argument("--weights", default="yolov8n.pt")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="auto", help="auto|cpu|0|0,1")
    ap.add_argument("--project", default="models")
    ap.add_argument("--name", default="detector")
    args = ap.parse_args()

    from ultralytics import YOLO
    import torch

    device = args.device
    if device == "auto":
        device = "0" if torch.cuda.is_available() else "cpu"
    print(f"Training device={device}  CUDA available={torch.cuda.is_available()}")

    data = resolve_path(args.data)
    project = resolve_path(args.project)

    # Prefer pretrained weights (ultralytics auto-downloads); fall back to
    # training from the architecture spec if the download is unavailable.
    try:
        model = YOLO(args.weights)
    except Exception as e:
        print(f"pretrained '{args.weights}' unavailable ({e}); training from scratch (yolov8n.yaml)")
        model = YOLO("yolov8n.yaml")
    model.train(data=data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                device=device, project=project, name=args.name, exist_ok=True, verbose=True)

    out = model.export(format="onnx", imgsz=args.imgsz)
    print(f"Training complete. Exported ONNX: {out}")
    print(f"Promote with: cp {out} {resolve_path('models/active/detection_v2.onnx')}")


if __name__ == "__main__":
    main()
