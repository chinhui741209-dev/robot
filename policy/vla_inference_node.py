#!/usr/bin/env python3
"""
VLA Inference Node — language + vision -> structured task plan.

backend=api  : Claude vision brain (policy/vla_brain.py) turns the user command +
               camera image into a task plan published on /task/parsed_command,
               which the Phase 2 event-driven planner consumes ("VLA = brain,
               BC policy = small-brain").
backend=mock : scripted step ticks for an offline, no-network demo.

The former GPU-only OpenVLA-7B path was removed — it never ran on this CPU-only
Orin and is superseded by the Claude API brain.
"""

import os
import sys
import json
import time

import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32, Float32MultiArray
from sensor_msgs.msg import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VlaInferenceNode(Node):
    def __init__(self):
        super().__init__("vla_inference_node")
        self.declare_parameter("backend", "mock")          # mock | api
        self.declare_parameter("api_model", "claude-opus-4-8")
        self.backend = self.get_parameter("backend").value

        self.create_subscription(String, "/ui/user_command", self.cmd_callback, 10)
        self.create_subscription(Image, "/camera/image_raw", self.img_callback, 10)
        self.action_pub = self.create_publisher(Float32MultiArray, "/skill/command", 10)
        self.step_pub = self.create_publisher(Int32, "/planner/current_step", 10)
        self.plan_pub = self.create_publisher(String, "/task/parsed_command", 10)

        self.latest_image = None
        self.is_processing = False
        self.vla_brain = None

        if self.backend == "api":
            try:
                from policy.vla_brain import ClaudeVlaBrain
                self.vla_brain = ClaudeVlaBrain(
                    model=self.get_parameter("api_model").value, logger=self.get_logger())
                self.get_logger().info(
                    f"🧠 VLA brain: Claude API ({self.get_parameter('api_model').value})")
            except Exception as e:
                self.get_logger().error(f"Claude VLA init failed ({e}); falling back to MOCK")
                self.backend = "mock"
        if self.backend != "api":
            self.get_logger().warn("⚠️ VLA running in MOCK mode")

    def img_callback(self, msg):
        self.latest_image = msg

    def cmd_callback(self, msg):
        if self.is_processing:
            self.get_logger().warn("VLA is busy.")
            return
        self.is_processing = True
        if self.backend == "api" and self.vla_brain is not None:
            self.run_api_vla(msg.data)
        else:
            self.run_mock_vla(msg.data)

    def _decode_image(self):
        if self.latest_image is None:
            return None
        try:
            m = self.latest_image
            bpp = (m.step // m.width) if m.width else 3
            frame = np.frombuffer(m.data, np.uint8).reshape(m.height, m.width, bpp)
            if bpp == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            return np.ascontiguousarray(frame)
        except Exception:
            return None

    def run_api_vla(self, command):
        self.get_logger().info(f"🧠 [Claude VLA] Planning: {command}")
        plan = self.vla_brain.plan(command, frame_bgr=self._decode_image(), scene_objects=None)
        if plan is None:
            self.get_logger().warn("VLA produced no plan.")
        else:
            self.plan_pub.publish(String(data=json.dumps(plan)))
            self.get_logger().info(f"[Claude VLA] plan -> {plan}")
        self.is_processing = False

    def run_mock_vla(self, command):
        self.get_logger().info(f"🤖 [Mock] Processing: {command}")
        for step_val in [0, 2, 5, 8, 10]:
            self.step_pub.publish(Int32(data=step_val))
            chunk = Float32MultiArray()
            chunk.data = [float(step_val * 5), float(step_val * 2), 0.0,
                          1.0 if step_val > 5 else 0.0]
            self.action_pub.publish(chunk)
            time.sleep(1.0)
        self.get_logger().info("Mock execution finished.")
        self.is_processing = False


def main(args=None):
    rclpy.init(args=args)
    node = VlaInferenceNode()
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
