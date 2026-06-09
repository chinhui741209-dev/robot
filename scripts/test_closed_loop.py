#!/usr/bin/env python3
"""
End-to-end closed-loop verification (single process, real ROS 2).

Runs WorldModelNode + PlannerNode + a StimulusNode together and drives a
scenario that proves the planner is genuinely closed-loop:

  t=0s : send task "pen -> box"; start publishing a 'pen' detection only.
  t<4s : planner advances locate_pen -> grasp_pen, then PARKS at move_to_box
         (target 'box' not present yet).
  t=4s : 'box' detection appears -> planner advances move_to_box -> release_pen
         -> COMPLETED.

Prints planner state/step transitions. Expected final state: COMPLETED.
Run:  PYTHONPATH=. ROS_DOMAIN_ID=78 python3 scripts/test_closed_loop.py
"""

import os
import sys
import json
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from world_model.scripts.world_model_node import WorldModelNode
from planner.scripts.planner_node import PlannerNode


def _det(cls, score, cx, cy):
    d = Detection2D()
    d.bbox.center.position.x = float(cx)
    d.bbox.center.position.y = float(cy)
    d.bbox.size_x, d.bbox.size_y = 30.0, 30.0
    h = ObjectHypothesisWithPose()
    h.hypothesis.class_id = cls
    h.hypothesis.score = float(score)
    d.results.append(h)
    return d


class StimulusNode(Node):
    def __init__(self):
        super().__init__("stimulus")
        self.cmd_pub = self.create_publisher(String, "/ui_bypass_command", 10)
        self.parsed_pub = self.create_publisher(String, "/task/parsed_command", 10)
        self.det_pub = self.create_publisher(Detection2DArray, "/perception/objects", 10)
        self.create_subscription(String, "/planner/status", self._status_cb, 10)
        self.create_subscription(String, "/planner/state", self._state_cb, 10)

        self.t0 = time.monotonic()
        self.sent_cmd = False
        self.last_print = None
        self.final_state = None
        self.create_timer(0.1, self._tick)        # 10 Hz detections
        self.get_logger().info("Stimulus running scenario...")

    def _tick(self):
        t = time.monotonic() - self.t0
        if not self.sent_cmd:
            self.parsed_pub.publish(String(data=json.dumps({
                "intent": "pick_and_place", "source": "pen", "target": "box",
                "steps": ["locate_pen", "grasp_pen", "move_to_box", "release_pen"],
            })))
            self.sent_cmd = True

        dets = [_det("pen", 0.92, 320, 240)]
        if t >= 4.0:                              # box appears after 4 s
            dets.append(_det("box", 0.88, 500, 300))
        arr = Detection2DArray()
        arr.detections = dets
        self.det_pub.publish(arr)

    def _state_cb(self, msg):
        self.final_state = msg.data

    def _status_cb(self, msg):
        ev = json.loads(msg.data)
        key = (ev["idx"], ev["state"])
        if key != self.last_print:
            t = time.monotonic() - self.t0
            present = "box" if (t >= 4.0) else "pen-only"
            print(f"[t={t:4.1f}s | scene={present:8s}] state={ev['state']:9s} "
                  f"step={ev['idx']} '{ev['step']}' need='{ev['precondition']}' :: {ev['reason']}",
                  flush=True)
            self.last_print = key


def main():
    rclpy.init()
    wm = WorldModelNode()
    planner = PlannerNode()
    stim = StimulusNode()
    ex = MultiThreadedExecutor()
    for n in (wm, planner, stim):
        ex.add_node(n)

    start = time.monotonic()
    try:
        while rclpy.ok() and (time.monotonic() - start) < 12.0:
            ex.spin_once(timeout_sec=0.05)
            if stim.final_state in ("COMPLETED", "FAILED") and (time.monotonic() - start) > 5.0:
                break  # reached a terminal state after the box-appears event
    finally:
        print(f"\nFINAL planner state = {stim.final_state}", flush=True)
        for n in (wm, planner, stim):
            try:
                n.destroy_node()
            except Exception:
                pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
