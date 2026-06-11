#!/usr/bin/env python3
"""
Monocular 3D back-projection (pure, no ROS/cv2 — unit-testable on host).

Pinhole camera model. Given a pixel (u, v) and a depth Z (metres) in the camera
frame, recover the 3D point; and the inverse projection. The RGB USB camera has
no depth sensor, so depth comes either from sim ground-truth or from a VLM
distance estimate (ClaudeVisionDetector) — this module only does the geometry.

Camera frame convention (matches OpenCV / REP-103 optical frame):
  +X right, +Y down, +Z forward (into the scene). u increases right, v down.
"""

import math


class CameraIntrinsics:
    def __init__(self, fx, fy, cx, cy):
        self.fx = float(fx)
        self.fy = float(fy)
        self.cx = float(cx)
        self.cy = float(cy)

    @classmethod
    def from_fov(cls, width, height, hfov_deg=70.0):
        """Build intrinsics from image size + horizontal FOV (square pixels)."""
        fx = (width / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)
        return cls(fx=fx, fy=fx, cx=width / 2.0, cy=height / 2.0)

    def __repr__(self):
        return f"CameraIntrinsics(fx={self.fx:.1f}, fy={self.fy:.1f}, cx={self.cx:.1f}, cy={self.cy:.1f})"


def backproject(u, v, depth, intr):
    """Pixel (u,v) + depth Z (m) -> (X, Y, Z) in camera frame (metres)."""
    z = float(depth)
    x = (float(u) - intr.cx) * z / intr.fx
    y = (float(v) - intr.cy) * z / intr.fy
    return (x, y, z)


def project(x, y, z, intr):
    """(X,Y,Z) camera-frame point -> (u, v, depth). z must be > 0."""
    if z <= 0:
        raise ValueError("project requires z > 0 (point in front of camera)")
    u = intr.fx * x / z + intr.cx
    v = intr.fy * y / z + intr.cy
    return (u, v, z)
