#!/usr/bin/env python3
"""
Unit tests for monocular 3D back-projection (pure; the Phase 4 GT validation).
Run: PYTHONPATH=. pytest tests/test_projection.py -v
"""

import os
import sys
import math

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.projection import CameraIntrinsics, backproject, project


def test_from_fov_center_is_principal_point():
    intr = CameraIntrinsics.from_fov(640, 480, hfov_deg=90.0)
    # 90deg HFOV on 640px -> fx = 320 / tan(45) = 320
    assert abs(intr.fx - 320.0) < 1e-6
    assert intr.cx == 320.0 and intr.cy == 240.0
    # principal-point pixel at depth Z -> X=Y=0
    X, Y, Z = backproject(320.0, 240.0, 5.0, intr)
    assert abs(X) < 1e-9 and abs(Y) < 1e-9 and Z == 5.0


def test_backproject_known_value():
    intr = CameraIntrinsics(fx=500, fy=500, cx=320, cy=240)
    # point (1,0,5): u = 500*1/5 + 320 = 420, v = 240
    X, Y, Z = backproject(420.0, 240.0, 5.0, intr)
    assert abs(X - 1.0) < 1e-9 and abs(Y) < 1e-9 and abs(Z - 5.0) < 1e-9


def test_project_backproject_round_trip():
    intr = CameraIntrinsics.from_fov(640, 480, 70.0)
    for (X, Y, Z) in [(0.0, 0.0, 2.0), (0.3, -0.1, 1.5), (-0.5, 0.4, 3.2)]:
        u, v, d = project(X, Y, Z, intr)
        X2, Y2, Z2 = backproject(u, v, d, intr)
        assert abs(X2 - X) < 1e-6 and abs(Y2 - Y) < 1e-6 and abs(Z2 - Z) < 1e-6


def test_project_requires_positive_depth():
    intr = CameraIntrinsics(500, 500, 320, 240)
    with pytest.raises(ValueError):
        project(1.0, 0.0, 0.0, intr)


def test_gt_localization_error_is_negligible():
    """Place objects at known 3D, project to (u,v,depth), back-project, and
    confirm recovered position matches ground truth (the Phase 4 sim check)."""
    intr = CameraIntrinsics.from_fov(640, 480, 70.0)
    gt = [(0.2, 0.1, 1.0), (-0.4, 0.2, 2.5), (0.0, -0.3, 0.8)]
    max_err = 0.0
    for (X, Y, Z) in gt:
        u, v, d = project(X, Y, Z, intr)
        rx, ry, rz = backproject(u, v, d, intr)
        max_err = max(max_err, math.dist((X, Y, Z), (rx, ry, rz)))
    assert max_err < 1e-6
