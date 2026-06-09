#!/usr/bin/env python3
"""
Expert Node — publishes the ScriptedExpert's actions as the policy command
stream so the full ROS 2 system runs closed-loop while we record BC data.

Subscribes:  /buddy/imu            sensor_msgs/Imu
             /perception/objects   vision_msgs/Detection2DArray
Publishes:   /policy/joint_commands Float32MultiArray[32]  (drop-in for policy_node)

When --record is set it also buffers each (obs13, act32) pair and writes a
.npz on shutdown, in the SAME format as scripts/collect_bc_dataset.py so
models/build_dataset.py consumes host- and device-collected shards uniformly.

This is the on-Orin label source for Behavior Cloning. Run it (instead of
policy_node) alongside the sim sensors + perception, then stop it to flush the
dataset. Use a dedicated ROS_DOMAIN_ID to stay isolated from the live
robot-core service.
"""

import os
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from vision_msgs.msg import Detection2DArray
import sensor_msgs.msg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from policy.obs_utils import build_obs13_from_msgs, OBS_DIM, ACT_DIM
from policy.scripted_expert import ScriptedExpert, EXPERT_VERSION, OBS_SCHEMA


class ExpertNode(Node):
    def __init__(self):
        super().__init__("expert")
        self.declare_parameter("rate", 50)
        self.declare_parameter("img_w", 640)
        self.declare_parameter("img_h", 480)
        self.declare_parameter("record", True)
        self.declare_parameter("out_dir", "data/bc")
        self.declare_parameter("max_steps", 0)  # 0 = unbounded

        self.rate = self.get_parameter("rate").value
        self.record = self.get_parameter("record").value
        self.out_dir = self.get_parameter("out_dir").value
        self.max_steps = self.get_parameter("max_steps").value
        self.expert = ScriptedExpert(img_w=self.get_parameter("img_w").value,
                                     img_h=self.get_parameter("img_h").value)

        self.joint_cmd_pub = self.create_publisher(Float32MultiArray, "/policy/joint_commands", 10)
        self.create_subscription(sensor_msgs.msg.Imu, "/buddy/imu", self._imu_cb, 10)
        self.create_subscription(Detection2DArray, "/perception/objects", self._det_cb, 10)

        self._last_imu = None
        self._last_det = None
        self._obs_buf = []
        self._act_buf = []

        self.create_timer(1.0 / self.rate, self._tick)
        self.get_logger().info(f"Expert started at {self.rate} Hz (record={self.record})")

    def _imu_cb(self, msg):
        self._last_imu = msg

    def _det_cb(self, msg):
        self._last_det = msg

    def _tick(self):
        if self._last_imu is None:
            return
        obs = build_obs13_from_msgs(self._last_imu, self._last_det)
        act = self.expert.act(obs)

        msg = Float32MultiArray()
        msg.data = [float(x) for x in act]
        self.joint_cmd_pub.publish(msg)

        if self.record:
            self._obs_buf.append(obs)
            self._act_buf.append(act)
            if self.max_steps and len(self._obs_buf) >= self.max_steps:
                self.get_logger().info(f"Reached max_steps={self.max_steps}; flushing.")
                self.flush()
                raise KeyboardInterrupt

    def flush(self):
        if not self.record or not self._obs_buf:
            return
        os.makedirs(self.out_dir, exist_ok=True)
        obs = np.asarray(self._obs_buf, dtype=np.float32)
        act = np.asarray(self._act_buf, dtype=np.float32)
        ts = int(time.time())
        path = os.path.join(self.out_dir, f"expert_ros2_{ts}_n{len(obs)}.npz")
        np.savez(path, obs=obs, act=act,
                 meta=np.array(f"source=expert_node;expert={EXPERT_VERSION};"
                               f"obs_schema={OBS_SCHEMA};steps={len(obs)}"))
        self.get_logger().info(f"Wrote {len(obs)} (obs,act) pairs -> {path}")


def main(args=None):
    rclpy.init(args=args)
    node = ExpertNode()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    try:
        while rclpy.ok():
            executor.spin_once(timeout_sec=0.001)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.flush()
        except Exception as e:
            node.get_logger().error(f"flush failed: {e}")
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
