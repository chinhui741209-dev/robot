#!/usr/bin/env python3
"""
Skill Node - Safety & Trajectory Management (D7 Layer)
Acts as a buffer between AI Policy and Real-time Control.
Implements safety limits and smoothing.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import numpy as np

class SkillNode(Node):
    def __init__(self):
        super().__init__("skill_node")
        
        # ICD Alignment: Subscribe to VLA output, Publish to Control Target
        self.cmd_sub = self.create_subscription(
            Float32MultiArray, "/skill/command", self.skill_callback, 10
        )
        self.target_pub = self.create_publisher(
            Float32MultiArray, "/control/target", 10
        )
        
        # Safety Limits (e.g., max 90 degrees for joints)
        self.max_limits = np.array([90.0, 90.0, 90.0, 1.0])
        self.min_limits = np.array([-90.0, -90.0, -90.0, 0.0])
        
        # Internal state for smoothing
        self.current_pos = np.zeros(4)
        self.smoothing_factor = 0.3  # Simple EMA smoothing
        
        self.get_logger().info("🛡️ Skill Layer (D7) Initialized - Safety Guard Active")

    def skill_callback(self, msg):
        raw_actions = np.array(msg.data)
        
        # 1. Safety Guard: Clip to limits
        clipped_actions = np.clip(raw_actions, self.min_limits, self.max_limits)
        
        # 2. Trajectory Smoothing: Exponential Moving Average
        self.current_pos = (self.smoothing_factor * clipped_actions) + \
                          ((1 - self.smoothing_factor) * self.current_pos)
        
        # 3. Publish to Control Layer
        target_msg = Float32MultiArray()
        target_msg.data = self.current_pos.tolist()
        self.target_pub.publish(target_msg)
        
        # Log occasionally
        if np.any(raw_actions != clipped_actions):
            self.get_logger().warn(f"⚠️ Safety Guard triggered! Action clipped.")

def main(args=None):
    rclpy.init(args=args)
    node = SkillNode()
    try:
        rclpy.spin(node)
    except Exception:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
