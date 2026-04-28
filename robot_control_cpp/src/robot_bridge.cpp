#include "robot_control_cpp/robot_bridge.hpp"
#include <chrono>

using namespace std::chrono_literals;

namespace robot_control_cpp {

RobotBridge::RobotBridge(const rclcpp::NodeOptions & options)
: Node("robot_bridge_cpp", options) {
    
    joint_names_ = {"shoulder", "elbow", "wrist", "gripper"};
    for (const auto & name : joint_names_) {
        motor_positions_[name] = 0.0;
    }

    // ICD Sub: Control Target
    target_sub_ = this->create_subscription<std_msgs::msg::Float32MultiArray>(
        "/control/target", 10,
        std::bind(&RobotBridge::target_callback, this, std::placeholders::_1)
    );

    // ICD Pub: Joint States
    joint_state_pub_ = this->create_publisher<sensor_msgs::msg::JointState>("/joint_states", 10);
    state_pub_ = this->create_publisher<std_msgs::msg::String>("/control/state", 10);

    // High-frequency State Publisher (100Hz for POC, can be 1kHz)
    timer_ = this->create_wall_timer(10ms, std::bind(&RobotBridge::publish_timer_callback, this));

    RCLCPP_INFO(this->get_logger(), "🚀 C++ Robot Bridge (D3) Started - High Frequency Control Ready");
}

void RobotBridge::target_callback(const std_msgs::msg::Float32MultiArray::SharedPtr msg) {
    if (msg->data.size() >= 4) {
        motor_positions_["shoulder"] = msg->data[0];
        motor_positions_["elbow"] = msg->data[1];
        motor_positions_["wrist"] = msg->data[2];
        motor_positions_["gripper"] = msg->data[3];

        // Unitree SDK Parameter Calculation Simulation
        double kp_rotor = kp_output_desired / (gear_ratio * gear_ratio);
        double kd_rotor = kd_output_desired / (gear_ratio * gear_ratio);
        
        RCLCPP_DEBUG(this->get_logger(), "[Unitree Sim] Target received. Kp_r: %.3f", kp_rotor);
    }
}

void RobotBridge::publish_timer_callback() {
    auto msg = sensor_msgs::msg::JointState();
    msg.header.stamp = this->get_clock()->now();
    
    for (const auto & name : joint_names_) {
        msg.name.push_back(name);
        msg.position.push_back(motor_positions_[name]);
    }
    
    joint_state_pub_->publish(msg);
}

} // namespace robot_control_cpp
