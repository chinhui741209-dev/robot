#!/usr/bin/env python3
"""
HAL Buddy Node — 1000 Hz LCM publisher.

Publishes to three LCM channels:
  BUDDY_IMU          BuddyImu    1000 Hz
  BUDDY_MOTOR_STATE  MotorState  1000 Hz
  BUDDY_HAL_HEALTH   bytes(str)  1000 Hz

ROS 2 removed: DDS jitter is incompatible with 1 kHz hard loops.
Use lcm_ros2_bridge to re-expose these channels as ROS 2 topics for
downstream orchestration nodes (recorder, GUI).
"""

import sys
import math
import time
import signal
import threading
import lcm

sys.path.insert(0, __file__.rsplit("/hal/", 1)[0])
from lcm_types.robot_lcm_types import (
    BuddyImu, MotorState,
    BUDDY_IMU, BUDDY_MOTOR_STATE, BUDDY_HAL_HEALTH,
)

_RATE  = 1000
_DT    = 1.0 / _RATE
_stop  = threading.Event()


def _sighandler(sig, _frame):
    _stop.set()


def main():
    print("==========================================")
    print("WARNING: hal_buddy_node.py (Python/LCM) is DEPRECATED.")
    print("Use C++ SHM implementation in rt_cpp/ instead.")
    print("==========================================")
    signal.signal(signal.SIGTERM, _sighandler)
    signal.signal(signal.SIGINT,  _sighandler)

    lc      = lcm.LCM()
    counter = 0
    t_next  = time.perf_counter()

    print(f"[hal_buddy] started at {_RATE} Hz via LCM", flush=True)

    while not _stop.is_set():
        now = time.perf_counter()
        if now < t_next:
            time.sleep(t_next - now)
        t_next += _DT
        counter += 1

        ts = int(time.monotonic() * 1e6)

        imu = BuddyImu()
        imu.timestamp = ts
        imu.orientation = [
            math.sin(counter * 0.001),
            math.cos(counter * 0.001),
            math.sin(counter * 0.0005),
            math.cos(counter * 0.0005),
        ]
        imu.angular_velocity = [
            math.sin(counter * 0.01) * 0.1,
            math.cos(counter * 0.01) * 0.1,
            math.sin(counter * 0.005) * 0.05,
        ]
        imu.linear_acceleration = [
            math.sin(counter * 0.001) * 9.8,
            math.cos(counter * 0.001) * 9.8,
            9.8,
        ]
        lc.publish(BUDDY_IMU, imu.encode())

        motor = MotorState()
        motor.timestamp = ts
        lc.publish(BUDDY_MOTOR_STATE, motor.encode())

        lc.publish(BUDDY_HAL_HEALTH, b"OK")

        if counter % 1000 == 0:
            print(f"[hal_buddy] {counter // 1000}k msgs published", flush=True)

    print("[hal_buddy] stopped", flush=True)


if __name__ == "__main__":
    main()
