#!/usr/bin/env python3
"""
W1 Launch - All components in one process
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Pose, Twist
from std_msgs.msg import String, Float32MultiArray
import math
import time
import signal
import sys


class W1Node(Node):
    def __init__(self):
        super().__init__("w1_launch")

        self.imu_sub = self.create_subscription(Imu, "/buddy/imu", self.imu_cb, 10)

        self.imu_pub = self.create_publisher(Imu, "/buddy/imu", 10)
        self.motor_pub = self.create_publisher(Twist, "/buddy/motor_state", 10)
        self.health_pub = self.create_publisher(String, "/buddy/hal/health", 10)

        self.pose_pub = self.create_publisher(Pose, "/state/pose", 10)

        self.action_pub = self.create_publisher(Twist, "/policy/action", 10)

        self.recorder_pub = self.create_publisher(String, "/recorder/status", 10)

        self.hz_imu = self.create_timer(1.0 / 1000, self.publish_imu)
        self.hz_pose = self.create_timer(1.0 / 500, self.publish_pose)
        self.hz_policy = self.create_timer(1.0 / 50, self.publish_policy)
        self.hz_status = self.create_timer(1.0, self.publish_status)

        self.counter = 0
        self.imu_count = 0
        self.pose_count = 0
        self.action_count = 0

        self.get_logger().info("W1 Launch started")

    def imu_cb(self, msg):
        self.imu_count += 1

    def publish_imu(self):
        self.counter += 1

        imu = Imu()
        t = self.get_clock().now()
        imu.header.stamp = t.to_msg()
        imu.header.frame_id = "imu_link"

        imu.orientation.x = math.sin(self.counter * 0.001)
        imu.orientation.y = math.cos(self.counter * 0.001)
        imu.orientation.z = math.sin(self.counter * 0.0005)
        imu.orientation.w = math.cos(self.counter * 0.0005)

        imu.angular_velocity.x = math.sin(self.counter * 0.01) * 0.1
        imu.angular_velocity.y = math.cos(self.counter * 0.01) * 0.1
        imu.angular_velocity.z = math.sin(self.counter * 0.005) * 0.05

        imu.linear_acceleration.x = 0.0
        imu.linear_acceleration.y = 0.0
        imu.linear_acceleration.z = 9.8

        self.imu_pub.publish(imu)

        motor = Twist()
        self.motor_pub.publish(motor)

        health = String()
        health.data = "OK"
        self.health_pub.publish(health)

    def publish_pose(self):
        self.pose_count += 1

        pose = Pose()
        pose.position.x = math.sin(self.pose_count * 0.001) * 0.1
        pose.position.y = math.cos(self.pose_count * 0.001) * 0.1
        pose.position.z = 0.0

        pose.orientation.x = math.sin(self.counter * 0.001)
        pose.orientation.y = math.cos(self.counter * 0.001)
        pose.orientation.z = math.sin(self.counter * 0.0005)
        pose.orientation.w = math.cos(self.counter * 0.0005)

        self.pose_pub.publish(pose)

    def publish_policy(self):
        self.action_count += 1

        action = Twist()
        action.linear.x = math.sin(time.time()) * 0.1
        action.linear.y = math.cos(time.time()) * 0.1
        action.linear.z = 0.0

        self.action_pub.publish(action)

    def publish_status(self):
        status = String()
        status.data = (
            f"IMU:{self.imu_count} Pose:{self.pose_count} Action:{self.action_count}"
        )
        self.recorder_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = W1Node()

    executor = rclpy.executors.MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    print("W1 Launch running...")

    try:
        while rclpy.ok():
            executor.spin_once(timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        node.destroy_node()


if __name__ == "__main__":
    main()
