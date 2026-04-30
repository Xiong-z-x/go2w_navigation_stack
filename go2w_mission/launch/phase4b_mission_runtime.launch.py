# Copyright 2026 Xiong-z-x
# SPDX-License-Identifier: Proprietary

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    route_params_file = LaunchConfiguration("route_params_file")
    graph_file = LaunchConfiguration("graph_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    log_level = LaunchConfiguration("log_level")

    default_route_params_file = PathJoinSubstitution([
        FindPackageShare("go2w_navigation"),
        "config",
        "phase3c_multifloor_route_server.yaml",
    ])
    default_graph_file = PathJoinSubstitution([
        FindPackageShare("go2w_navigation"),
        "graphs",
        "phase3c_hospital_multifloor_route.geojson",
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            "route_params_file",
            default_value=default_route_params_file,
            description="Phase 4B-min route server parameters.",
        ),
        DeclareLaunchArgument(
            "graph_file",
            default_value=default_graph_file,
            description="Phase 4B-min manual multi-floor route graph.",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="false",
            description="Use simulation time for Phase 4B-min handoff nodes.",
        ),
        DeclareLaunchArgument(
            "autostart",
            default_value="true",
            description="Automatically configure and activate route_server.",
        ),
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="ROS log level for Phase 4B-min nodes.",
        ),
        Node(
            package="nav2_route",
            executable="route_server",
            name="route_server",
            output="screen",
            parameters=[
                route_params_file,
                {
                    "use_sim_time": use_sim_time,
                    "graph_filepath": graph_file,
                },
            ],
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_phase4b_route",
            output="screen",
            parameters=[
                {"use_sim_time": use_sim_time},
                {"autostart": autostart},
                {"node_names": ["route_server"]},
            ],
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="go2w_control",
            executable="go2w_command_gate",
            name="go2w_command_gate",
            output="screen",
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="go2w_control",
            executable="go2w_stair_executor",
            name="go2w_stair_executor",
            output="screen",
            arguments=["--ros-args", "--log-level", log_level],
        ),
    ])
