#include "robot_control_cpp/robot_bridge.hpp"
#include <rclcpp/rclcpp.hpp>
#include <memory>

int main(int argc, char ** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<robot_control_cpp::RobotBridge>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
