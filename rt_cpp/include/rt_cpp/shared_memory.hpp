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
#define NUM_JOINTS 32
#define SHM_SIZE sizeof(RobotSharedData)

// Interface Metadata for multi-vendor standardization
#define INTERFACE_VERSION 100 // v1.0.0
#define ROBOT_TYPE_GENERIC 0
#define ROBOT_TYPE_ARM     1
#define ROBOT_TYPE_BIPED   2
#define ROBOT_TYPE_QUAD    3
#define ROBOT_TYPE_AMR     4

struct BuddyImu {
    int64_t timestamp;             // [OWNER: VENDOR]
    double orientation[4];         // [OWNER: VENDOR] x, y, z, w
    double angular_velocity[3];    // [OWNER: VENDOR] x, y, z
    double linear_acceleration[3]; // [OWNER: VENDOR] x, y, z
};

struct JointState {
    double position[NUM_JOINTS];   // [OWNER: VENDOR] rad
    double velocity[NUM_JOINTS];   // [OWNER: VENDOR] rad/s
    double effort[NUM_JOINTS];     // [OWNER: VENDOR] Nm
};

struct JointCommand {
    double q_des[NUM_JOINTS];      // [OWNER: PLATFORM] target pos
    double dq_des[NUM_JOINTS];     // [OWNER: PLATFORM] target vel
    double kp[NUM_JOINTS];         // [OWNER: PLATFORM] proportional gain
    double kd[NUM_JOINTS];         // [OWNER: PLATFORM] derivative gain
    double tau_ff[NUM_JOINTS];     // [OWNER: PLATFORM] feed-forward torque
};

struct StatePose {
    int64_t timestamp;             // [OWNER: PLATFORM]
    double position[3];            // [OWNER: PLATFORM] x, y, z
    double orientation[4];         // [OWNER: PLATFORM] x, y, z, w
};

/**
 * @brief Standardized Hardware Interface Contract
 * This structure is the ONLY touchpoint between Platform and Vendor.
 */
struct RobotSharedData {
    pthread_mutex_t mutex;
    
    // Header Info
    uint32_t version;              // Contract version (INTERFACE_VERSION)
    uint32_t robot_type;           // Type of robot connected
    
    // Vendor Data (Inbound to Platform)
    BuddyImu imu;
    JointState joint_state;
    uint64_t imu_counter;          // Incremented by Vendor @1kHz
    
    // Platform Data (Outbound to Vendor)
    JointCommand joint_cmd;
    StatePose pose;                // Calculated by Platform
    uint64_t watchdog_counter;     // Incremented by Platform @100Hz
    uint64_t pose_counter;         // Incremented by Platform @500Hz
    
    // Control Flags
    bool stop;                     // Request global stop
    bool estop_active;             // Emergency stop status
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
