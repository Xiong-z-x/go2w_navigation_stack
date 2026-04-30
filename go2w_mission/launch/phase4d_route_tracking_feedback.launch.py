# Copyright 2026 Xiong-z-x
# SPDX-License-Identifier: Proprietary

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    log_level = LaunchConfiguration("log_level")
    drop_operation = LaunchConfiguration("drop_operation")

    return LaunchDescription([
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="ROS log level for Phase 4D-min nodes.",
        ),
        DeclareLaunchArgument(
            "drop_operation",
            default_value="false",
            description="When true, omit the stair_exec route operation feedback.",
        ),
        Node(
            package="go2w_navigation",
            executable="go2w_route_tracking_feedback_executor",
            name="go2w_route_tracking_feedback_executor",
            output="screen",
            arguments=[
                "--drop-operation",
                drop_operation,
                "--ros-args",
                "--log-level",
                log_level,
            ],
        ),
    ])
