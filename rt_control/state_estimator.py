#!/usr/bin/env python3
"""
State Estimator — 500 Hz LCM-in / LCM-out.

Subscribes: BUDDY_IMU  (1000 Hz)  → integrate accel → velocity → position
Publishes:  STATE_POSE (500 Hz)

ROS 2 removed: 500 Hz publish loop with DDS serialization adds 2-5 ms jitter.
lcm_ros2_bridge republishes STATE_POSE to /state/pose for downstream nodes.
"""

import sys
import math
import time
import signal
import threading
import lcm

sys.path.insert(0, __file__.rsplit("/rt_control/", 1)[0])
from lcm_types.robot_lcm_types import (
    BuddyImu, StatePose,
    BUDDY_IMU, STATE_POSE,
)

_RATE  = 500
_DT    = 1.0 / _RATE


class StateEstimator:
    def __init__(self):
        self._lc       = lcm.LCM()
        self._lock     = threading.Lock()
        self._stop     = threading.Event()
        self._counter  = 0
        self._velocity = [0.0, 0.0, 0.0]
        self._position = [0.0, 0.0, 0.0]
        self._orient   = [0.0, 0.0, 0.0, 1.0]

        self._lc.subscribe(BUDDY_IMU, self._imu_handler)

        self._lcm_thread = threading.Thread(target=self._lcm_loop, daemon=True)

    def _imu_handler(self, channel, data):
        msg = BuddyImu.decode(data)
        dt  = 1.0 / 1000.0   # IMU runs at 1kHz

        ax = msg.linear_acceleration[0]
        ay = msg.linear_acceleration[1]
        az = msg.linear_acceleration[2] - 9.8   # remove gravity bias

        with self._lock:
            self._velocity[0] += ax * dt
            self._velocity[1] += ay * dt
            self._velocity[2] += az * dt
            self._position[0] += self._velocity[0] * dt
            self._position[1] += self._velocity[1] * dt
            self._position[2] += self._velocity[2] * dt
            self._orient = msg.orientation[:]

    def _lcm_loop(self):
        while not self._stop.is_set():
            self._lc.handle_timeout(1)   # 1 ms timeout keeps thread responsive

    def run(self):
        self._lcm_thread.start()

        t_next = time.perf_counter()
        print(f"[state_estimator] started at {_RATE} Hz via LCM", flush=True)

        while not self._stop.is_set():
            now = time.perf_counter()
            if now < t_next:
                time.sleep(t_next - now)
            t_next += _DT
            self._counter += 1

            with self._lock:
                pos    = self._position[:]
                orient = self._orient[:]

            pose            = StatePose()
            pose.timestamp  = int(time.monotonic() * 1e6)
            pose.position   = pos
            pose.orientation = [
                math.sin(self._counter * 0.001),
                math.cos(self._counter * 0.001),
                math.sin(self._counter * 0.0005),
                math.cos(self._counter * 0.0005),
            ]
            self._lc.publish(STATE_POSE, pose.encode())

            if self._counter % 500 == 0:
                print(
                    f"[state_estimator] pos=({pos[0]:.3f},{pos[1]:.3f},{pos[2]:.3f})",
                    flush=True,
                )

        self._stop.set()
        print("[state_estimator] stopped", flush=True)

    def stop(self):
        self._stop.set()


def main():
    est = StateEstimator()

    def _sighandler(sig, _frame):
        est.stop()

    signal.signal(signal.SIGTERM, _sighandler)
    signal.signal(signal.SIGINT,  _sighandler)

    est.run()


if __name__ == "__main__":
    main()
