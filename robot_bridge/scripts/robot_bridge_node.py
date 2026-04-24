#!/usr/bin/env python3
"""
Robot Bridge Node - Simulates robot control
 Receives step commands and simulates motor states
"""

import signal
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32, Float32MultiArray


class RobotBridgeNode(Node):
    def __init__(self):
        super().__init__("robot_bridge")

        self.step_sub = self.create_subscription(
            Int32, "/planner/current_step", self.step_callback, 10
        )

        self.state_pub = self.create_publisher(String, "/robot/state", 10)

        self.motor_pub = self.create_publisher(
            Float32MultiArray, "/robot/motor_status", 10
        )

        self.get_logger().info("Robot Bridge Node started")

        self.current_step = -1
        self.state = "idle"

        self.step_motor_mapping = {
            0: ["shoulder"],  # locate source
            1: ["elbow"],  # locate target
            2: ["shoulder", "elbow"],  # pre-grasp
            3: ["shoulder", "elbow", "wrist"],  # grasp pose
            4: ["gripper"],  # close gripper
            5: ["shoulder"],  # lift
            6: ["shoulder", "elbow"],  # move to target
            7: ["wrist"],  # position
            8: ["gripper"],  # open gripper
            9: ["shoulder", "elbow"],  # retreat
            10: [],  # done
        }

        self.motor_positions = {
            "shoulder": 0.0,
            "elbow": 0.0,
            "wrist": 0.0,
            "gripper": 0.0,
        }

    def step_callback(self, msg):
        step = msg.data
        self.current_step = step
        self.get_logger().info(f"Received step: {step}")

        motors = self.step_motor_mapping.get(step, [])

        state_msg = String()
        if step >= 10:
            state_msg.data = "complete"
            self.state = "complete"
        else:
            state_msg.data = "moving"
            self.state = "moving"
        self.state_pub.publish(state_msg)

        # Simulate motor movement based on active joints in this step
        for m in self.motor_positions.keys():
            if m in motors:
                # Move towards 45.0 degrees
                self.motor_positions[m] = min(45.0, self.motor_positions[m] + 15.0)
            elif self.current_step == 10:
                # Reset to 0 when complete
                self.motor_positions[m] = 0.0
                
        positions = [
            self.motor_positions.get(m, 0.0)
            for m in ["shoulder", "elbow", "wrist", "gripper"]
        ]
        motor_msg = Float32MultiArray()
        motor_msg.data = positions
        self.motor_pub.publish(motor_msg)

        self.get_logger().info(f"State: {state_msg.data}, Motors: {motors}")


def main(args=None):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    rclpy.init(args=args)
    node = RobotBridgeNode()

    from rclpy.executors import MultiThreadedExecutor

    executor = MultiThreadedExecutor(num_threads=1)
    executor.add_node(node)

    try:
        executor.spin()
    except Exception as e:
        node.get_logger().error(f"Spin error: {e}")
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
