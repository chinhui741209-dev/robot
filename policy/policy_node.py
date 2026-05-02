#!/usr/bin/env python3
"""
RL Policy Node — 50 Hz hybrid: LCM-in (IMU) / ROS 2-out (action).

Subscribes:  BUDDY_IMU via LCM (1000 Hz source, consumed at 50 Hz cadence)
Publishes:   /policy/action         Twist          50 Hz  ROS 2
             /policy/action_chunk   Float32MultiArray      ROS 2
             /policy/latency        Float32MultiArray  1 Hz ROS 2

50 Hz is below the LCM-only threshold but this node sits in the RT data path
(reads IMU directly), so we subscribe from LCM to avoid DDS subscription
overhead on the 1 kHz channel.
"""

import sys
import math
import time
import threading
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray
import sensor_msgs.msg
import lcm
import os
import onnxruntime as ort

try:
    from perception.trt_inference import TRTInference
    HAS_TRT = True
except ImportError:
    HAS_TRT = False

sys.path.insert(0, __file__.rsplit("/policy/", 1)[0])
from lcm_types.robot_lcm_types import BuddyImu, BUDDY_IMU


class PolicyNode(Node):
    def __init__(self):
        super().__init__("policy")

        self.declare_parameter("rate", 50)
        self.declare_parameter("sim",  True)
        self.declare_parameter("use_trt", True)
        self.declare_parameter("model_path", "/home/nvidia/poc/poc-orin/models/active/simple_policy.onnx")
        
        self.rate = self.get_parameter("rate").value
        self.sim  = self.get_parameter("sim").value
        self.use_trt = self.get_parameter("use_trt").value
        model_path = self.get_parameter("model_path").value

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

        if self.trt_engine is None and not self.sim:
            try:
                self.session = ort.InferenceSession(model_path)
                self.get_logger().info("Using ONNX Runtime for Policy")
            except Exception as e:
                self.get_logger().error(f"Failed to load Policy ONNX model: {e}")

        self.action_pub       = self.create_publisher(Twist,             "/policy/action",       10)
        self.action_chunk_pub = self.create_publisher(Float32MultiArray, "/policy/action_chunk", 10)
        self.latency_pub      = self.create_publisher(Float32MultiArray, "/policy/latency",      10)

        # ── Data Input: Support both LCM (direct) and ROS 2 (bridged) ─────────
        self.imu_sub = self.create_subscription(sensor_msgs.msg.Imu, "/buddy/imu", self._ros2_imu_handler, 10)
        
        self._lc             = lcm.LCM()
        self._last_imu       = None
        self._imu_lock       = threading.Lock()
        self._inference_count = 0
        self._latencies      = []

        self._lc.subscribe(BUDDY_IMU, self._imu_handler)
        self._lcm_thread = threading.Thread(target=self._lcm_loop, daemon=True)
        self._lcm_thread.start()

        self.create_timer(1.0 / self.rate, self._publish_action)
        self.get_logger().info(f"Policy started at {self.rate} Hz (LCM IMU / ROS2 action)")

    # ── LCM ───────────────────────────────────────────────────────────────────
    def _lcm_loop(self):
        while rclpy.ok():
            self._lc.handle_timeout(1)

    def _imu_handler(self, channel, data):
        with self._imu_lock:
            self._last_imu = BuddyImu.decode(data)
            self._inference_count += 1

    def _ros2_imu_handler(self, msg):
        # Convert ROS 2 IMU message to the internal BuddyImu format
        # This allows the rest of the logic to remain unchanged
        new_imu = BuddyImu()
        new_imu.timestamp = int(msg.header.stamp.sec * 1e6 + msg.header.stamp.nanosec / 1e3)
        new_imu.orientation = [msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w]
        new_imu.angular_velocity = [msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z]
        new_imu.linear_acceleration = [msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z]
        
        with self._imu_lock:
            self._last_imu = new_imu
            self._inference_count += 1

    # ── ROS 2 timer ───────────────────────────────────────────────────────────
    def _publish_action(self):
        start = time.time()

        with self._imu_lock:
            imu = self._last_imu

        t = time.time()
        action = Twist()
        action.linear.x  = math.sin(t)       * 0.1
        action.linear.y  = math.cos(t)       * 0.1
        action.linear.z  = math.sin(t * 0.5) * 0.05
        action.angular.x = math.sin(t * 0.1) * 0.01
        action.angular.y = math.cos(t * 0.1) * 0.01
        action.angular.z = math.sin(t * 0.05) * 0.005

        chunk = Float32MultiArray()
        chunk.data = [
            action.linear.x,  action.linear.y,  action.linear.z,
            action.angular.x, action.angular.y, action.angular.z,
            0.0,
        ]

        self.action_pub.publish(action)
        self.action_chunk_pub.publish(chunk)

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
