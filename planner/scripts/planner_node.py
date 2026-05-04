#!/usr/bin/env python3
"""
Planner Node - Task planning and step control
 Receives parsed commands and generates step-by-step task plan
"""

import signal
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32, Float32MultiArray


class PlannerNode(Node):
    def __init__(self):
        super().__init__("planner")

        self.command_sub = self.create_subscription(
            String, "/task/parsed_command", self.command_callback, 10
        )

        self.plan_pub = self.create_publisher(
            Float32MultiArray, "/planner/task_plan", 10
        )

        self.step_pub = self.create_publisher(Int32, "/planner/current_step", 10)
        self.state_pub = self.create_publisher(String, "/planner/state", 10)

        self.get_logger().info("Planner Node started")

        self.default_steps = ["Idle"]
        self.current_steps = self.default_steps
        self.current_command = None
        self.current_step_idx = -1
        self.state = "IDLE" # IDLE, RUNNING, COMPLETED
        self.step_duration = 2.0

        self.timer = self.create_timer(1.0, self.state_machine_callback)

    def command_callback(self, msg):
        try:
            command = json.loads(msg.data)
        except:
            self.get_logger().error(f"Failed to parse command: {msg.data}")
            return

        self.current_command = command
        self.current_steps = command.get("steps", ["Default Action"])
        self.current_step_idx = 0
        self.state = "RUNNING"

        self.get_logger().info(f"Starting task: {command['intent']} with {len(self.current_steps)} steps")

        plan_msg = Float32MultiArray()
        plan_msg.data = [float(i) for i in range(len(self.current_steps))]
        self.plan_pub.publish(plan_msg)
        
    def state_machine_callback(self):
        # Publish current state
        state_msg = String()
        state_msg.data = self.state
        self.state_pub.publish(state_msg)

        if self.state != "RUNNING":
            return

        if self.current_step_idx < len(self.current_steps):
            step_name = self.current_steps[self.current_step_idx]
            self.get_logger().info(f"Executing Step {self.current_step_idx}: {step_name}")
            
            step_msg = Int32()
            step_msg.data = self.current_step_idx
            self.step_pub.publish(step_msg)
            
            # Simulate step execution - in real system, wait for feedback
            self.current_step_idx += 1
        else:
            self.get_logger().info("Task Completed")
            self.state = "COMPLETED"
            self.current_step_idx = -1

    def execute_callback(self, msg):
        if msg.data == "reset":
            self.state = "IDLE"
            self.current_step_idx = -1
            self.current_command = None
            self.current_steps = self.default_steps


def main(args=None):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    rclpy.init(args=args)
    node = PlannerNode()

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
