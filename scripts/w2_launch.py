#!/usr/bin/env python3
"""
W2 Launch - Robust version
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, Image
from geometry_msgs.msg import Pose, Twist
from std_msgs.msg import String, Float32MultiArray, Header
import math
import time
import numpy as np
import random


class W2Node(Node):
    def __init__(self):
        super().__init__("w2_launch")

        self.buddy_imu_pub = self.create_publisher(Imu, "/buddy/imu", 10)
        self.buddy_motor_pub = self.create_publisher(Twist, "/buddy/motor_state", 10)
        self.buddy_health_pub = self.create_publisher(String, "/buddy/hal/health", 10)

        self.omni_imu_pub = self.create_publisher(Imu, "/omni/imu", 10)
        self.omni_motor_pub = self.create_publisher(Twist, "/omni/motor_state", 10)
        self.omni_health_pub = self.create_publisher(String, "/omni/hal/health", 10)

        self.pose_pub = self.create_publisher(Pose, "/state/pose", 10)
        self.action_pub = self.create_publisher(Twist, "/policy/action", 10)
        self.camera_pub = self.create_publisher(Image, "/perception/camera", 10)
        self.metrics_pub = self.create_publisher(
            Float32MultiArray, "/metrics/system", 10
        )
        self.recorder_pub = self.create_publisher(String, "/recorder/status", 10)

        self.timer = self.create_timer(0.001, self.tick)

        self.counter = 0
        self.get_logger().info("W2 Launch started")

    def tick(self):
        try:
            self.counter += 1
            t = self.get_clock().now()

            if self.counter % 1 == 0:
                imu = Imu()
                imu.header.stamp = t.to_msg()
                imu.header.frame_id = "buddy_imu"
                imu.orientation.x = math.sin(self.counter * 0.001)
                imu.orientation.y = math.cos(self.counter * 0.001)
                imu.orientation.z = math.sin(self.counter * 0.0005)
                imu.orientation.w = math.cos(self.counter * 0.0005)
                imu.angular_velocity.x = math.sin(self.counter * 0.01) * 0.1
                imu.angular_velocity.y = math.cos(self.counter * 0.01) * 0.1
                imu.angular_velocity.z = math.sin(self.counter * 0.005) * 0.05
                imu.linear_acceleration.z = 9.8
                self.buddy_imu_pub.publish(imu)
                self.buddy_motor_pub.publish(Twist())
                self.buddy_health_pub.publish(String(data="OK"))

                imu2 = Imu()
                imu2.header.stamp = t.to_msg()
                imu2.header.frame_id = "omni_imu"
                imu2.orientation.x = math.sin(self.counter * 0.0008)
                imu2.orientation.y = math.cos(self.counter * 0.0008)
                imu2.orientation.z = math.sin(self.counter * 0.0004)
                imu2.orientation.w = math.cos(self.counter * 0.0004)
                imu2.angular_velocity.x = math.sin(self.counter * 0.008) * 0.08
                imu2.angular_velocity.y = math.cos(self.counter * 0.008) * 0.08
                imu2.angular_velocity.z = math.sin(self.counter * 0.004) * 0.04
                imu2.linear_acceleration.z = 9.8
                self.omni_imu_pub.publish(imu2)
                self.omni_motor_pub.publish(Twist())
                self.omni_health_pub.publish(String(data="OK"))

            if self.counter % 2 == 0:
                pose = Pose()
                pose.position.x = math.sin(self.counter * 0.001) * 0.1
                pose.position.y = math.cos(self.counter * 0.001) * 0.1
                pose.orientation.x = math.sin(self.counter * 0.001)
                pose.orientation.y = math.cos(self.counter * 0.001)
                self.pose_pub.publish(pose)

            if self.counter % 20 == 0:
                action = Twist()
                action.linear.x = math.sin(time.time()) * 0.1
                action.linear.y = math.cos(time.time()) * 0.1
                self.action_pub.publish(action)

            if self.counter % 67 == 0:
                img = Image()
                h = Header()
                h.stamp = t.to_msg()
                h.frame_id = "camera"
                img.header = h
                img.height = 480
                img.width = 640
                img.encoding = "rgb8"
                img.step = 640 * 3
                img.data = np.random.randint(
                    0, 255, (480, 640, 3), dtype=np.uint8
                ).tobytes()
                self.camera_pub.publish(img)

            if self.counter % 1000 == 0:
                m = Float32MultiArray()
                m.data = [random.uniform(20, 40), 35.0, 45.0, 0.0]
                self.metrics_pub.publish(m)
                s = String()
                s.data = f"W2: {self.counter}"
                self.recorder_pub.publish(s)

        except Exception as e:
            pass


def main(args=None):
    try:
        rclpy.init(args=args)
        node = W2Node()
        executor = rclpy.executors.SingleThreadedExecutor()
        executor.add_node(node)

        while rclpy.ok():
            executor.spin_once(timeout_sec=0.1)
    except:
        pass
    finally:
        try:
            node.destroy_node()
        except:
            pass
        try:
            rclpy.shutdown()
        except:
            pass


if __name__ == "__main__":
    main()
