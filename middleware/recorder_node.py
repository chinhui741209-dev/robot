#!/usr/bin/env python3
"""
MCAP Recorder Node
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Pose, Twist
from std_msgs.msg import String
import time


class Recorder(Node):
    def __init__(self):
        super().__init__("recorder")

        self.declare_parameter("bag_path", "/tmp/ros2bag")
        self.bag_path = self.get_parameter("bag_path").value

        self.imu_sub = self.create_subscription(
            Imu, "/buddy/imu", self.imu_callback, 10
        )
        self.pose_sub = self.create_subscription(
            Pose, "/state/pose", self.pose_callback, 10
        )
        self.action_sub = self.create_subscription(
            Twist, "/policy/action", self.action_callback, 10
        )
        self.status_pub = self.create_publisher(String, "/recorder/status", 10)

        self.imu_count = 0
        self.pose_count = 0
        self.action_count = 0

        self.get_logger().info(f"Recorder started (path={self.bag_path})")

    def imu_callback(self, msg):
        self.imu_count += 1

    def pose_callback(self, msg):
        self.pose_count += 1

    def action_callback(self, msg):
        self.action_count += 1

    def publish_status(self):
        status = String()
        status.data = (
            f"imu:{self.imu_count} pose:{self.pose_count} action:{self.action_count}"
        )
        self.status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = Recorder()

    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)

    timer = node.create_timer(1.0, node.publish_status)

    try:
        while rclpy.ok():
            executor.spin_once(timeout_sec=0.001)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
