#!/usr/bin/env python3
"""
Train YOLOv8n model for pen and box detection
"""

from ultralytics import YOLO
import torch


def train_model():
    import os

    os.chdir("/home/nvidia/poc/poc-orin")

    print("Starting training...")
    print(f"CUDA available: {torch.cuda.is_available()}")

    # Load pretrained model
    model = YOLO("/home/nvidia/poc/poc-orin/yolov8n.pt")

    # Train
    results = model.train(
        data="/home/nvidia/poc/poc-orin/dataset/dataset.yaml",
        epochs=30,
        imgsz=224,
        batch=8,
        device="cpu",
        verbose=True,
        project="/home/nvidia/poc/poc-orin/models",
        name="pen_box_detector",
        exist_ok=True,
    )

    print("Training complete!")

    # Export to ONNX
    best_model = f"models/pen_box_detector/weights/best.pt"
    model.export(format="onnx", imgsz=224, verbose=True)

    print(f"Model exported to models/pen_box_detector/weights/best.onnx")


if __name__ == "__main__":
    train_model()
