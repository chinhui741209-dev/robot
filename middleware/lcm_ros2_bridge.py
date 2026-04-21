#!/usr/bin/env python3
"""
LCM → ROS 2 Bridge.

Subscribes to high-frequency LCM channels and republishes as ROS 2 topics
for downstream orchestration nodes (recorder, GUI, planner) that do not
need raw 1 kHz/500 Hz rates.

LCM channel    → ROS 2 topic             publish rate
─────────────────────────────────────────────────────
BUDDY_IMU      → /buddy/imu              100 Hz (decimated from 1 kHz)
BUDDY_MOTOR    → /buddy/motor_state      100 Hz
BUDDY_HEALTH   → /buddy/hal/health        10 Hz
STATE_POSE     → /state/pose             100 Hz (decimated from 500 Hz)

Decimation avoids flooding ROS 2 DDS with full RT rates while preserving
observability for logging and diagnostics.
"""

import sys
import threading
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Pose, Twist
from std_msgs.msg import String
import lcm

sys.path.insert(0, __file__.rsplit("/middleware/", 1)[0])
from lcm_types.robot_lcm_types import (
    BuddyImu, MotorState, StatePose,
    BUDDY_IMU, BUDDY_MOTOR_STATE, BUDDY_HAL_HEALTH, STATE_POSE,
)

# Publish at most once every N microseconds per channel
_IMU_INTERVAL_US    = 10_000   # 100 Hz
_MOTOR_INTERVAL_US  = 10_000   # 100 Hz
_HEALTH_INTERVAL_US = 100_000  # 10 Hz
_POSE_INTERVAL_US   = 10_000   # 100 Hz


class LcmRos2Bridge(Node):
    def __init__(self):
        super().__init__("lcm_ros2_bridge")

        self._imu_pub    = self.create_publisher(Imu,   "/buddy/imu",         10)
        self._motor_pub  = self.create_publisher(Twist, "/buddy/motor_state",  10)
        self._health_pub = self.create_publisher(String,"/buddy/hal/health",   10)
        self._pose_pub   = self.create_publisher(Pose,  "/state/pose",         10)

        self._last_us = {
            BUDDY_IMU:         0,
            BUDDY_MOTOR_STATE: 0,
            BUDDY_HAL_HEALTH:  0,
            STATE_POSE:        0,
        }
        self._intervals = {
            BUDDY_IMU:         _IMU_INTERVAL_US,
            BUDDY_MOTOR_STATE: _MOTOR_INTERVAL_US,
            BUDDY_HAL_HEALTH:  _HEALTH_INTERVAL_US,
            STATE_POSE:        _POSE_INTERVAL_US,
        }

        self._lc = lcm.LCM()
        self._lc.subscribe(BUDDY_IMU,         self._on_imu)
        self._lc.subscribe(BUDDY_MOTOR_STATE, self._on_motor)
        self._lc.subscribe(BUDDY_HAL_HEALTH,  self._on_health)
        self._lc.subscribe(STATE_POSE,        self._on_pose)

        self._lcm_thread = threading.Thread(target=self._lcm_loop, daemon=True)
        self._lcm_thread.start()

        self.get_logger().info("LCM→ROS2 bridge started (IMU@100Hz, Pose@100Hz)")

    def _throttle(self, channel: str) -> bool:
        now = int(time.monotonic() * 1e6)
        if now - self._last_us[channel] >= self._intervals[channel]:
            self._last_us[channel] = now
            return True
        return False

    def _on_imu(self, channel, data):
        if not self._throttle(channel):
            return
        msg_in = BuddyImu.decode(data)
        msg = Imu()
        msg.header.stamp            = self.get_clock().now().to_msg()
        msg.header.frame_id         = "imu_link"
        msg.orientation.x           = msg_in.orientation[0]
        msg.orientation.y           = msg_in.orientation[1]
        msg.orientation.z           = msg_in.orientation[2]
        msg.orientation.w           = msg_in.orientation[3]
        msg.angular_velocity.x      = msg_in.angular_velocity[0]
        msg.angular_velocity.y      = msg_in.angular_velocity[1]
        msg.angular_velocity.z      = msg_in.angular_velocity[2]
        msg.linear_acceleration.x   = msg_in.linear_acceleration[0]
        msg.linear_acceleration.y   = msg_in.linear_acceleration[1]
        msg.linear_acceleration.z   = msg_in.linear_acceleration[2]
        self._imu_pub.publish(msg)

    def _on_motor(self, channel, data):
        if not self._throttle(channel):
            return
        msg_in = MotorState.decode(data)
        msg = Twist()
        msg.linear.x  = msg_in.linear[0]
        msg.linear.y  = msg_in.linear[1]
        msg.linear.z  = msg_in.linear[2]
        msg.angular.x = msg_in.angular[0]
        msg.angular.y = msg_in.angular[1]
        msg.angular.z = msg_in.angular[2]
        self._motor_pub.publish(msg)

    def _on_health(self, channel, data):
        if not self._throttle(channel):
            return
        msg = String()
        msg.data = data.decode("utf-8", errors="replace")
        self._health_pub.publish(msg)

    def _on_pose(self, channel, data):
        if not self._throttle(channel):
            return
        msg_in = StatePose.decode(data)
        msg = Pose()
        msg.position.x    = msg_in.position[0]
        msg.position.y    = msg_in.position[1]
        msg.position.z    = msg_in.position[2]
        msg.orientation.x = msg_in.orientation[0]
        msg.orientation.y = msg_in.orientation[1]
        msg.orientation.z = msg_in.orientation[2]
        msg.orientation.w = msg_in.orientation[3]
        self._pose_pub.publish(msg)

    def _lcm_loop(self):
        while rclpy.ok():
            self._lc.handle_timeout(1)


def main(args=None):
    rclpy.init(args=args)
    node = LcmRos2Bridge()

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
