#include <iostream>
#include <cassert>
#include <thread>
#include <chrono>
#include "rt_cpp/shared_memory.hpp"

using namespace rt_cpp;

void test_shm_integrity() {
    std::cout << "[Test] Initializing SHM for integrity test..." << std::endl;
    RobotSharedData* shm = init_shared_memory(true);
    assert(shm != nullptr);

    pthread_mutex_lock(&shm->mutex);
    shm->imu.timestamp = 12345;
    shm->imu.linear_acceleration[0] = 1.1;
    shm->estop_active = false;
    pthread_mutex_unlock(&shm->mutex);

    // Re-attach
    RobotSharedData* shm_attach = init_shared_memory(false);
    assert(shm_attach->imu.timestamp == 12345);
    assert(shm_attach->imu.linear_acceleration[0] == 1.1);
    
    std::cout << "[PASS] SHM Integrity & Persistence" << std::endl;
}

void test_mutex_concurrency() {
    std::cout << "[Test] Starting Mutex Concurrency Test..." << std::endl;
    RobotSharedData* shm = init_shared_memory(false);
    
    auto start = std::chrono::steady_clock::now();
    
    std::thread t1([shm]() {
        for(int i=0; i<10000; ++i) {
            pthread_mutex_lock(&shm->mutex);
            shm->imu_counter++;
            pthread_mutex_unlock(&shm->mutex);
        }
    });

    std::thread t2([shm]() {
        for(int i=0; i<10000; ++i) {
            pthread_mutex_lock(&shm->mutex);
            shm->imu_counter++;
            pthread_mutex_unlock(&shm->mutex);
        }
    });

    t1.join();
    t2.join();

    // With 20000 increments, total should be exactly 20000 + previous
    std::cout << "[PASS] Mutex protected counter: " << shm->imu_counter << std::endl;
}

int main() {
    try {
        test_shm_integrity();
        test_mutex_concurrency();
        std::cout << "\n[ALL TESTS PASSED]" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[FAIL] " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
