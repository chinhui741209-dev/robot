#!/usr/bin/env python3
"""
Perception Node - ONNX Object Detection
 Subscribes to camera images and runs object detection
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import (
    Detection2DArray,
    Detection2D,
    BoundingBox2D,
    ObjectHypothesisWithPose,
)
from std_msgs.msg import Header, Float32MultiArray, String
import cv2
import numpy as np
import onnxruntime as ort
import os
import sys

# Add project root to path for package imports
sys.path.insert(0, __file__.rsplit("/perception/", 1)[0])

try:
    from perception.trt_inference import TRTInference
    HAS_TRT = True
except ImportError:
    HAS_TRT = False


class PerceptionNode(Node):
    def __init__(self):
        super().__init__("perception_node")

        self.declare_parameter(
            "model_path", "/home/nvidia/poc/poc-orin/models/active/detection_v2.onnx"
        )
        self.declare_parameter("use_trt", True)
        self.declare_parameter("confidence_threshold", 0.5)
        self.declare_parameter("input_size", 224)
        self.declare_parameter("publish_rate", 10.0)

        self.class_names = ["pen", "box"]

        model_path = self.get_parameter("model_path").value
        self.use_trt = self.get_parameter("use_trt").value
        self.confidence_threshold = self.get_parameter("confidence_threshold").value
        self.input_size = self.get_parameter("input_size").value
        self.publish_rate = self.get_parameter("publish_rate").value

        self.image_sub = self.create_subscription(
            Image, "/camera/image_raw", self.image_callback, 10
        )

        self.detection_pub = self.create_publisher(
            Detection2DArray, "/perception/objects", 10
        )

        self.scene_pub = self.create_publisher(String, "/perception/scene_state", 10)

        self.latency_pub = self.create_publisher(
            Float32MultiArray, "/perception/latency", 10
        )

        self.get_logger().info(f"Loading model: {model_path}")

        # Initialize Inference Backend
        self.trt_engine = None
        self.session = None

        if self.use_trt and HAS_TRT:
            engine_path = model_path.replace(".onnx", ".engine")
            if os.path.exists(engine_path):
                try:
                    self.trt_engine = TRTInference(engine_path)
                    self.get_logger().info(f"Using TensorRT backend: {engine_path}")
                except Exception as e:
                    self.get_logger().warn(f"Failed to load TRT engine, falling back: {e}")

        if self.trt_engine is None:
            try:
                self.session = ort.InferenceSession(model_path)
                self.input_name = self.session.get_inputs()[0].name
                self.output_name = self.session.get_outputs()[0].name
                self.get_logger().info("Using ONNX Runtime backend")
            except Exception as e:
                self.get_logger().error(f"Failed to load model: {e}")
                self.session = None

        self.frame_count = 0
        self.last_fps_time = self.get_clock().now()

    def preprocess(self, image):
        img = cv2.resize(image, (self.input_size, self.input_size))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        return img

    def postprocess(self, output, image_shape):
        detections = []

        if output is None or len(output) == 0:
            return detections

        try:
            output = np.array(output[0])
            if len(output) == 0:
                return detections

            for det in output:
                det = np.array(det)
                if len(det) < 6:
                    continue

                conf = float(det[4])
                if conf < self.confidence_threshold:
                    continue

                cls = int(det[5])
                x = float(det[0])
                y = float(det[1])
                w = float(det[2])
                h = float(det[3])

                x1 = int((x - w / 2) * image_shape[1])
                y1 = int((y - h / 2) * image_shape[0])
                x2 = int((x + w / 2) * image_shape[1])
                y2 = int((y + h / 2) * image_shape[0])

                x1 = max(0, min(x1, image_shape[1]))
                y1 = max(0, min(y1, image_shape[0]))
                x2 = max(0, min(x2, image_shape[1]))
                y2 = max(0, min(y2, image_shape[0]))

                class_name = (
                    self.class_names[cls]
                    if cls < len(self.class_names)
                    else f"class{cls}"
                )

                detections.append(
                    {"bbox": [x1, y1, x2, y2], "confidence": conf, "class": class_name}
                )
        except Exception as e:
            pass

        return detections

    def image_callback(self, msg):
        if self.session is None:
            return

        try:
            import time

            start_time = time.time()

            image = np.frombuffer(msg.data, dtype=np.uint8)
            image = image.reshape(msg.height, msg.width, 3)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            input_data = self.preprocess(image)

            if self.trt_engine:
                outputs = self.trt_engine.run(input_data)
            else:
                outputs = self.session.run(
                    [self.output_name], {self.input_name: input_data}
                )

            detections = self.postprocess(outputs, image.shape)

            detection_msg = Detection2DArray()
            detection_msg.header = Header()
            detection_msg.header.stamp = self.get_clock().now().to_msg()
            detection_msg.header.frame_id = msg.header.frame_id

            for det in detections:
                det_msg = Detection2D()
                det_msg.bbox.center.position.x = (det["bbox"][0] + det["bbox"][2]) / 2
                det_msg.bbox.center.position.y = (det["bbox"][1] + det["bbox"][3]) / 2
                det_msg.bbox.size_x = det["bbox"][2] - det["bbox"][0]
                det_msg.bbox.size_y = det["bbox"][3] - det["bbox"][1]
                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id = det["class"]
                hyp.hypothesis.score = det["confidence"]
                det_msg.results.append(hyp)
                detection_msg.detections.append(det_msg)

            self.detection_pub.publish(detection_msg)

            import json

            scene_objects = []
            for det in detections:
                scene_objects.append(
                    {
                        "class": det.get("class", "unknown"),
                        "x": int(det["bbox"][0]),
                        "y": int(det["bbox"][1]),
                        "confidence": float(det["confidence"]),
                    }
                )
            scene_msg = String()
            scene_msg.data = json.dumps({"objects": scene_objects})
            self.scene_pub.publish(scene_msg)

            latency = (time.time() - start_time) * 1000
            latency_msg = Float32MultiArray()
            latency_msg.data = [latency, float(len(detections))]
            self.latency_pub.publish(latency_msg)

            self.frame_count += 1
            if self.frame_count % 30 == 0:
                self.get_logger().info(
                    f"Latency: {latency:.1f}ms, Detections: {len(detections)}"
                )

        except Exception as e:
            self.get_logger().error(f"Error processing image: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
