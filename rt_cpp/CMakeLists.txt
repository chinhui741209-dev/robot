cmake_minimum_required(VERSION 3.8)
project(robot_rt_cpp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(Threads REQUIRED)
find_package(std_srvs REQUIRED)

include_directories(include)

# Standalone RT binaries
add_executable(hal_buddy src/hal_buddy.cpp)
target_link_libraries(hal_buddy PRIVATE Threads::Threads)
if(NOT APPLE)
    target_link_libraries(hal_buddy PRIVATE rt)
endif()

add_executable(state_estimator src/state_estimator.cpp)
target_link_libraries(state_estimator PRIVATE Threads::Threads)
if(NOT APPLE)
    target_link_libraries(state_estimator PRIVATE rt)
endif()

# ROS 2 Bridge
add_executable(ros2_bridge src/ros2_bridge.cpp)
ament_target_dependencies(ros2_bridge
  rclcpp
  sensor_msgs
  geometry_msgs
  std_msgs
  std_srvs
  nav_msgs
)
target_link_libraries(ros2_bridge PRIVATE Threads::Threads)
if(NOT APPLE)
    target_link_libraries(ros2_bridge PRIVATE rt)
endif()

# Unit Tests
add_executable(test_shm_logic src/test_shm_logic.cpp)
target_link_libraries(test_shm_logic PRIVATE Threads::Threads)
if(NOT APPLE)
    target_link_libraries(test_shm_logic PRIVATE rt)
endif()

add_executable(test_safety_logic src/test_safety_logic.cpp)
target_link_libraries(test_safety_logic PRIVATE Threads::Threads)
if(NOT APPLE)
    target_link_libraries(test_safety_logic PRIVATE rt)
endif()

add_executable(benchmark_rt src/benchmark_rt.cpp)
target_link_libraries(benchmark_rt PRIVATE Threads::Threads)
if(NOT APPLE)
    target_link_libraries(benchmark_rt PRIVATE rt)
endif()

install(TARGETS
  hal_buddy
  hal_quadruped_mock
  state_estimator
  ros2_bridge
  test_shm_logic
  test_safety_logic
  benchmark_rt
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
t PRIVATE rt)
endif()

install(TARGETS
  hal_buddy
  state_estimator
  ros2_bridge
  test_shm_logic
  test_safety_logic
  benchmark_rt
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
