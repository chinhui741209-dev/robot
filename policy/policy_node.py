#!/usr/bin/env python3
"""
RL Policy Node - 50 Hz inference (simulated)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray
import math
import time
import numpy as np


class PolicyNode(Node):
    def __init__(self):
        super().__init__("policy")

        self.declare_parameter("rate", 50)
        self.declare_parameter("sim", True)
        self.rate = self.get_parameter("rate").value
        self.sim = self.get_parameter("sim").value

        self.action_pub = self.create_publisher(Twist, "/policy/action", 10)
        self.action_chunk_pub = self.create_publisher(
            Float32MultiArray, "/policy/action_chunk", 10
        )
        self.latency_pub = self.create_publisher(
            Float32MultiArray, "/policy/latency", 10
        )

        self.imu_sub = self.create_subscription(
            Imu, "/buddy/imu", self.inference_callback, 10
        )

        self.timer = self.create_timer(1.0 / self.rate, self.publish_action)

        self.inference_count = 0
        self.latencies = []

        self.get_logger().info(f"Policy started at {self.rate} Hz (sim={self.sim})")

    def inference_callback(self, msg):
        self.inference_count += 1

    def publish_action(self):
        start = time.time()

        action = Twist()
        action.linear.x = math.sin(time.time()) * 0.1
        action.linear.y = math.cos(time.time()) * 0.1
        action.linear.z = math.sin(time.time() * 0.5) * 0.05
        action.angular.x = math.sin(time.time() * 0.1) * 0.01
        action.angular.y = math.cos(time.time() * 0.1) * 0.01
        action.angular.z = math.sin(time.time() * 0.05) * 0.005

        chunk = Float32MultiArray()
        chunk.data = [
            action.linear.x,
            action.linear.y,
            action.linear.z,
            action.angular.x,
            action.angular.y,
            action.angular.z,
            0.0,
        ]

        self.action_pub.publish(action)
        self.action_chunk_pub.publish(chunk)

        latency = (time.time() - start) * 1000

        if self.inference_count % 100 == 0:
            avg_latency = (
                sum(self.latencies) / len(self.latencies) if self.latencies else 0
            )
            p99_latency = (
                sorted(self.latencies)[int(len(self.latencies) * 0.99)]
                if self.latencies
                else 0
            )
            self.get_logger().info(
                f"Latency: avg={avg_latency:.2f}ms, p99={p99_latency:.2f}ms"
            )

        self.latencies.append(latency)
        if len(self.latencies) > 1000:
            self.latencies.pop(0)


def main(args=None):
    rclpy.init(args=args)
    node = PolicyNode()

    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)

    try:
        while rclpy.ok():
            executor.spin_once(timeout_sec=0.001)
    except KeyboardInterrupt:
        pass
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
