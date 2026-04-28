#ifndef ROBOT_CONTROL_CPP__ROBOT_BRIDGE_HPP_
#define ROBOT_CONTROL_CPP__ROBOT_BRIDGE_HPP_

#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_msgs/msg/float32_multi_array.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <vector>
#include <string>
#include <map>

namespace robot_control_cpp {

class RobotBridge : public rclcpp::Node {
public:
    explicit RobotBridge(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
    // Callbacks
    void target_callback(const std_msgs::msg::Float32MultiArray::SharedPtr msg);
    void publish_timer_callback();

    // ROS 2 Interfaces
    rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr target_sub_;
    rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_state_pub_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr state_pub_;
    rclcpp::TimerBase::SharedPtr timer_;

    // Internal State
    std::vector<std::string> joint_names_;
    std::map<std::string, double> motor_positions_;
    
    // Unitree SDK Simulation Params
    const double gear_ratio = 6.33;
    const double kp_output_desired = 60.0;
    const double kd_output_desired = 1.5;
};

} // namespace robot_control_cpp

#endif // ROBOT_CONTROL_CPP__ROBOT_BRIDGE_HPP_
