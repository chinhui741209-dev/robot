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

    const int rate = 1000;
    const auto dt = std::chrono::nanoseconds(1000000000 / rate);
    auto next_time = std::chrono::steady_clock::now();

    uint64_t counter = 0;
    std::cout << "[hal_buddy] started at " << rate << " Hz via Shared Memory" << std::endl;

    while (!g_stop) {
        next_time += dt;
        std::this_thread::sleep_until(next_time);

        counter++;
        auto now = std::chrono::steady_clock::now();
        int64_t ts = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch()).count();

        pthread_mutex_lock(&shm->mutex);
        
        shm->imu.timestamp = ts;
        shm->imu.orientation[0] = std::sin(counter * 0.001);
        shm->imu.orientation[1] = std::cos(counter * 0.001);
        shm->imu.orientation[2] = std::sin(counter * 0.0005);
        shm->imu.orientation[3] = std::cos(counter * 0.0005);
        
        shm->imu.angular_velocity[0] = std::sin(counter * 0.01) * 0.1;
        shm->imu.angular_velocity[1] = std::cos(counter * 0.01) * 0.1;
        shm->imu.angular_velocity[2] = std::sin(counter * 0.005) * 0.05;
        
        shm->imu.linear_acceleration[0] = std::sin(counter * 0.001) * 9.8;
        shm->imu.linear_acceleration[1] = std::cos(counter * 0.001) * 9.8;
        shm->imu.linear_acceleration[2] = 9.8;

        // Mock 32-DOF Joint States
        for (int i = 0; i < NUM_JOINTS; ++i) {
            shm->joint_state.position[i] = std::sin(counter * 0.001 + i * 0.1);
            shm->joint_state.velocity[i] = std::cos(counter * 0.001 + i * 0.1);
            shm->joint_state.effort[i] = 0.0;
        }

        shm->imu_counter = counter;

        if (shm->stop) g_stop = true;

        pthread_mutex_unlock(&shm->mutex);

        if (counter % 1000 == 0) {
            std::cout << "[hal_buddy] " << counter / 1000 << "k msgs written to SHM" << std::endl;
        }
    }

    shm->stop = true;
    std::cout << "[hal_buddy] stopped" << std::endl;
    return 0;
}
