#!/usr/bin/env python3
"""
Simple Object Detection Model Generator
 Generates a simple CNN-based detection model for robot perception.
 Input: 3x224x224 image
 Output: 5-dim (bbox_x, bbox_y, width, height, confidence)
"""

import torch
import torch.nn as nn


class SimpleDetection(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 28 * 28, 128),
            nn.ReLU(),
            nn.Linear(128, 5),
            nn.Sigmoid(),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.fc(x)
        return x


def generate_detection_model(output_path="models/active/detection.onnx"):
    model = SimpleDetection()
    model.eval()

    dummy_input = torch.zeros(1, 3, 224, 224)

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        input_names=["image"],
        output_names=["detection_output"],
        dynamic_axes={
            "image": {0: "batch_size"},
            "detection_output": {0: "batch_size"},
        },
        opset_version=18,
    )

    print(f"Detection model saved to: {output_path}")

    import onnx

    model_onnx = onnx.load(output_path)
    onnx.checker.check_model(model_onnx)
    print("ONNX model validated")


if __name__ == "__main__":
    generate_detection_model()
