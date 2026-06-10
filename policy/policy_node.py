#!/usr/bin/env python3
"""
Policy Node — 50 Hz Pure ROS 2.

Subscribes:  /buddy/imu             sensor_msgs/Imu              100 Hz
             /joint_states          sensor_msgs/JointState       100 Hz
             /perception/objects    vision_msgs/Detection2DArray  15 Hz
Publishes:   /policy/joint_commands Float32MultiArray[32]         50 Hz (joint position targets)
             /policy/action_chunk   Float32MultiArray              50 Hz (output + sim flag)
             /policy/latency        Float32MultiArray               1 Hz (avg_ms, p99_ms)

Model: (batch, 13) -> (batch, 32)
  Input:  Quat(4) + Gyro(3) + Accel(3) + Detection(3)
  Output: 32 joint position targets
"""

import sys
import math
import time
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from vision_msgs.msg import Detection2DArray
import sensor_msgs.msg
import numpy as np
import os
import onnxruntime as ort

try:
    from perception.trt_inference import TRTInference
    HAS_TRT = True
except ImportError:
    HAS_TRT = False


class PolicyNode(Node):
    def __init__(self):
        super().__init__("policy")

        self.declare_parameter("rate", 50)
        self.declare_parameter("sim",  True)
        self.declare_parameter("use_trt", True)
        self.declare_parameter("model_path", "models/active/simple_policy.onnx")
        
        self.rate = self.get_parameter("rate").value
        self.sim  = self.get_parameter("sim").value
        self.use_trt = self.get_parameter("use_trt").value
        model_path = self.get_parameter("model_path").value
        
        # Absolute path check
        if not os.path.isabs(model_path):
            poc_root = os.environ.get("POC_ROOT", os.getcwd())
            model_path = os.path.join(poc_root, model_path)

        # Initialize Inference Backend
        self.trt_engine = None
        self.session = None

        if self.use_trt and HAS_TRT:
            engine_path = model_path.replace(".onnx", ".engine")
            if os.path.exists(engine_path):
                try:
                    self.trt_engine = TRTInference(engine_path)
                    self.get_logger().info(f"Using TensorRT for Policy: {engine_path}")
                except Exception as e:
                    self.get_logger().warn(f"Failed to load Policy TRT engine: {e}")

        if self.trt_engine is None:
            try:
                self.session = ort.InferenceSession(model_path)
                self.get_logger().info(f"Using ONNX Runtime for Policy: {model_path}")
            except Exception as e:
                self.get_logger().error(f"Failed to load Policy ONNX model: {e}")

        self.joint_cmd_pub    = self.create_publisher(Float32MultiArray, "/policy/joint_commands", 10)
        self.action_chunk_pub = self.create_publisher(Float32MultiArray, "/policy/action_chunk", 10)
        self.latency_pub      = self.create_publisher(Float32MultiArray, "/policy/latency",      10)

        # ── Data Input ────────────────────────────────────────────────────────
        self.imu_sub = self.create_subscription(sensor_msgs.msg.Imu, "/buddy/imu", self._ros2_imu_handler, 10)
        self.joint_sub = self.create_subscription(sensor_msgs.msg.JointState, "/joint_states", self._ros2_joint_handler, 10)
        self.det_sub = self.create_subscription(Detection2DArray, "/perception/objects", self._ros2_det_handler, 10)
        
        self._last_imu       = None
        self._last_joints    = None
        self._last_det       = None
        self._imu_lock       = threading.Lock()
        self._joint_lock     = threading.Lock()
        self._det_lock       = threading.Lock()
        self._inference_count = 0
        self._latencies      = []

        self.create_timer(1.0 / self.rate, self._publish_action)
        self.get_logger().info(f"Policy started at {self.rate} Hz [SIM={self.sim}]")

    def _ros2_joint_handler(self, msg):
        with self._joint_lock:
            self._last_joints = msg

    def _ros2_imu_handler(self, msg):
        with self._imu_lock:
            self._last_imu = msg

    def _ros2_det_handler(self, msg):
        with self._det_lock:
            self._last_det = msg

    # ── ROS 2 timer ───────────────────────────────────────────────────────────
    def _publish_action(self):
        start = time.time()

        with self._imu_lock:
            imu = self._last_imu
        
        with self._det_lock:
            det_msg = self._last_det
        
        # If no IMU data, we can't run real inference (unless in mock mode)
        if imu is None:
            return

        # Prepare Perception data (highest score detection; guard empty results)
        det_data = [0.0, 0.0, 0.0] # x, y, score
        cand = [d for d in det_msg.detections if d.results] if det_msg else []
        if cand:
            best_det = max(cand, key=lambda d: d.results[0].hypothesis.score)
            det_data = [
                best_det.bbox.center.position.x,
                best_det.bbox.center.position.y,
                best_det.results[0].hypothesis.score
            ]

        # Prepare 13-dim input: [Quat(4), Gyro(3), Accel(3), Det(3)]
        input_data = np.array([[
            imu.orientation.x, imu.orientation.y, imu.orientation.z, imu.orientation.w,
            imu.angular_velocity.x, imu.angular_velocity.y, imu.angular_velocity.z,
            imu.linear_acceleration.x, imu.linear_acceleration.y, imu.linear_acceleration.z,
            det_data[0], det_data[1], det_data[2]
        ]], dtype=np.float32)

        # Run Inference
        try:
            if self.trt_engine:
                output_list = self.trt_engine.run(input_data)
                output = output_list[0].reshape(1, -1)
            elif self.session:
                input_name = self.session.get_inputs()[0].name
                output = self.session.run(None, {input_name: input_data})[0]
            else:
                # Fallback to mock if no model loaded (32 joints)
                t = time.time()
                output = np.array([[math.sin(t + i*0.1)*0.1 for i in range(32)]])
        except Exception as e:
            self.get_logger().error(f"Inference error: {e}")
            return

        # Map to JointCommand (Float32MultiArray)
        joint_msg = Float32MultiArray()
        joint_msg.data = [float(x) for x in output[0]]
        self.joint_cmd_pub.publish(joint_msg)

        chunk = Float32MultiArray()
        chunk.data = [float(x) for x in output[0]]
        if self.sim:
            chunk.data.append(1.0) # Mark as SIM in metadata
        else:
            chunk.data.append(0.0)

        self.action_chunk_pub.publish(chunk)
        self._inference_count += 1

        latency = (time.time() - start) * 1000
        self._latencies.append(latency)
        if len(self._latencies) > 1000:
            self._latencies.pop(0)

        if self._inference_count % 100 == 0 and self._latencies:
            avg = sum(self._latencies) / len(self._latencies)
            p99 = sorted(self._latencies)[int(len(self._latencies) * 0.99)]
            lat_msg = Float32MultiArray()
            lat_msg.data = [avg, p99]
            self.latency_pub.publish(lat_msg)
            self.get_logger().info(f"Latency avg={avg:.2f}ms p99={p99:.2f}ms  imu_rx={self._inference_count}")


def main(args=None):
    rclpy.init(args=args)
    node = PolicyNode()

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
