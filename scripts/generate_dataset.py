#!/usr/bin/env python3
"""
Synthetic detection dataset generator (Phase 3).

Multi-class + domain randomization, driven by perception/classes.py so the
class list is consistent across perception / dataset / training. Emits YOLO-
format labels (class cx cy w h, normalized) and dataset.yaml. Replaces the old
pen/box-only generator and the deprecated np.int0 call (-> np.intp).

Usage:
    python3 scripts/generate_dataset.py --num 200 --out dataset
    POC_CLASSES=pen,box,apple,orange python3 scripts/generate_dataset.py --num 300
"""

import argparse
import os
import sys
import random

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from perception.classes import get_class_names

# Per-class appearance hints; unknown classes fall back to a random rectangle.
SHAPES = {
    "pen":    {"kind": "rect", "color": (0, 0, 255),   "w": (12, 26),  "h": (70, 150), "rot": True},
    "box":    {"kind": "rect", "color": (255, 0, 0),   "w": (70, 150), "h": (55, 120), "rot": False},
    "apple":  {"kind": "circle", "color": (40, 40, 220), "r": (22, 40)},
    "orange": {"kind": "circle", "color": (40, 150, 240), "r": (22, 40)},
}


def _rand_color():
    return tuple(int(c) for c in np.random.randint(40, 220, 3))


def draw_object(img, cls, W, H):
    """Draw one instance of class `cls`; return YOLO bbox (cxn,cyn,wn,hn)."""
    spec = SHAPES.get(cls, {"kind": "rect", "color": _rand_color(),
                            "w": (40, 90), "h": (40, 90), "rot": True})
    cx, cy = random.randint(int(W * 0.15), int(W * 0.85)), random.randint(int(H * 0.15), int(H * 0.85))
    if spec["kind"] == "circle":
        r = random.randint(*spec["r"])
        cv2.circle(img, (cx, cy), r, spec["color"], -1)
        bw = bh = 2 * r
    else:
        w = random.randint(*spec["w"]); h = random.randint(*spec["h"])
        if spec.get("rot"):
            angle = random.uniform(-35, 35)
            box = cv2.boxPoints(((cx, cy), (w, h), angle))
            cv2.drawContours(img, [np.intp(box)], 0, spec["color"], -1)  # np.int0 was removed in NumPy 2
            bw = bh = max(w, h)  # axis-aligned bound approx for rotated rect
        else:
            cv2.rectangle(img, (cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2), spec["color"], -1)
            bw, bh = w, h
    return (cx / W, cy / H, bw / W, bh / H)


def domain_randomize(img):
    H, W = img.shape[:2]
    img = img.astype(np.int16)
    img += np.random.randint(-25, 25, img.shape, dtype=np.int16)          # noise
    img = (img * np.random.uniform(0.7, 1.3) + np.random.randint(-30, 30))  # brightness/contrast
    return np.clip(img, 0, 255).astype(np.uint8)


def generate(out_dir, num, classes, W=640, H=640, seed=0):
    random.seed(seed); np.random.seed(seed)
    img_dir = os.path.join(out_dir, "images", "train")
    lbl_dir = os.path.join(out_dir, "labels", "train")
    os.makedirs(img_dir, exist_ok=True); os.makedirs(lbl_dir, exist_ok=True)

    for i in range(num):
        base = np.random.randint(80, 200)
        img = np.full((H, W, 3), base, np.uint8)
        labels = []
        for ci, cls in enumerate(classes):
            for _ in range(random.randint(0, 2)):        # 0-2 instances per class
                cxn, cyn, wn, hn = draw_object(img, cls, W, H)
                labels.append(f"{ci} {cxn:.4f} {cyn:.4f} {wn:.4f} {hn:.4f}")
        for _ in range(random.randint(0, 3)):            # unlabeled distractors
            cv2.ellipse(img, (random.randint(0, W), random.randint(0, H)),
                        (random.randint(8, 30), random.randint(8, 30)), 0, 0, 360, _rand_color(), -1)
        img = domain_randomize(img)
        cv2.imwrite(os.path.join(img_dir, f"image_{i:04d}.jpg"), img)
        with open(os.path.join(lbl_dir, f"image_{i:04d}.txt"), "w") as f:
            f.write("\n".join(labels))

    with open(os.path.join(out_dir, "dataset.yaml"), "w") as f:
        f.write(f"train: {os.path.join(out_dir, 'images', 'train')}\n"
                f"val: {os.path.join(out_dir, 'images', 'train')}\n"
                f"nc: {len(classes)}\nnames: {list(classes)}\n")
    print(f"Generated {num} images, classes={classes} -> {out_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--num", type=int, default=200)
    ap.add_argument("--out", default="dataset")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    generate(args.out, args.num, get_class_names(), seed=args.seed)


if __name__ == "__main__":
    main()
