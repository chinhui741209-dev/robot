#!/usr/bin/env python3
"""
Bringup launch file for HAL Buddy
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    robot_name = DeclareLaunchArgument(
        "robot", default_value="buddy", description="Robot name (buddy or omni)"
    )

    sim_mode = DeclareLaunchArgument(
        "sim", default_value="true", description="Simulation mode"
    )

    hal_node = ExecuteProcess(
        cmd=["python3", "/home/nvidia/poc/poc-orin/hal/scripts/hal_buddy_node.py"],
        output="screen",
    )

    return LaunchDescription([robot_name, sim_mode, hal_node])
