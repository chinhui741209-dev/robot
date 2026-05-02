#ifndef RT_CPP_SHARED_MEMORY_HPP
#define RT_CPP_SHARED_MEMORY_HPP

#include <stdint.h>
#include <pthread.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>

namespace rt_cpp {

#define SHM_NAME "/robot_shared_data"
#define SHM_SIZE sizeof(RobotSharedData)

struct BuddyImu {
    int64_t timestamp;
    double orientation[4];         // x, y, z, w
    double angular_velocity[3];    // x, y, z
    double linear_acceleration[3]; // x, y, z
};

struct MotorState {
    int64_t timestamp;
    double linear[3];  // x, y, z
    double angular[3]; // x, y, z
};

struct StatePose {
    int64_t timestamp;
    double position[3];    // x, y, z
    double orientation[4]; // x, y, z, w
};

struct RobotSharedData {
    pthread_mutex_t mutex;
    BuddyImu imu;
    MotorState motor;
    StatePose pose;
    bool stop;
    bool estop_active;             // New: Hardware-level emergency stop flag
    uint64_t watchdog_counter;     // New: For heartbeat monitoring
    uint64_t imu_counter;
    uint64_t pose_counter;
};

inline RobotSharedData* init_shared_memory(bool create = false) {
    int fd;
    if (create) {
        shm_unlink(SHM_NAME);
        fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
        if (fd == -1) return nullptr;
        if (ftruncate(fd, SHM_SIZE) == -1) return nullptr;
    } else {
        fd = shm_open(SHM_NAME, O_RDWR, 0666);
        if (fd == -1) return nullptr;
    }

    void* ptr = mmap(NULL, SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (ptr == MAP_FAILED) return nullptr;

    RobotSharedData* shm = static_cast<RobotSharedData*>(ptr);

    if (create) {
        pthread_mutexattr_t attr;
        pthread_mutexattr_init(&attr);
        pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_SHARED);
        pthread_mutex_init(&shm->mutex, &attr);
        shm->stop = false;
        shm->imu_counter = 0;
        shm->pose_counter = 0;
    }

    return shm;
}

} // namespace rt_cpp

#endif // RT_CPP_SHARED_MEMORY_HPP
