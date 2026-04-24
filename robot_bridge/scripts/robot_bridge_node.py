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

        self.target_sub = self.create_subscription(
            Float32MultiArray, "/control/target", self.target_callback, 10
        )

        self.step_sub = self.create_subscription(Int32, "/planner/current_step", self.step_callback, 10)
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
        self.current_step = msg.data
        self.get_logger().info(f"Monitor: Task at Step {self.current_step}")

    def target_callback(self, msg):
        # D3 Layer Logic: Control following the target from D7 Skill Layer
        positions = list(msg.data)
        if len(positions) >= 4:
            self.motor_positions["shoulder"] = positions[0]
            self.motor_positions["elbow"] = positions[1]
            self.motor_positions["wrist"] = positions[2]
            self.motor_positions["gripper"] = positions[3]
            
        # 1. Update Internal State and Publish for GUI
        motor_msg = Float32MultiArray()
        motor_msg.data = [float(x) for x in positions[:4]]
        self.motor_pub.publish(motor_msg)

        # 2. Update Robot State
        state_msg = String()
        state_msg.data = "executing_skill" if self.current_step < 10 else "complete"
        self.state_pub.publish(state_msg)

        # 3. Unitree SDK Simulation (RT Control Layer Logic)
        gear_ratio = 6.33
        kp_output_desired = 60.0
        kd_output_desired = 1.5
        
        kp_rotor = kp_output_desired / (gear_ratio ** 2)
        kd_rotor = kd_output_desired / (gear_ratio ** 2)
        
        # Log RT stats (throttled)
        if hasattr(self, "log_counter"): self.log_counter += 1
        else: self.log_counter = 0
        
        if self.log_counter % 20 == 0:
            self.get_logger().info(
                f"[D3 Control] Target: {positions[0]:.1f}, {positions[1]:.1f} | "
                f"SDK Kp_r: {kp_rotor:.3f}"
            )


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
