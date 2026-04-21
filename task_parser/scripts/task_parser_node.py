#!/usr/bin/env python3
"""
Task Parser Node - Rule-based command parser
 Converts natural language commands to structured task definitions
"""

import signal
import sys
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TaskParserNode(Node):
    def __init__(self):
        super().__init__("task_parser")

        self.command_sub = self.create_subscription(
            String, "/ui/user_command", self.command_callback, 10
        )

        self.parsed_pub = self.create_publisher(String, "/task/parsed_command", 10)

        self.get_logger().info("Task Parser Node started")

        self.commands = {
            "把蘋果放到盒子中": {
                "intent": "pick_and_place",
                "source": "apple",
                "target": "box",
            },
            "把橘子放到盒子中": {
                "intent": "pick_and_place",
                "source": "orange",
                "target": "box",
            },
            "把蘋果放到箱子中": {
                "intent": "pick_and_place",
                "source": "apple",
                "target": "box",
            },
            "pick apple to box": {
                "intent": "pick_and_place",
                "source": "apple",
                "target": "box",
            },
            "pick orange to box": {
                "intent": "pick_and_place",
                "source": "orange",
                "target": "box",
            },
        }

    def command_callback(self, msg):
        command = msg.data.strip()
        self.get_logger().info(f"Received command: {command}")

        parsed = self.parse_command(command)

        if parsed:
            parsed_msg = String()
            parsed_msg.data = json.dumps(parsed)
            self.parsed_pub.publish(parsed_msg)
            self.get_logger().info(f"Published: {parsed}")
        else:
            self.get_logger().warn(f"Unknown command: {command}")

    def parse_command(self, command):
        if command in self.commands:
            return self.commands[command]

        for cmd_template, parsed in self.commands.items():
            if cmd_template in command or command in cmd_template:
                return parsed

        return None


def main(args=None):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    rclpy.init(args=args)
    node = TaskParserNode()

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
