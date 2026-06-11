#!/usr/bin/env python3
"""
World Model Node (D5 Layer) - State Fusion & Persistent Scene Graph.

Phase 2: upgraded from a passive per-frame snapshot to a persistent, queryable
scene graph. Detections are fed through an ObjectTracker so a class stays
"present" across brief dropouts and the planner can gate steps on it.

Subscribes:  /perception/objects  vision_msgs/Detection2DArray
             /joint_states        std_msgs/Float32MultiArray
Publishes:   /world_model/state   std_msgs/String (JSON: objects[], present_classes[],
                                   robot_joints[], status) at 10 Hz
"""

import os
import sys
import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray
from vision_msgs.msg import Detection2DArray, Detection3DArray

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from world_model.tracker import ObjectTracker


class WorldModelNode(Node):
    def __init__(self):
        super().__init__("world_model_node")
        self.declare_parameter("present_timeout", 1.0)
        self.declare_parameter("confirm_frames", 2)
        self.tracker = ObjectTracker(
            present_timeout=self.get_parameter("present_timeout").value,
            confirm_frames=self.get_parameter("confirm_frames").value,
        )

        self.create_subscription(Detection2DArray, "/perception/objects", self.object_callback, 10)
        self.create_subscription(Detection3DArray, "/perception/objects_3d", self.object3d_callback, 10)
        self.create_subscription(Float32MultiArray, "/joint_states", self.joint_callback, 10)
        self.state_pub = self.create_publisher(String, "/world_model/state", 10)

        self.robot_joints = [0.0, 0.0, 0.0, 0.0]
        self.pos3d = {}  # class -> {x,y,z,last_seen} (camera-frame metres)
        self.last_update = 0.0
        self.create_timer(0.1, self.broadcast_state)
        self.get_logger().info("🌍 World Model (D5) - persistent scene graph + tracking")

    def object_callback(self, msg):
        now = time.time()
        dets = []
        for det in msg.detections:
            if not det.results:
                continue
            dets.append({
                "class": det.results[0].hypothesis.class_id,
                "confidence": float(det.results[0].hypothesis.score),
                "cx": float(det.bbox.center.position.x),
                "cy": float(det.bbox.center.position.y),
            })
        self.tracker.update(dets, now)
        self.last_update = now

    def object3d_callback(self, msg):
        now = time.time()
        for det in msg.detections:
            if not det.results:
                continue
            p = det.bbox.center.position
            self.pos3d[det.results[0].hypothesis.class_id] = {
                "x": round(float(p.x), 3), "y": round(float(p.y), 3),
                "z": round(float(p.z), 3), "last_seen": now,
            }

    def joint_callback(self, msg):
        self.robot_joints = [round(float(x), 2) for x in msg.data]

    def broadcast_state(self):
        now = time.time()
        objects_3d = {c: {"x": p["x"], "y": p["y"], "z": p["z"]}
                      for c, p in self.pos3d.items() if (now - p["last_seen"]) <= 2.0}
        state = {
            "last_update": round(self.last_update, 2),
            "objects": self.tracker.snapshot(now),
            "present_classes": self.tracker.present_classes(now),
            "objects_3d": objects_3d,  # class -> camera-frame {x,y,z} (m), monocular estimate
            "robot_joints": self.robot_joints,
            "status": "active" if (now - self.last_update) <= 2.0 else "stale",
        }
        msg = String()
        msg.data = json.dumps(state)
        self.state_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = WorldModelNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, Exception):
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
