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

        self.get_logger().info("Planner Node started")

        self.task_steps = [
            "Locate source",
            "Locate target",
            "Move to pre-grasp",
            "Move to grasp",
            "Close gripper",
            "Lift object",
            "Move to target",
            "Position over target",
            "Open gripper",
            "Retreat",
            "Complete",
        ]

        self.current_command = None
        self.current_step = -1
        self.running = False
        self.step_duration = 1.0

        self.timer = self.create_timer(self.step_duration, self.step_timer_callback)

    def command_callback(self, msg):
        try:
            command = json.loads(msg.data)
        except:
            self.get_logger().error(f"Failed to parse command: {msg.data}")
            return

        self.current_command = command
        self.current_step = 0
        self.running = True

        self.get_logger().info(f"Starting task: {command}")

        plan_msg = Float32MultiArray()
        plan_msg.data = [float(i) for i in range(len(self.task_steps))]
        self.plan_pub.publish(plan_msg)

    def step_timer_callback(self):
        if not self.running:
            return

        self.current_step += 1

        if self.current_step >= len(self.task_steps):
            self.current_step = len(self.task_steps) - 1
            self.running = False
            return

        step_msg = Int32()
        step_msg.data = self.current_step
        self.step_pub.publish(step_msg)

        self.get_logger().info(
            f"Step {self.current_step}: {self.task_steps[self.current_step]}"
        )

    def next_step(self):
        if not self.running:
            return

        self.current_step += 1

        if self.current_step >= len(self.task_steps):
            self.current_step = len(self.task_steps) - 1
            self.running = False

        step_msg = Int32()
        step_msg.data = self.current_step
        self.step_pub.publish(step_msg)

        self.get_logger().info(
            f"Step {self.current_step}: {self.task_steps[self.current_step]}"
        )

    def run_task(self):
        while self.running and rclpy.ok():
            self.next_step()
            if self.running:
                import time

                time.sleep(self.step_duration)

    def execute_callback(self, msg):
        if msg.data == "start":
            if self.current_command:
                self.run_task()
        elif msg.data == "stop":
            self.running = False
            self.current_step = -1
        elif msg.data == "reset":
            self.running = False
            self.current_step = -1
            self.current_command = None


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
