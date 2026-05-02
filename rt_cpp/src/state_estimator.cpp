#include <iostream>
#include <cmath>
#include <chrono>
#include <thread>
#include <signal.h>
#include <sched.h>
#include <vector>
#include "rt_cpp/shared_memory.hpp"

using namespace rt_cpp;

volatile bool g_stop = false;

void signal_handler(int) {
    g_stop = true;
}

int main() {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // Set RT priority
#ifndef __APPLE__
    struct sched_param param;
    param.sched_priority = 70;
    if (sched_setscheduler(0, SCHED_FIFO, &param) == -1) {
        std::cerr << "[state_estimator] Warning: failed to set SCHED_FIFO. Run with sudo?" << std::endl;
    }
#endif

    RobotSharedData* shm = init_shared_memory(false);
    while (!shm && !g_stop) {
        std::cout << "[state_estimator] Waiting for HAL to create SHM..." << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(1));
        shm = init_shared_memory(false);
    }

    if (!shm) return 1;

    const int rate = 500;
    const double dt = 1.0 / rate;
    const double imu_dt = 1.0 / 1000.0;
    const auto loop_dt = std::chrono::nanoseconds(1000000000 / rate);
    auto next_time = std::chrono::steady_clock::now();

    double velocity[3] = {0, 0, 0};
    double position[3] = {0, 0, 0};
    uint64_t last_imu_counter = 0;
    uint64_t imu_stale_count = 0;
    uint64_t counter = 0;

    std::cout << "[state_estimator] started at " << rate << " Hz via Shared Memory" << std::endl;

    while (!g_stop) {
        next_time += loop_dt;
        std::this_thread::sleep_until(next_time);

        pthread_mutex_lock(&shm->mutex);
        
        // Watchdog: Check if HAL is still providing data
        if (shm->imu_counter == last_imu_counter) {
            imu_stale_count++;
            if (imu_stale_count > 25) { // 25 samples @ 500Hz = 50ms
                if (!shm->estop_active) {
                    std::cerr << "[state_estimator] WATCHDOG TRIGGERED: HAL data stale!" << std::endl;
                    shm->estop_active = true;
                }
            }
        } else {
            imu_stale_count = 0;
            last_imu_counter = shm->imu_counter;
        }

        // Integration logic...
        if (!shm->estop_active && shm->imu_counter > last_imu_counter) {
            double ax = shm->imu.linear_acceleration[0];
            double ay = shm->imu.linear_acceleration[1];
            double az = shm->imu.linear_acceleration[2] - 9.8;

            // Integrate (crude)
            velocity[0] += ax * imu_dt;
            velocity[1] += ay * imu_dt;
            velocity[2] += az * imu_dt;
            position[0] += velocity[0] * imu_dt;
            position[1] += velocity[1] * imu_dt;
            position[2] += velocity[2] * imu_dt;
            
            last_imu_counter = shm->imu_counter;
        }

        counter++;
        shm->pose.timestamp = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
        shm->pose.position[0] = position[0];
        shm->pose.position[1] = position[1];
        shm->pose.position[2] = position[2];
        
        // Mock orientation
        shm->pose.orientation[0] = std::sin(counter * 0.001);
        shm->pose.orientation[1] = std::cos(counter * 0.001);
        shm->pose.orientation[2] = std::sin(counter * 0.0005);
        shm->pose.orientation[3] = std::cos(counter * 0.0005);
        
        shm->pose_counter = counter;

        if (shm->stop) {
            std::cout << "[state_estimator] Stop flag detected in SHM" << std::endl;
            g_stop = true;
        }

        pthread_mutex_unlock(&shm->mutex);

        if (counter % 500 == 0) {
            printf("[state_estimator] counter=%llu pos=(%.3f, %.3f, %.3f)\n", (unsigned long long)counter, position[0], position[1], position[2]);
        }
    }

    std::cout << "[state_estimator] stopped (g_stop=" << g_stop << ")" << std::endl;
    return 0;
}
