#!/usr/bin/env python3
"""
Action-Chain Arbiter (Phase 2).

The system has two command sources that both want motor authority:
  - Locomotion: /policy/joint_commands  (32-DoF, BC policy)
  - Manipulation: /control/target       (4-DoF arm: shoulder/elbow/wrist/gripper, skill layer)

The arbiter resolves who is authoritative based on /arbiter/mode (set by the
planner from the current step) and republishes the winning command to
/control/arbitrated_command with a source tag on /arbiter/status. Wiring the
actuator layer (ros2_bridge / robot_bridge) to consume the arbitrated topic is
a follow-up; for now this DEFINES and publishes the arbitration decision.

Modes: LOCOMOTION -> policy wins; MANIPULATION -> skill wins; IDLE -> hold (no output).
"""

import os
import sys
import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from arbiter.arbiter_logic import arbitrate


class ArbiterNode(Node):
    def __init__(self):
        super().__init__("arbiter")
        self.mode = "IDLE"
        self.policy_cmd = []
        self.skill_cmd = []

        self.create_subscription(Float32MultiArray, "/policy/joint_commands", self._policy_cb, 10)
        self.create_subscription(Float32MultiArray, "/control/target", self._skill_cb, 10)
        self.create_subscription(String, "/arbiter/mode", self._mode_cb, 10)

        self.cmd_pub = self.create_publisher(Float32MultiArray, "/control/arbitrated_command", 10)
        self.status_pub = self.create_publisher(String, "/arbiter/status", 10)
        self.create_timer(0.05, self._tick)  # 20 Hz
        self.get_logger().info("Action-chain Arbiter started")

    def _policy_cb(self, msg):
        self.policy_cmd = list(msg.data)

    def _skill_cb(self, msg):
        self.skill_cmd = list(msg.data)

    def _mode_cb(self, msg):
        self.mode = msg.data

    def _tick(self):
        source, cmd = arbitrate(self.mode, self.policy_cmd, self.skill_cmd)
        if cmd:
            self.cmd_pub.publish(Float32MultiArray(data=[float(x) for x in cmd]))
        self.status_pub.publish(String(data=json.dumps(
            {"mode": self.mode, "authority": source, "n": len(cmd)})))


def main(args=None):
    rclpy.init(args=args)
    node = ArbiterNode()
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
