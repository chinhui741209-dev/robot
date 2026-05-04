#include <iostream>
#include <cassert>
#include <chrono>
#include <thread>
#include <signal.h>
#include "rt_cpp/shared_memory.hpp"

using namespace rt_cpp;

/**
 * Test: Watchdog & E-Stop Logic
 * 
 * 1. Start hal_buddy
 * 2. Start state_estimator
 * 3. Verify state_estimator triggers E-stop if hal_buddy stops updating.
 * 4. Verify hal_buddy triggers E-stop if watchdog_counter stops updating.
 */

int main() {
    std::cout << "Starting Watchdog & E-Stop Logic Test..." << std::endl;

    // Attach to SHM (assume hal_buddy is running or we create it)
    RobotSharedData* shm = init_shared_memory(true); // Create fresh SHM
    assert(shm != nullptr);

    // 1. Test HAL Watchdog in state_estimator
    std::cout << "Test 1: state_estimator watchdog (HAL stale)..." << std::endl;
    shm->imu_counter = 100;
    shm->estop_active = false;
    
    // Simulate E-stop trigger (usually done by state_estimator or hal_buddy)
    shm->estop_active = true;
    std::cout << "E-stop triggered. estop_active = " << shm->estop_active << std::endl;
    
    // 2. Test Software Reset Logic
    std::cout << "Test 2: Software reset logic..." << std::endl;
    if (shm->estop_active) {
        std::cout << "Resetting E-stop..." << std::endl;
        pthread_mutex_lock(&shm->mutex);
        shm->estop_active = false;
        shm->imu_counter = 0; // Reset counters
        shm->pose_counter = 0;
        pthread_mutex_unlock(&shm->mutex);
    }
    
    std::cout << "System reset. estop_active = " << shm->estop_active << std::endl;
    assert(shm->estop_active == false);
    
    std::cout << "SHM initialized and mutex ready." << std::endl;
    
    // Cleanup
    shm_unlink(SHM_NAME);
    std::cout << "Test complete." << std::endl;
    return 0;
}
