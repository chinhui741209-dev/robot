#!/usr/bin/env python3
"""
Generate synthetic dataset for pen and box detection
 Creates simple geometric shapes to simulate pen and box
"""

import os
import random
import cv2
import numpy as np
from pathlib import Path


def generate_dataset(output_dir="dataset", num_images=100):
    """Generate synthetic images with pen and box"""

    output_path = Path(output_dir)
    images_path = output_path / "images" / "train"
    labels_path = output_path / "labels" / "train"

    images_path.mkdir(parents=True, exist_ok=True)
    labels_path.mkdir(parents=True, exist_ok=True)

    # Class: 0=pen, 1=box
    classes = ["pen", "box"]

    for i in range(num_images):
        # Create image
        img = np.ones((640, 640, 3), dtype=np.uint8) * 240

        # Random background noise
        noise = np.random.randint(-20, 20, (640, 640, 3), dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        labels = []

        # Add pen (thin rectangle)
        pen_x = random.randint(100, 400)
        pen_y = random.randint(100, 400)
        pen_w = random.randint(15, 30)
        pen_h = random.randint(80, 150)
        pen_angle = random.uniform(-30, 30)

        # Draw pen
        center = (pen_x, pen_y)
        rect = (center, (pen_w, pen_h), pen_angle)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        cv2.drawContours(img, [box], 0, (0, 0, 255), -1)  # Red pen

        # YOLO format: class x_center y_center width height (normalized)
        labels.append(
            f"0 {(pen_x / 640):.4f} {(pen_y / 640):.4f} {(pen_w / 640):.4f} {(pen_h / 640):.4f}"
        )

        # Add box (larger rectangle)
        box_x = random.randint(300, 500)
        box_y = random.randint(200, 450)
        box_w = random.randint(80, 150)
        box_h = random.randint(60, 120)

        # Draw box
        cv2.rectangle(
            img,
            (box_x - box_w // 2, box_y - box_h // 2),
            (box_x + box_w // 2, box_y + box_h // 2),
            (255, 0, 0),
            -1,
        )  # Blue box

        labels.append(
            f"1 {((box_x) / 640):.4f} {((box_y) / 640):.4f} {(box_w / 640):.4f} {(box_h / 640):.4f}"
        )

        # Add some random objects as distraction
        for _ in range(random.randint(0, 3)):
            ox = random.randint(50, 590)
            oy = random.randint(50, 590)
            ow = random.randint(20, 50)
            oh = random.randint(20, 50)
            cv2.ellipse(
                img, (ox, oy), (ow // 2, oh // 2), 0, 0, 360, (100, 100, 100), -1
            )

        # Save image
        cv2.imwrite(str(images_path / f"image_{i:04d}.jpg"), img)

        # Save label
        with open(labels_path / f"image_{i:04d}.txt", "w") as f:
            f.write("\n".join(labels))

    # Create dataset.yaml
    yaml_content = f"""
train: {output_dir}/images/train
val: {output_dir}/images/train

nc: 2
names: {classes}
"""
    with open(output_path / "dataset.yaml", "w") as f:
        f.write(yaml_content)

    print(f"Generated {num_images} images in {output_dir}")
    print(f"Classes: {classes}")


if __name__ == "__main__":
    generate_dataset(num_images=50)
