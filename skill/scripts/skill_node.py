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
        
        # Safety Limits — 4-DoF simplified arm contract [shoulder, elbow, wrist, gripper].
        # Arm limits are the real Unitree G1 (EDU 29-DOF) joint ranges in DEGREES,
        # converted from g1_29dof.urdf (shoulder_pitch −3.0892..2.6704, elbow
        # −1.0472..2.0944, wrist_pitch ±1.6144 rad). gripper is a 0..1 close fraction.
        # NOTE: G1's full arm is 7-DoF; this demo guard covers the 3 driven joints
        # + gripper. Real-robot commands convert deg -> rad at the unitree_hg boundary.
        self.max_limits = np.array([153.0, 120.0,  92.5, 1.0])
        self.min_limits = np.array([-177.0, -60.0, -92.5, 0.0])
        
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
