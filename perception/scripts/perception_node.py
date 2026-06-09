#!/usr/bin/env python3
"""
Perception Node - ONNX/YOLOv8 Object Detection (Phase 3).

Fixes the detection decoding: detection_v2.onnx is a YOLOv8 model with output
(1, 4+nc, anchors). The old per-row [x,y,w,h,conf,cls] postprocess produced
garbage; this uses the shared, tested decoder in perception/detection_utils.py.
Class names come from perception/classes.py (single source of truth) and the
model path is resolved against POC_ROOT (no hardcoded /home/nvidia/... path).

Subscribes:  /camera/image_raw    sensor_msgs/Image
Publishes:   /perception/objects  vision_msgs/Detection2DArray
             /perception/scene_state  std_msgs/String (JSON)
             /perception/latency  std_msgs/Float32MultiArray
"""

import os
import sys
import json
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import (
    Detection2DArray, Detection2D, ObjectHypothesisWithPose,
)
from std_msgs.msg import Header, Float32MultiArray, String
import cv2
import numpy as np
import onnxruntime as ort

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from perception.detection_utils import decode_yolov8
from perception.classes import get_class_names, resolve_path

try:
    from perception.trt_inference import TRTInference
    HAS_TRT = True
except ImportError:
    HAS_TRT = False


class PerceptionNode(Node):
    def __init__(self):
        super().__init__("perception_node")

        self.declare_parameter("model_path", "models/active/detection_v2.onnx")
        self.declare_parameter("use_trt", True)
        self.declare_parameter("confidence_threshold", 0.5)
        self.declare_parameter("iou_threshold", 0.45)
        self.declare_parameter("input_size", 224)

        self.class_names = get_class_names()
        model_path = resolve_path(self.get_parameter("model_path").value)
        self.use_trt = self.get_parameter("use_trt").value
        self.conf = self.get_parameter("confidence_threshold").value
        self.iou = self.get_parameter("iou_threshold").value
        self.input_size = self.get_parameter("input_size").value

        self.create_subscription(Image, "/camera/image_raw", self.image_callback, 10)
        self.detection_pub = self.create_publisher(Detection2DArray, "/perception/objects", 10)
        self.scene_pub = self.create_publisher(String, "/perception/scene_state", 10)
        self.latency_pub = self.create_publisher(Float32MultiArray, "/perception/latency", 10)

        self.trt_engine = None
        self.session = None
        if self.use_trt and HAS_TRT:
            engine_path = model_path.replace(".onnx", ".engine")
            if os.path.exists(engine_path):
                try:
                    self.trt_engine = TRTInference(engine_path)
                    self.get_logger().info(f"Using TensorRT backend: {engine_path}")
                except Exception as e:
                    self.get_logger().warn(f"TRT load failed, falling back: {e}")
        if self.trt_engine is None:
            try:
                self.session = ort.InferenceSession(model_path)
                self.input_name = self.session.get_inputs()[0].name
                self.get_logger().info(f"ONNX Runtime backend: {model_path}")
            except Exception as e:
                self.get_logger().error(f"Failed to load detection model: {e}")
        self.get_logger().info(f"Perception classes: {self.class_names}")
        self.frame_count = 0

    def preprocess(self, image):
        img = cv2.resize(image, (self.input_size, self.input_size)).astype(np.float32) / 255.0
        return np.expand_dims(np.transpose(img, (2, 0, 1)), axis=0)

    def image_callback(self, msg):
        if self.session is None and self.trt_engine is None:
            return
        try:
            start = time.time()
            image = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
            inp = self.preprocess(image)
            if self.trt_engine:
                out = self.trt_engine.run(inp)[0]
            else:
                out = self.session.run(None, {self.input_name: inp})[0]

            dets = decode_yolov8(out, msg.width, msg.height, input_size=self.input_size,
                                 conf_thresh=self.conf, iou_thresh=self.iou,
                                 class_names=self.class_names)

            det_arr = Detection2DArray()
            det_arr.header = Header()
            det_arr.header.stamp = self.get_clock().now().to_msg()
            det_arr.header.frame_id = msg.header.frame_id
            for d in dets:
                dm = Detection2D()
                dm.bbox.center.position.x = d["cx"]
                dm.bbox.center.position.y = d["cy"]
                dm.bbox.size_x = d["w"]; dm.bbox.size_y = d["h"]
                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id = d["class"]
                hyp.hypothesis.score = d["score"]
                dm.results.append(hyp)
                det_arr.detections.append(dm)
            self.detection_pub.publish(det_arr)

            scene = {"objects": [{"class": d["class"], "x": int(d["cx"]), "y": int(d["cy"]),
                                  "confidence": round(d["score"], 3)} for d in dets]}
            self.scene_pub.publish(String(data=json.dumps(scene)))

            latency = (time.time() - start) * 1000
            self.latency_pub.publish(Float32MultiArray(data=[latency, float(len(dets))]))
            self.frame_count += 1
            if self.frame_count % 30 == 0:
                self.get_logger().info(f"Latency {latency:.1f}ms, detections {len(dets)}")
        except Exception as e:
            self.get_logger().error(f"Error processing image: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, Exception):
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
