#!/usr/bin/env python3
from launch import LaunchService
from launch_ros import RosLaunchServer
from launch.actions import ExecuteProcess

cmd = ["python3", "/home/nvidia/poc/poc-orin/hal/scripts/hal_buddy_node.py"]

launch_service = LaunchService()
launch_service.include_launch_description(RosLaunchServer())

process = ExecuteProcess(cmd=cmd, shell=False)
launch_service.add_action(process)

launch_service.run()
