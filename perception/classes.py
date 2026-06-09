#!/usr/bin/env python3
"""
Single source of truth for detection class names + portable path resolution.

Used by perception_node, the verify GUI, the dataset generator and the trainer
so the class list never drifts (the old code had perception hardcoded to
["pen","box"] while task_parser already referenced apple/orange).

Override the class list with the POC_CLASSES env var (comma-separated) or a
`config/classes.txt` file (one class per line); otherwise DEFAULT_CLASSES.
"""

import os

DEFAULT_CLASSES = ["pen", "box"]


def poc_root():
    return os.environ.get("POC_ROOT", os.getcwd())


def resolve_path(path):
    """Make a repo-relative path absolute against POC_ROOT (no-op if absolute)."""
    if os.path.isabs(path):
        return path
    return os.path.join(poc_root(), path)


def get_class_names():
    env = os.environ.get("POC_CLASSES")
    if env:
        names = [c.strip() for c in env.split(",") if c.strip()]
        if names:
            return names
    cfg = resolve_path(os.path.join("config", "classes.txt"))
    try:
        with open(cfg) as f:
            names = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        if names:
            return names
    except OSError:
        pass
    return list(DEFAULT_CLASSES)
