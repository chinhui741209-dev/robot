cmake_minimum_required(VERSION 3.8)
project(robot_control_cpp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)

# Include directories
include_directories(include)

# Create the library/node executable
add_executable(robot_bridge_cpp
  src/robot_bridge.cpp
  src/main.cpp
)

# Target dependencies
target_link_libraries(robot_bridge_cpp
  ${rclcpp_LIBRARIES}
  ${std_msgs_LIBRARIES}
  ${sensor_msgs_LIBRARIES}
)

# Define include directories for the target
target_include_directories(robot_bridge_cpp PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

# Install rules
install(TARGETS
  robot_bridge_cpp
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
