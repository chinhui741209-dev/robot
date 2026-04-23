#!/usr/bin/env python3
"""
Visualization Node - Bounding Box Overlay
 Subscribes to detections and overlays on camera image
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
from std_msgs.msg import Header, String
import cv2
import numpy as np
import json
from collections import deque


class VisualizationNode(Node):
    def __init__(self):
        super().__init__("visualization_node")

        self.declare_parameter("input_image_topic", "/camera/image_raw")
        self.declare_parameter("detection_topic", "/perception/detections")
        self.declare_parameter("output_topic", "/perception/visualization")

        input_topic = self.get_parameter("input_image_topic").value
        detection_topic = self.get_parameter("detection_topic").value
        output_topic = self.get_parameter("output_topic").value

        self.image_sub = self.create_subscription(
            Image, input_topic, self.image_callback, 10
        )

        self.detection_sub = self.create_subscription(
            Detection2DArray, detection_topic, self.detection_callback, 10
        )
        
        self.command_sub = self.create_subscription(
            String, "/task/parsed_command", self.command_callback, 10
        )

        self.visualization_pub = self.create_publisher(Image, output_topic, 10)

        self.latest_detections = None
        self.latest_image = None
        self.image_buffer = deque(maxlen=5)
        
        # State for active task targets
        self.active_source = None
        self.active_target = None

        self.get_logger().info("Visualization node started")

    def command_callback(self, msg):
        try:
            data = json.loads(msg.data)
            self.active_source = data.get("source")
            self.active_target = data.get("target")
            self.get_logger().info(f"Targeting active: {self.active_source} -> {self.active_target}")
        except Exception as e:
            self.get_logger().error(f"Error parsing command in visualization: {e}")

    def detection_callback(self, msg):
        self.latest_detections = msg

    def image_callback(self, msg):
        try:
            image = np.frombuffer(msg.data, dtype=np.uint8)
            image = image.reshape(msg.height, msg.width, 3)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if self.latest_detections is not None:
                for det in self.latest_detections.detections:
                    x = int(det.bbox.center.position.x)
                    y = int(det.bbox.center.position.y)
                    w = int(det.bbox.size_x)
                    h = int(det.bbox.size_y)

                    x1 = int(x - w / 2)
                    y1 = int(y - h / 2)
                    x2 = int(x + w / 2)
                    y2 = int(y + h / 2)

                    conf = det.results[0].hypothesis.confidence
                    class_id = det.results[0].hypothesis.class_id
                    label = f"{class_id}: {conf:.2f}"

                    # Default styling (Green)
                    color = (0, 255, 0)
                    thickness = 2

                    # Highlight based on active command
                    if class_id == self.active_source:
                        color = (0, 0, 255) # Red for source/target to pick
                        thickness = 4
                        label = f"[TARGET] {label}"
                    elif class_id == self.active_target:
                        color = (255, 0, 0) # Blue for destination
                        thickness = 3
                        label = f"[DEST] {label}"

                    cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
                    cv2.putText(
                        image,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        thickness,
                    )

            vis_msg = Image()
            vis_msg.header = Header()
            vis_msg.header.stamp = self.get_clock().now().to_msg()
            vis_msg.header.frame_id = msg.header.frame_id
            vis_msg.height = image.shape[0]
            vis_msg.width = image.shape[1]
            vis_msg.encoding = "bgr8"
            vis_msg.step = image.shape[1] * 3
            vis_msg.data = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).tobytes()

            self.visualization_pub.publish(vis_msg)

        except Exception as e:
            self.get_logger().error(f"Error: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = VisualizationNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
