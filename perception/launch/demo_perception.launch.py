#!/usr/bin/env python3
"""
Demo Perception Launch - Camera + Detection + Visualization
"""

from launch import LaunchService
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
import sys


def generate_launch_description():
    return []


if __name__ == "__main__":
    print("Starting Demo Perception Pipeline...")
    print("Use individual nodes for now:")
    print("  Terminal 1: python3 perception/scripts/camera_node.py")
    print("  Terminal 2: python3 perception/scripts/perception_node.py")
    print(
        "  Terminal 3: ros2 run image_view image_view --ros-args -r image:=/camera/image_raw"
    )
