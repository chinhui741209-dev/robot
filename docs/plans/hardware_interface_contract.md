# Hardware Interface Contract (v1.0)

## 1. Overview
This document defines the standardized hardware interface for the robot. All HAL implementations and hardware bridges must adhere to these specifications.

## 2. Communications & Timing
*   **Primary Control Loop:** 1000 Hz (1ms period)
*   **Shared Memory (SHM) Updates:** Must occur within the 1000 Hz loop.
*   **Timestamp Sync:** All sensor data must use `std::chrono::steady_clock` converted to microseconds for `timestamp` fields.
*   **Jitter Tolerance:** Control loop jitter should be < 100μs.

## 3. Sensor Data Standards
### 3.1 IMU (`BuddyImu`)
*   **Orientation:** Quaternion (x, y, z, w). Normalized.
*   **Angular Velocity:** [rad/s].
*   **Linear Acceleration:** [m/s²]. Includes gravity (approx 9.81 on Z when flat).

### 3.2 Joint States (`JointState`)
*   **Position:** [rad].
*   **Velocity:** [rad/s].
*   **Effort:** [Nm] (Torque).
*   **Max DOF:** 32.

## 4. Control Command Standards (`JointCommand`)
*   **q_des:** Desired position [rad].
*   **dq_des:** Desired velocity [rad/s].
*   **kp:** Proportional gain [Nm/rad].
*   **kd:** Derivative gain [Nm/(rad/s)].
*   **tau_ff:** Feed-forward torque [Nm].
*   **Safety Limits:** HAL must enforce hard joint limits and velocity limits.

## 5. Safety & Fault States
### 5.1 Emergency Stop (E-Stop)
*   **SHM Flag:** `estop_active` (bool).
*   **Logic:**
    *   If `estop_active == true`, HAL must zero all `tau_ff` and set `kp`, `kd` to safe idle values or zero (depending on robot type).
    *   Once triggered, `estop_active` can only be cleared by an explicit "Reset" command (to be implemented in `RobotSharedData`).

### 5.2 Fault Mapping
Hardware faults must be mapped to the `watchdog_counter` or a dedicated `fault_bits` field (TBD).
*   **Bit 0:** CAN Bus Error
*   **Bit 1:** Motor Overheat
*   **Bit 2:** Battery Low
*   **Bit 3:** IMU Disconnected

## 6. Watchdog Protocol
*   **HAL Watchdog:** Increments `imu_counter` every 1ms.
*   **Controller Watchdog:** Must increment `watchdog_counter` in SHM at least every 20ms (50Hz).
*   **HAL Action:** If `watchdog_counter` has not changed for > 100ms, HAL enters E-stop mode.
