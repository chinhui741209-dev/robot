#!/usr/bin/env python3
"""
Simple Locomotion Policy Model Generator
 Generates a simple MLP policy model for robot locomotion control.
 Input: 13-dim sensor state (Quat(4) + Gyro(3) + Accel(3) + Detection(3))
 Output: 32-dim action (joint position targets for 32-DOF robot)
"""

import torch
import torch.nn as nn
import os


class SimpleLocomotionPolicy(nn.Module):
    def __init__(self, input_dim=13, hidden_dim=64, output_dim=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim),
            nn.Tanh(),
        )

    def forward(self, x):
        return self.net(x)


def export_onnx(model, output_path, input_dim=13):
    """Export a (trained or fresh) SimpleLocomotionPolicy to ONNX.

    Shared by generate_model() and models/train_policy.py so the export
    settings (names, dynamic batch axis, opset) never drift. Exports a single
    self-contained .onnx (no external .data side-file).
    """
    model = model.eval()
    dummy_input = torch.zeros(1, input_dim)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        input_names=["sensor_input"],
        output_names=["action_output"],
        dynamic_axes={
            "sensor_input": {0: "batch_size"},
            "action_output": {0: "batch_size"},
        },
        opset_version=13,
    )

    import onnx

    model_onnx = onnx.load(output_path)
    onnx.checker.check_model(model_onnx)
    print(f"Model saved + validated: {output_path}")
    return output_path


def generate_model(output_path="models/active/simple_policy.onnx"):
    model = SimpleLocomotionPolicy(input_dim=13, hidden_dim=64, output_dim=32)
    return export_onnx(model, output_path, input_dim=13)


if __name__ == "__main__":
    generate_model()
