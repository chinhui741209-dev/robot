#!/usr/bin/env python3
"""
Minimal simulated-sensor publisher (seed of the Phase 2 mock world).

Publishes a coherent synthetic stream so the rest of the ROS 2 graph can run
closed-loop on the Orin with no physical camera/IMU:

Publishes:  /buddy/imu           sensor_msgs/Imu               (rate Hz)
            /perception/objects  vision_msgs/Detection2DArray  (rate Hz)

The motion model is the SAME SimObsSource used by the offline BC collector, so
observations recorded over ROS 2 match the offline training distribution. Run
under a dedicated ROS_DOMAIN_ID to stay isolated from the live robot-core.
"""

import os
import sys

import rclpy
from rclpy.node import Node
import sensor_msgs.msg
from vision_msgs.msg import (
    Detection2DArray, Detection2D, ObjectHypothesisWithPose,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from policy.obs_utils import QUAT, GYRO, ACCEL, I_DET_CX, I_DET_CY, I_DET_SCORE
from scripts.collect_bc_dataset import SimObsSource


class SimSensorsNode(Node):
    def __init__(self):
        super().__init__("sim_sensors")
        self.declare_parameter("rate", 50.0)
        self.declare_parameter("seed", 0)
        self.declare_parameter("img_w", 640)
        self.declare_parameter("img_h", 480)
        # Allow IMU-only mode so a REAL camera+perception can own /perception/objects.
        self.declare_parameter("publish_imu", True)
        self.declare_parameter("publish_det", True)
        self.publish_imu = self.get_parameter("publish_imu").value
        self.publish_det = self.get_parameter("publish_det").value
        rate = self.get_parameter("rate").value
        self.src = SimObsSource(seed=self.get_parameter("seed").value,
                                img_w=self.get_parameter("img_w").value,
                                img_h=self.get_parameter("img_h").value,
                                dt=1.0 / rate)

        self.imu_pub = self.create_publisher(sensor_msgs.msg.Imu, "/buddy/imu", 10)
        self.det_pub = self.create_publisher(Detection2DArray, "/perception/objects", 10)
        self.create_timer(1.0 / rate, self._tick)
        self.get_logger().info(f"Sim sensors publishing at {rate} Hz")

    def _tick(self):
        obs = self.src.step()
        now = self.get_clock().now().to_msg()

        if self.publish_imu:
            self._publish_imu(obs, now)
        if self.publish_det:
            self._publish_det(obs, now)

    def _publish_imu(self, obs, now):
        imu = sensor_msgs.msg.Imu()
        imu.header.stamp = now
        imu.header.frame_id = "imu_link"
        q = obs[QUAT]
        imu.orientation.x, imu.orientation.y = float(q[0]), float(q[1])
        imu.orientation.z, imu.orientation.w = float(q[2]), float(q[3])
        g = obs[GYRO]
        imu.angular_velocity.x, imu.angular_velocity.y, imu.angular_velocity.z = \
            float(g[0]), float(g[1]), float(g[2])
        a = obs[ACCEL]
        imu.linear_acceleration.x, imu.linear_acceleration.y, imu.linear_acceleration.z = \
            float(a[0]), float(a[1]), float(a[2])
        self.imu_pub.publish(imu)

    def _publish_det(self, obs, now):
        det_arr = Detection2DArray()
        det_arr.header.stamp = now
        det_arr.header.frame_id = "camera_link"
        score = float(obs[I_DET_SCORE])
        if score > 0.0:  # SimObsSource emits score=0 on dropout frames
            d = Detection2D()
            d.bbox.center.position.x = float(obs[I_DET_CX])
            d.bbox.center.position.y = float(obs[I_DET_CY])
            d.bbox.size_x, d.bbox.size_y = 40.0, 40.0
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = "target"
            hyp.hypothesis.score = score
            d.results.append(hyp)
            det_arr.detections.append(d)
        self.det_pub.publish(det_arr)


def main(args=None):
    rclpy.init(args=args)
    node = SimSensorsNode()
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
