#!/usr/bin/env python3
"""
BC Recorder Node.

Records aligned (obs13, act32) Behavior-Cloning pairs by snapshotting the
latest IMU + detection at each /policy/joint_commands message (the action
stream — whether produced by expert_node or the trained policy_node, which
makes this reusable for DAgger). Writes a .npz on shutdown in the SAME format
as scripts/collect_bc_dataset.py so models/build_dataset.py treats host- and
device-collected shards uniformly.

Subscribes:  /buddy/imu             sensor_msgs/Imu
             /perception/objects    vision_msgs/Detection2DArray
             /policy/joint_commands std_msgs/Float32MultiArray[32]
Publishes:   /recorder/status       std_msgs/String   (1 Hz)
"""

import os
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from vision_msgs.msg import Detection2DArray
from std_msgs.msg import String, Float32MultiArray

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from policy.obs_utils import build_obs13_from_msgs, ACT_DIM, OBS_SCHEMA


class Recorder(Node):
    def __init__(self):
        super().__init__("recorder")

        self.declare_parameter("out_dir", "data/bc")
        self.declare_parameter("max_obs_age", 0.5)  # s; older imu/det is stale -> don't pair
        self.out_dir = self.get_parameter("out_dir").value
        self.max_obs_age = float(self.get_parameter("max_obs_age").value)

        self.create_subscription(Imu, "/buddy/imu", self._imu_cb, 10)
        self.create_subscription(Detection2DArray, "/perception/objects", self._det_cb, 10)
        self.create_subscription(Float32MultiArray, "/policy/joint_commands", self._act_cb, 10)
        self.status_pub = self.create_publisher(String, "/recorder/status", 10)
        self.create_timer(1.0, self._publish_status)

        self._last_imu = None
        self._last_det = None
        self._imu_t = 0.0
        self._det_t = 0.0
        self._obs_buf = []
        self._act_buf = []
        self._skipped = 0

        self.get_logger().info(f"BC Recorder started (out_dir={self.out_dir})")

    def _imu_cb(self, msg):
        self._last_imu = msg
        self._imu_t = time.time()

    def _det_cb(self, msg):
        self._last_det = msg
        self._det_t = time.time()

    def _act_cb(self, msg):
        # Pair the action with a FRESH observation; skip if the IMU is stale
        # (topic stalled) and drop a stale detection so we don't bake a phantom
        # target into obs after perception dies.
        now = time.time()
        if self._last_imu is None or (now - self._imu_t) > self.max_obs_age \
                or len(msg.data) < ACT_DIM:
            self._skipped += 1
            return
        det = self._last_det if (now - self._det_t) <= self.max_obs_age else None
        obs = build_obs13_from_msgs(self._last_imu, det)
        act = np.asarray(msg.data[:ACT_DIM], dtype=np.float32)
        self._obs_buf.append(obs)
        self._act_buf.append(act)

    def _publish_status(self):
        s = String()
        s.data = f"pairs:{len(self._obs_buf)} skipped:{self._skipped}"
        self.status_pub.publish(s)

    def flush(self):
        if not self._obs_buf:
            self.get_logger().warn("No pairs recorded; nothing to flush.")
            return
        os.makedirs(self.out_dir, exist_ok=True)
        obs = np.asarray(self._obs_buf, dtype=np.float32)
        act = np.asarray(self._act_buf, dtype=np.float32)
        ts = int(time.time())
        path = os.path.join(self.out_dir, f"recorder_{ts}_n{len(obs)}.npz")
        np.savez(path, obs=obs, act=act,
                 meta=np.array(f"source=recorder_node;obs_schema={OBS_SCHEMA};steps={len(obs)}"))
        self.get_logger().info(f"Wrote {len(obs)} (obs,act) pairs -> {path}")


def main(args=None):
    rclpy.init(args=args)
    node = Recorder()
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
