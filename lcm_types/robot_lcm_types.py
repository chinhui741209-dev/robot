"""
LCM message type definitions for high-frequency RT channels.

Channels:
  BUDDY_IMU        1000 Hz  hal_buddy_node → state_estimator, policy_node
  BUDDY_MOTOR_STATE 1000 Hz  hal_buddy_node → bridge
  BUDDY_HAL_HEALTH  1000 Hz  hal_buddy_node → bridge
  STATE_POSE        500 Hz  state_estimator → bridge, (future) planner

Serialization: big-endian struct (no lcm-gen dependency required).
Run `bash lcm_types/generate_types.sh` to regenerate proper lcm-gen bindings
once full JetPack LCM is installed.
"""

import struct
import time


# ─── Channel name constants ────────────────────────────────────────────────────
BUDDY_IMU         = "BUDDY_IMU"
BUDDY_JOINT_STATE = "BUDDY_JOINT_STATE"
BUDDY_JOINT_CMD   = "BUDDY_JOINT_CMD"
BUDDY_MOTOR_STATE = "BUDDY_MOTOR_STATE"
BUDDY_HAL_HEALTH  = "BUDDY_HAL_HEALTH"
STATE_POSE        = "STATE_POSE"


def _now_us() -> int:
    return int(time.monotonic() * 1e6)


# ─── BuddyImu ─────────────────────────────────────────────────────────────────
# Fields: timestamp(i64) | orientation[4](f64) | angular_velocity[3](f64) | linear_acceleration[3](f64)
# Wire size: 8 + 10*8 = 88 bytes
class BuddyImu:
    _FMT  = ">q10d"
    _SIZE = struct.calcsize(_FMT)  # 88

    __slots__ = ("timestamp", "orientation", "angular_velocity", "linear_acceleration")

    def __init__(self):
        self.timestamp           = _now_us()
        self.orientation         = [0.0, 0.0, 0.0, 1.0]   # x y z w
        self.angular_velocity    = [0.0, 0.0, 0.0]         # rad/s
        self.linear_acceleration = [0.0, 0.0, 9.8]         # m/s²

    def encode(self) -> bytes:
        return struct.pack(
            self._FMT,
            self.timestamp,
            *self.orientation,
            *self.angular_velocity,
            *self.linear_acceleration,
        )

    @classmethod
    def decode(cls, data: bytes) -> "BuddyImu":
        f = struct.unpack(cls._FMT, data[: cls._SIZE])
        msg = cls.__new__(cls)
        msg.timestamp           = f[0]
        msg.orientation         = list(f[1:5])
        msg.angular_velocity    = list(f[5:8])
        msg.linear_acceleration = list(f[8:11])
        return msg


# ─── JointState ───────────────────────────────────────────────────────────────
# Fields: timestamp(i64) | position[32](f64) | velocity[32](f64) | effort[32](f64)
# Wire size: 8 + 96*8 = 776 bytes
class JointState:
    _FMT  = ">q96d"
    _SIZE = struct.calcsize(_FMT)

    __slots__ = ("timestamp", "position", "velocity", "effort")

    def __init__(self):
        self.timestamp = _now_us()
        self.position  = [0.0] * 32
        self.velocity  = [0.0] * 32
        self.effort    = [0.0] * 32

    def encode(self) -> bytes:
        return struct.pack(self._FMT, self.timestamp, *self.position, *self.velocity, *self.effort)

    @classmethod
    def decode(cls, data: bytes) -> "JointState":
        f = struct.unpack(cls._FMT, data[: cls._SIZE])
        msg = cls.__new__(cls)
        msg.timestamp = f[0]
        msg.position  = list(f[1:33])
        msg.velocity  = list(f[33:65])
        msg.effort    = list(f[65:97])
        return msg


# ─── JointCommand ─────────────────────────────────────────────────────────────
# Fields: timestamp(i64) | q_des[32](f64) | dq_des[32](f64) | kp[32](f64) | kd[32](f64) | tau_ff[32](f64)
# Wire size: 8 + 160*8 = 1288 bytes
class JointCommand:
    _FMT  = ">q160d"
    _SIZE = struct.calcsize(_FMT)

    __slots__ = ("timestamp", "q_des", "dq_des", "kp", "kd", "tau_ff")

    def __init__(self):
        self.timestamp = _now_us()
        self.q_des     = [0.0] * 32
        self.dq_des    = [0.0] * 32
        self.kp        = [0.0] * 32
        self.kd        = [0.0] * 32
        self.tau_ff    = [0.0] * 32

    def encode(self) -> bytes:
        return struct.pack(self._FMT, self.timestamp, *self.q_des, *self.dq_des, *self.kp, *self.kd, *self.tau_ff)

    @classmethod
    def decode(cls, data: bytes) -> "JointCommand":
        f = struct.unpack(cls._FMT, data[: cls._SIZE])
        msg = cls.__new__(cls)
        msg.timestamp = f[0]
        msg.q_des     = list(f[1:33])
        msg.dq_des    = list(f[33:65])
        msg.kp        = list(f[65:97])
        msg.kd        = list(f[97:129])
        msg.tau_ff    = list(f[129:161])
        return msg


# ─── MotorState ───────────────────────────────────────────────────────────────
# Fields: timestamp(i64) | linear[3](f64) | angular[3](f64)
# Wire size: 8 + 6*8 = 56 bytes
class MotorState:
    _FMT  = ">q6d"
    _SIZE = struct.calcsize(_FMT)  # 56

    __slots__ = ("timestamp", "linear", "angular")

    def __init__(self):
        self.timestamp = _now_us()
        self.linear    = [0.0, 0.0, 0.0]   # m/s  x y z
        self.angular   = [0.0, 0.0, 0.0]   # rad/s x y z

    def encode(self) -> bytes:
        return struct.pack(self._FMT, self.timestamp, *self.linear, *self.angular)

    @classmethod
    def decode(cls, data: bytes) -> "MotorState":
        f = struct.unpack(cls._FMT, data[: cls._SIZE])
        msg = cls.__new__(cls)
        msg.timestamp = f[0]
        msg.linear    = list(f[1:4])
        msg.angular   = list(f[4:7])
        return msg


# ─── StatePose ────────────────────────────────────────────────────────────────
# Fields: timestamp(i64) | position[3](f64) | orientation[4](f64)
# Wire size: 8 + 7*8 = 64 bytes
class StatePose:
    _FMT  = ">q7d"
    _SIZE = struct.calcsize(_FMT)  # 64

    __slots__ = ("timestamp", "position", "orientation")

    def __init__(self):
        self.timestamp   = _now_us()
        self.position    = [0.0, 0.0, 0.0]        # x y z  metres
        self.orientation = [0.0, 0.0, 0.0, 1.0]   # x y z w

    def encode(self) -> bytes:
        return struct.pack(self._FMT, self.timestamp, *self.position, *self.orientation)

    @classmethod
    def decode(cls, data: bytes) -> "StatePose":
        f = struct.unpack(cls._FMT, data[: cls._SIZE])
        msg = cls.__new__(cls)
        msg.timestamp   = f[0]
        msg.position    = list(f[1:4])
        msg.orientation = list(f[4:8])
        return msg
