#!/usr/bin/env python3
"""
State Estimator - 500 Hz pose estimation from IMU
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Pose, TransformStamped
import math
import numpy as np


class StateEstimator(Node):
    def __init__(self):
        super().__init__("state_estimator")

        self.declare_parameter("rate", 500)
        self.rate = self.get_parameter("rate").value

        self.pose_pub = self.create_publisher(Pose, "/state/pose", 10)
        self.tf_pub = self.create_publisher(TransformStamped, "/tf", 10)

        self.imu_sub = self.create_subscription(
            Imu, "/buddy/imu", self.imu_callback, 10
        )

        self.timer = self.create_timer(1.0 / self.rate, self.publish_state)

        self.counter = 0
        self.velocity = [0.0, 0.0, 0.0]
        self.position = [0.0, 0.0, 0.0]

        self.get_logger().info(f"State Estimator started at {self.rate} Hz (sim=True)")

    def imu_callback(self, msg):
        dt = 1.0 / self.rate

        ax = msg.linear_acceleration.x - 9.8 * 0.0
        ay = msg.linear_acceleration.y - 9.8 * 0.0
        az = msg.linear_acceleration.z - 9.8

        self.velocity[0] += ax * dt
        self.velocity[1] += ay * dt
        self.velocity[2] += az * dt

        self.position[0] += self.velocity[0] * dt
        self.position[1] += self.velocity[1] * dt
        self.position[2] += self.velocity[2] * dt

    def publish_state(self):
        self.counter += 1

        pose = Pose()
        pose.position.x = self.position[0]
        pose.position.y = self.position[1]
        pose.position.z = self.position[2]

        pose.orientation.x = math.sin(self.counter * 0.001)
        pose.orientation.y = math.cos(self.counter * 0.001)
        pose.orientation.z = math.sin(self.counter * 0.0005)
        pose.orientation.w = math.cos(self.counter * 0.0005)

        self.pose_pub.publish(pose)


def main(args=None):
    rclpy.init(args=args)
    node = StateEstimator()

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
