#!/usr/bin/env python3
"""
USB Camera ROS 2 Node
 Publishes camera images to ROS 2 topics
"""

import signal
import sys

signal.signal(signal.SIGTERM, signal.SIG_IGN)
signal.signal(signal.SIGINT, signal.SIG_IGN)

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header
import cv2
import numpy as np


class CameraNode(Node):
    def __init__(self):
        super().__init__("camera_node")

        self.declare_parameter("device", "/dev/video0")
        self.declare_parameter("frame_id", "camera_link")
        self.declare_parameter("publish_rate", 30.0)
        self.declare_parameter("width", 640)
        self.declare_parameter("height", 480)

        self.device = self.get_parameter("device").value
        self.frame_id = self.get_parameter("frame_id").value
        self.publish_rate = self.get_parameter("publish_rate").value
        self.width = self.get_parameter("width").value
        self.height = self.get_parameter("height").value

        self._publisher = None
        self._timer = None
        self._setup_publisher()

        self.cap = None
        self.frame_count = 0

        self.get_logger().info(f"Opening camera: {self.device}")
        self.cap = cv2.VideoCapture(self.device)

        if not self.cap.isOpened():
            self.get_logger().error(f"Failed to open camera: {self.device}")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.get_logger().info(f"Camera opened: {actual_width}x{actual_height}")

    def _setup_publisher(self):
        if self._publisher is not None:
            self.destroy_publisher(self._publisher)
        if self._timer is not None:
            self.destroy_timer(self._timer)
        self._publisher = self.create_publisher(Image, "/camera/image_raw", 1)
        self._timer = self.create_timer(1.0 / self.publish_rate, self.publish_frame)

    def publish_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return

        if not rclpy.ok():
            self.get_logger().warn("Context not OK, recreating publisher")
            self._setup_publisher()
            return

        try:
            ret, frame = self.cap.read()
            if not ret:
                self.get_logger().warn("Failed to read frame")
                return

            self.frame_count += 1

            if not rclpy.ok():
                self.get_logger().warn(
                    "Context not OK after read, recreating publisher"
                )
                self._setup_publisher()
                return

            msg = Image()
            msg.header = Header()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id

            msg.height = frame.shape[0]
            msg.width = frame.shape[1]
            msg.encoding = "bgr8"
            msg.step = frame.shape[1] * 3
            msg.data = frame.tobytes()

            try:
                self._publisher.publish(msg)
            except Exception as pub_err:
                self.get_logger().error(
                    f"Publish error: {pub_err}, recreating publisher"
                )
                self._setup_publisher()
                return

            if self.frame_count % 30 == 0:
                self.get_logger().info(f"Published frame {self.frame_count}")
        except Exception as e:
            self.get_logger().error(f"Frame error: {e}")

    def destroy_node(self):
        if self.cap:
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()

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
