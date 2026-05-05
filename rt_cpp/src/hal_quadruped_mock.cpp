#include <iostream>
#include <cmath>
#include <chrono>
#include <thread>
#include <signal.h>
#include <sched.h>
#include "rt_cpp/shared_memory.hpp"

using namespace rt_cpp;

volatile bool g_stop = false;

void signal_handler(int) {
    g_stop = true;
}

/**
 * @brief Mock Quadruped Vendor Implementation
 * Simulates a 12-DOF Quadruped Robot (3 joints per leg)
 */
class QuadrupedVendorStub {
public:
    QuadrupedVendorStub() {
        std::cout << "[QuadrupedVendor] Standardized Adapter Initialized." << std::endl;
    }

    void read(BuddyImu& imu, JointState& joint_state) {
        auto now = std::chrono::steady_clock::now();
        double t = std::chrono::duration<double>(now.time_since_epoch()).count();
        
        imu.timestamp = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch()).count();
        
        // Simulate some slight body oscillation
        imu.orientation[0] = 0.0;
        imu.orientation[1] = 0.0;
        imu.orientation[2] = 0.0;
        imu.orientation[3] = 1.0;
        
        imu.angular_velocity[0] = 0.1 * sin(t);
        imu.linear_acceleration[2] = 9.81 + 0.2 * cos(t);

        // Quadrupeds typically use 12 joints (3 per leg)
        // We map them to the first 12 slots of the 32-DOF interface
        for (int i = 0; i < 12; ++i) {
            joint_state.position[i] = 0.5 * sin(t + i);
            joint_state.velocity[i] = 0.5 * cos(t + i);
            joint_state.effort[i] = 2.0 * sin(t);
        }
        // Zero the rest
        for (int i = 12; i < NUM_JOINTS; ++i) {
            joint_state.position[i] = 0.0;
        }
    }

    void write(const JointCommand& cmd) {
        // Vendor would convert JointCommand (q_des, kp, kd, tau_ff) to their motor drivers
        // For mock, we just acknowledge receipt
    }
};

int main() {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

#ifndef __APPLE__
    struct sched_param param;
    param.sched_priority = 80;
    sched_setscheduler(0, SCHED_FIFO, &param);
#endif

    // Initialize SHM as the creator (Vendor always owns the lifecycle of SHM in this contract)
    RobotSharedData* shm = init_shared_memory(true);
    if (!shm) return 1;

    // --- Identification ---
    shm->version = INTERFACE_VERSION;
    shm->robot_type = ROBOT_TYPE_QUAD;
    // ----------------------

    QuadrupedVendorStub vendor;
    const int rate = 1000;
    const auto dt = std::chrono::nanoseconds(1000000000 / rate);
    auto next_time = std::chrono::steady_clock::now();

    uint64_t counter = 0;
    std::cout << "[QuadrupedVendor] Running standardized loop for QUADRUPED robot..." << std::endl;

    while (!g_stop) {
        next_time += dt;
        std::this_thread::sleep_until(next_time);
        counter++;
        
        pthread_mutex_lock(&shm->mutex);
        
        // Safety: Check Watchdog from Platform
        static uint64_t last_wd = 0;
        static int wd_stale = 0;
        if (shm->watchdog_counter == last_wd) {
            if (++wd_stale > 100) shm->estop_active = true;
        } else {
            wd_stale = 0;
            last_wd = shm->watchdog_counter;
        }

        // Apply E-stop if active
        if (shm->estop_active) {
            // Vendor safety fallback: zero gains
            for (int i = 0; i < NUM_JOINTS; ++i) {
                shm->joint_cmd.kp[i] = 0; shm->joint_cmd.kd[i] = 0;
            }
        }

        vendor.read(shm->imu, shm->joint_state);
        vendor.write(shm->joint_cmd);

        shm->imu_counter = counter;
        if (shm->stop) g_stop = true;

        pthread_mutex_unlock(&shm->mutex);

        if (counter % 1000 == 0) {
            std::cout << "[QuadrupedVendor] Heartbeat OK | Type: QUAD | Counter: " << counter << std::endl;
        }
    }

    shm->stop = true;
    return 0;
}
