#!/usr/bin/env python3
"""Test script for demo nodes"""

import rclpy
from std_msgs.msg import String
from rclpy.node import Node


class TestPublisher(Node):
    def __init__(self):
        super().__init__("test_pub")
        self.cmd_pub = self.create_publisher(String, "/ui/user_command", 10)
        self.parsed_sub = self.create_subscription(
            String, "/task/parsed_command", self.parsed_callback, 10
        )
        self.step_sub = self.create_subscription(
            Int32, "/planner/current_step", self.step_callback, 10
        )

    def parsed_callback(self, msg):
        print(f"  [received] parsed_command: {msg.data}")

    def step_callback(self, msg):
        print(f"  [received] current_step: {msg.data}")


def test_flow():
    rclpy.init()
    node = TestPublisher()

    print("Publishing test command: '把蘋果放到盒子中'")
    msg = String()
    msg.data = "把蘋果放到盒子中"
    node.cmd_pub.publish(msg)

    print("Waiting for response...")
    import time

    for i in range(10):
        rclpy.spin_once(node, timeout_sec=0.5)
        time.sleep(0.5)

    rclpy.shutdown()


if __name__ == "__main__":
    from std_msgs.msg import Int32

    test_flow()
