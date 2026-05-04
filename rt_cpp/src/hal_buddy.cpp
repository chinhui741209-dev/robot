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

class HardwareInterfaceStub {
public:
    HardwareInterfaceStub() {
        std::cout << "[HardwareInterfaceStub] Initializing hardware communication..." << std::endl;
    }
    ~HardwareInterfaceStub() {
        std::cout << "[HardwareInterfaceStub] Closing hardware communication..." << std::endl;
    }

    void read(BuddyImu& imu, JointState& joint_state) {
        // In a real implementation, this would call the SDK functions.
        // For now, we provide static/stable data instead of a mock sine wave.
        auto now = std::chrono::steady_clock::now();
        imu.timestamp = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch()).count();
        
        // Identity quaternion
        imu.orientation[0] = 0.0;
        imu.orientation[1] = 0.0;
        imu.orientation[2] = 0.0;
        imu.orientation[3] = 1.0;
        
        for (int i = 0; i < 3; ++i) imu.angular_velocity[i] = 0.0;
        imu.linear_acceleration[0] = 0.0;
        imu.linear_acceleration[1] = 0.0;
        imu.linear_acceleration[2] = 9.81;

        for (int i = 0; i < NUM_JOINTS; ++i) {
            joint_state.position[i] = 0.0;
            joint_state.velocity[i] = 0.0;
            joint_state.effort[i] = 0.0;
        }
    }

    void write(const JointCommand& cmd) {
        // In a real implementation, this would send commands to the actuators.
        // (void)cmd; 
    }
};

int main() {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // Set RT priority
#ifndef __APPLE__
    struct sched_param param;
    param.sched_priority = 80;
    if (sched_setscheduler(0, SCHED_FIFO, &param) == -1) {
        std::cerr << "[hal_buddy] Warning: failed to set SCHED_FIFO. Run with sudo?" << std::endl;
    }
#endif

    RobotSharedData* shm = init_shared_memory(true);
    if (!shm) {
        std::cerr << "[hal_buddy] Failed to init shared memory" << std::endl;
        return 1;
    }

    HardwareInterfaceStub hw;
    const int rate = 1000;
    const auto dt = std::chrono::nanoseconds(1000000000 / rate);
    auto next_time = std::chrono::steady_clock::now();

    uint64_t counter = 0;
    uint64_t last_watchdog_counter = 0;
    uint64_t watchdog_stale_count = 0;
    std::cout << "[hal_buddy] started at " << rate << " Hz via Shared Memory" << std::endl;

    while (!g_stop) {
        next_time += dt;
        std::this_thread::sleep_until(next_time);

        counter++;
        
        pthread_mutex_lock(&shm->mutex);
        
        // Watchdog: Check if controller is alive
        if (shm->watchdog_counter == last_watchdog_counter) {
            watchdog_stale_count++;
            if (watchdog_stale_count > 100) { // 100ms
                if (!shm->estop_active) {
                    std::cerr << "[hal_buddy] WATCHDOG TRIGGERED: No heartbeat from controller!" << std::endl;
                    shm->estop_active = true;
                }
            }
        } else {
            watchdog_stale_count = 0;
            last_watchdog_counter = shm->watchdog_counter;
        }

        // Handle E-stop (Zero commands)
        if (shm->estop_active) {
            for (int i = 0; i < NUM_JOINTS; ++i) {
                shm->joint_cmd.tau_ff[i] = 0.0;
                shm->joint_cmd.kp[i] = 0.0;
                shm->joint_cmd.kd[i] = 0.0;
            }
        }

        // Read from hardware
        hw.read(shm->imu, shm->joint_state);
        
        // Write to hardware
        hw.write(shm->joint_cmd);

        shm->imu_counter = counter;

        if (shm->stop) g_stop = true;

        pthread_mutex_unlock(&shm->mutex);

        if (counter % 1000 == 0) {
            std::cout << "[hal_buddy] " << counter / 1000 << "k msgs processed" << std::endl;
        }
    }

    shm->stop = true;
    std::cout << "[hal_buddy] stopped" << std::endl;
    return 0;
}
