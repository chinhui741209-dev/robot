#include <chrono>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "std_msgs/msg/string.hpp"
#include "std_msgs/msg/bool.hpp"
#include "std_srvs/srv/trigger.hpp"
#include "rt_cpp/shared_memory.hpp"

using namespace std::chrono_literals;
using namespace rt_cpp;

class RobotRTBridge : public rclcpp::Node {
public:
    RobotRTBridge() : Node("robot_rt_bridge") {
        imu_pub_ = this->create_publisher<sensor_msgs::msg::Imu>("/buddy/imu", 10);
        joint_pub_ = this->create_publisher<sensor_msgs::msg::JointState>("/joint_states", 10);
        pose_pub_ = this->create_publisher<geometry_msgs::msg::PoseStamped>("/state/pose", 10);
        health_pub_ = this->create_publisher<std_msgs::msg::String>("/buddy/hal/health", 10);
        estop_reset_sub_ = this->create_subscription<std_msgs::msg::Bool>(
            "/estop_reset", 10, std::bind(&RobotRTBridge::estop_reset_callback, this, std::placeholders::_1));
        estop_sub_ = this->create_subscription<std_msgs::msg::Bool>(
            "/estop", 10, std::bind(&RobotRTBridge::estop_callback, this, std::placeholders::_1));
        estop_reset_srv_ = this->create_service<std_srvs::srv::Trigger>(
            "/estop_reset",
            std::bind(&RobotRTBridge::estop_reset_srv_callback, this,
                      std::placeholders::_1, std::placeholders::_2));

        // Initialize joint names
        joint_msg_.name.resize(NUM_JOINTS);
        joint_msg_.position.resize(NUM_JOINTS);
        joint_msg_.velocity.resize(NUM_JOINTS);
        joint_msg_.effort.resize(NUM_JOINTS);
        for (int i = 0; i < NUM_JOINTS; ++i) {
            joint_msg_.name[i] = "joint_" + std::to_string(i + 1);
        }

        shm_ = init_shared_memory(false);
        if (!shm_) {
            RCLCPP_ERROR(this->get_logger(), "Failed to attach to Shared Memory. Is hal_buddy running?");
        }

        timer_ = this->create_wall_timer(10ms, std::bind(&RobotRTBridge::timer_callback, this));
    }

private:
    void timer_callback() {
        if (!shm_) {
            shm_ = init_shared_memory(false);
            if (!shm_) return;
        }

        pthread_mutex_lock(&shm_->mutex);

        // Heartbeat: Let HAL know the bridge (controller interface) is alive
        shm_->watchdog_counter++;

        // Publish IMU
        auto imu_msg = sensor_msgs::msg::Imu();
        imu_msg.header.stamp = this->now();
        imu_msg.header.frame_id = "imu_link";
        imu_msg.orientation.x = shm_->imu.orientation[0];
        imu_msg.orientation.y = shm_->imu.orientation[1];
        imu_msg.orientation.z = shm_->imu.orientation[2];
        imu_msg.orientation.w = shm_->imu.orientation[3];
        imu_msg.angular_velocity.x = shm_->imu.angular_velocity[0];
        imu_msg.angular_velocity.y = shm_->imu.angular_velocity[1];
        imu_msg.angular_velocity.z = shm_->imu.angular_velocity[2];
        imu_msg.linear_acceleration.x = shm_->imu.linear_acceleration[0];
        imu_msg.linear_acceleration.y = shm_->imu.linear_acceleration[1];
        imu_msg.linear_acceleration.z = shm_->imu.linear_acceleration[2];
        imu_pub_->publish(imu_msg);

        // Publish Joint States
        joint_msg_.header.stamp = imu_msg.header.stamp;
        for (int i = 0; i < NUM_JOINTS; ++i) {
            joint_msg_.position[i] = shm_->joint_state.position[i];
            joint_msg_.velocity[i] = shm_->joint_state.velocity[i];
            joint_msg_.effort[i] = shm_->joint_state.effort[i];
        }
        joint_pub_->publish(joint_msg_);

        // Publish Pose
        auto pose_msg = geometry_msgs::msg::PoseStamped();
        pose_msg.header.stamp = this->now();
        pose_msg.header.frame_id = "odom";
        pose_msg.pose.position.x = shm_->pose.position[0];
        pose_msg.pose.position.y = shm_->pose.position[1];
        pose_msg.pose.position.z = shm_->pose.position[2];
        pose_msg.pose.orientation.x = shm_->pose.orientation[0];
        pose_msg.pose.orientation.y = shm_->pose.orientation[1];
        pose_msg.pose.orientation.z = shm_->pose.orientation[2];
        pose_msg.pose.orientation.w = shm_->pose.orientation[3];
        pose_pub_->publish(pose_msg);

        // Publish Health
        auto health_msg = std_msgs::msg::String();
        health_msg.data = shm_->stop ? "STOPPED" : "OK";
        health_pub_->publish(health_msg);

        pthread_mutex_unlock(&shm_->mutex);
    }

    void estop_reset_callback(const std_msgs::msg::Bool::SharedPtr msg) {
        if (shm_ && msg->data) {
            pthread_mutex_lock(&shm_->mutex);
            shm_->estop_active = false;
            pthread_mutex_unlock(&shm_->mutex);
            RCLCPP_INFO(this->get_logger(), "E-STOP Reset triggered via ROS 2!");
        }
    }

    void estop_callback(const std_msgs::msg::Bool::SharedPtr msg) {
        if (shm_ && msg->data) {
            pthread_mutex_lock(&shm_->mutex);
            shm_->estop_active = true;
            pthread_mutex_unlock(&shm_->mutex);
            RCLCPP_WARN(this->get_logger(), "E-STOP triggered via ROS 2!");
        }
    }

    void estop_reset_srv_callback(
        const std_srvs::srv::Trigger::Request::SharedPtr /*request*/,
        std_srvs::srv::Trigger::Response::SharedPtr response)
    {
        if (!shm_) {
            response->success = false;
            response->message = "Shared memory not attached";
            return;
        }
        pthread_mutex_lock(&shm_->mutex);
        shm_->estop_active = false;
        shm_->imu_counter  = 0;
        shm_->pose_counter = 0;
        pthread_mutex_unlock(&shm_->mutex);
        RCLCPP_INFO(this->get_logger(), "E-STOP reset via /estop_reset service");
        response->success = true;
        response->message = "E-Stop cleared; counters reset";
    }

    RobotSharedData* shm_;
    rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_pub_;
    rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_pub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr pose_pub_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr health_pub_;
    rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr estop_sub_;
    rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr estop_reset_sub_;
    rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr estop_reset_srv_;
    rclcpp::TimerBase::SharedPtr timer_;
    sensor_msgs::msg::JointState joint_msg_;
};

int main(int argc, char* argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<RobotRTBridge>());
    rclcpp::shutdown();
    return 0;
}
