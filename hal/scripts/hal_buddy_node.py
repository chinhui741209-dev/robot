#!/usr/bin/env python3
"""
HAL Buddy Node - Simulated data source for testing
"""

import sys
import math
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Twist
from std_msgs.msg import String


class HalBuddyNode(Node):
    def __init__(self):
        super().__init__("hal_buddy")

        self.declare_parameter("rate", 1000)
        self.declare_parameter("sim", True)
        self.rate = self.get_parameter("rate").value
        self.sim = self.get_parameter("sim").value

        self.imu_pub = self.create_publisher(Imu, "/buddy/imu", 10)
        self.motor_pub = self.create_publisher(Twist, "/buddy/motor_state", 10)
        self.health_pub = self.create_publisher(String, "/buddy/hal/health", 10)

        self.timer = self.create_timer(1.0 / self.rate, self.publish_data)

        self.counter = 0
        self.get_logger().info(f"HAL Buddy started at {self.rate} Hz (sim={self.sim})")

    def publish_data(self):
        try:
            self.counter += 1

            imu_msg = Imu()
            t = self.get_clock().now()

            imu_msg.header.stamp = t.to_msg()
            imu_msg.header.frame_id = "imu_link"
            imu_msg.orientation.x = math.sin(self.counter * 0.001)
            imu_msg.orientation.y = math.cos(self.counter * 0.001)
            imu_msg.orientation.z = math.sin(self.counter * 0.0005)
            imu_msg.orientation.w = math.cos(self.counter * 0.0005)

            imu_msg.angular_velocity.x = math.sin(self.counter * 0.01) * 0.1
            imu_msg.angular_velocity.y = math.cos(self.counter * 0.01) * 0.1
            imu_msg.angular_velocity.z = math.sin(self.counter * 0.005) * 0.05

            imu_msg.linear_acceleration.x = math.sin(self.counter * 0.001) * 9.8
            imu_msg.linear_acceleration.y = math.cos(self.counter * 0.001) * 9.8
            imu_msg.linear_acceleration.z = 9.8

            twist_msg = Twist()
            health_msg = String()
            health_msg.data = "OK"

            self.imu_pub.publish(imu_msg)
            self.motor_pub.publish(twist_msg)
            self.health_pub.publish(health_msg)

        except Exception as e:
            self.get_logger().error(f"Publish error: {e}", throttle_duration_sec=1)


def main(args=None):
    rclpy.init(args=args)
    node = HalBuddyNode()

    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)

    try:
        while rclpy.ok():
            executor.spin_once(timeout_sec=0.001)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
