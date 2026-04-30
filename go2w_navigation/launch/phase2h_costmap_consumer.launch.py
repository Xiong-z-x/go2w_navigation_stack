# Copyright 2026 Xiong-z-x
# SPDX-License-Identifier: Proprietary

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    log_level = LaunchConfiguration("log_level")

    default_params_file = PathJoinSubstitution([
        FindPackageShare("go2w_navigation"),
        "config",
        "phase2h_costmap_consumer.yaml",
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            "params_file",
            default_value=default_params_file,
            description="Phase 2H standalone Nav2 costmap parameters.",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation clock for the costmap consumer.",
        ),
        DeclareLaunchArgument(
            "autostart",
            default_value="true",
            description="Automatically configure and activate the costmap lifecycle node.",
        ),
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="ROS log level for Phase 2H costmap nodes.",
        ),
        Node(
            package="nav2_costmap_2d",
            executable="nav2_costmap_2d",
            output="screen",
            parameters=[params_file, {"use_sim_time": use_sim_time}],
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_phase2_costmap",
            output="screen",
            parameters=[
                {"use_sim_time": use_sim_time},
                {"autostart": autostart},
                {"node_names": ["costmap/costmap"]},
            ],
            arguments=["--ros-args", "--log-level", log_level],
        ),
    ])
