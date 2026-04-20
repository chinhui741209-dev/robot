#!/usr/bin/env python3
"""
USB Camera ROS 2 Node
 Publishes camera images to ROS 2 topics
"""

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

        self.publisher = self.create_publisher(Image, "/camera/image_raw", 10)
        self.timer = self.create_timer(1.0 / self.publish_rate, self.publish_frame)

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

    def publish_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn("Failed to read frame")
            return

        self.frame_count += 1

        msg = Image()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        msg.height = frame.shape[0]
        msg.width = frame.shape[1]
        msg.encoding = "bgr8"
        msg.step = frame.shape[1] * 3
        msg.data = frame.tobytes()

        self.publisher.publish(msg)

        if self.frame_count % 30 == 0:
            self.get_logger().info(f"Published frame {self.frame_count}")

    def destroy_node(self):
        if self.cap:
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
