#!/usr/bin/env python3
"""
Object persistence tracker for the World Model (pure, ROS-free, unit-testable).

Turns per-frame detections into persistent per-class tracks so downstream
consumers (the planner) can ask "is the pen present?" without flickering on a
single dropped frame. One track per class (highest-confidence instance).

A class counts as PRESENT when it has been seen on >= confirm_frames recent
frames AND was last seen within present_timeout seconds.
"""


class ObjectTracker:
    def __init__(self, present_timeout=1.0, confirm_frames=2):
        self.present_timeout = float(present_timeout)
        self.confirm_frames = int(confirm_frames)
        self.tracks = {}  # class -> {conf, cx, cy, last_seen, hits}

    def update(self, detections, now):
        """detections: list of {class, confidence, cx, cy}. now: seconds."""
        seen = {}
        for d in detections:
            cls = d.get("class")
            if cls is None:
                continue
            # Keep the highest-confidence detection per class this frame.
            if cls not in seen or d.get("confidence", 0) > seen[cls].get("confidence", 0):
                seen[cls] = d
        for cls, d in seen.items():
            t = self.tracks.get(cls, {"hits": 0})
            t["conf"] = float(d.get("confidence", 0.0))
            t["cx"] = float(d.get("cx", 0.0))
            t["cy"] = float(d.get("cy", 0.0))
            t["last_seen"] = now
            t["hits"] = min(t.get("hits", 0) + 1, self.confirm_frames + 5)
            self.tracks[cls] = t
        # Decay hits for classes not seen this frame (so they drop out cleanly).
        for cls, t in self.tracks.items():
            if cls not in seen and (now - t.get("last_seen", 0)) > self.present_timeout:
                t["hits"] = 0

    def is_present(self, cls, now):
        t = self.tracks.get(cls)
        if not t:
            return False
        return (t.get("hits", 0) >= self.confirm_frames
                and (now - t.get("last_seen", 0)) <= self.present_timeout)

    def present_classes(self, now):
        return sorted(c for c in self.tracks if self.is_present(c, now))

    def snapshot(self, now):
        objs = []
        for cls, t in self.tracks.items():
            objs.append({
                "class": cls,
                "confidence": round(t.get("conf", 0.0), 3),
                "pos": {"x": round(t.get("cx", 0.0), 1), "y": round(t.get("cy", 0.0), 1)},
                "age_s": round(now - t.get("last_seen", now), 2),
                "present": self.is_present(cls, now),
            })
        return objs
