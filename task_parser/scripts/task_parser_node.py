#!/usr/bin/env python3
"""
Task Parser Node — natural-language command -> structured task plan.

Pluggable LanguageBackend (task_parser/language_backend.py):
  backend=rule (default, offline, deterministic) | llm (Claude, opt-in).
LLM misses fall back to the rule backend. Publishes the parsed_command the
Phase 2 event-driven planner consumes: {intent, source, target, steps}.
Replaces the old hardcoded 3-command dictionary.
"""

import os
import sys
import json
import signal

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from task_parser.language_backend import RuleBackend, LLMBackend


class TaskParserNode(Node):
    def __init__(self):
        super().__init__("task_parser")
        self.declare_parameter("backend", "rule")   # rule | llm
        self.declare_parameter("api_model", "claude-opus-4-8")

        self.rule = RuleBackend()
        self.llm = None
        if self.get_parameter("backend").value == "llm":
            try:
                self.llm = LLMBackend(model=self.get_parameter("api_model").value,
                                      logger=self.get_logger())
                self.get_logger().info("Task parser backend: Claude LLM (rule fallback)")
            except Exception as e:
                self.get_logger().error(f"LLM backend init failed ({e}); using rule")
        if self.llm is None:
            self.get_logger().info("Task parser backend: rule (offline)")

        self.create_subscription(String, "/ui/user_command", self.command_callback, 10)
        self.parsed_pub = self.create_publisher(String, "/task/parsed_command", 10)
        self.get_logger().info("Task Parser Node started")

    def command_callback(self, msg):
        cmd = msg.data.strip()
        self.get_logger().info(f"Received command: {cmd}")
        parsed = self.llm.parse(cmd) if self.llm else None
        if parsed is None:
            parsed = self.rule.parse(cmd)   # offline fallback / default
        if parsed:
            self.parsed_pub.publish(String(data=json.dumps(parsed)))
            self.get_logger().info(f"Published: {parsed}")
        else:
            self.get_logger().warn(f"Could not parse command: {cmd}")


def main(args=None):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    rclpy.init(args=args)
    node = TaskParserNode()
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor(num_threads=1)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, Exception) as e:
        node.get_logger().error(f"Spin error: {e}")
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
