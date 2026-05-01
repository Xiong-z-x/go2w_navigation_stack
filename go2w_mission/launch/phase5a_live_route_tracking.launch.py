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
    log_level = LaunchConfiguration("log_level")
    trajectory_node_ids = LaunchConfiguration("trajectory_node_ids")
    sample_hold_sec = LaunchConfiguration("sample_hold_sec")
    result_timeout_sec = LaunchConfiguration("result_timeout_sec")

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
            description="Phase 5A route server parameters.",
        ),
        DeclareLaunchArgument(
            "graph_file",
            default_value=default_graph_file,
            description="Phase 5A manual multi-floor route graph.",
        ),
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="ROS log level for Phase 5A nodes.",
        ),
        DeclareLaunchArgument(
            "trajectory_node_ids",
            default_value="100,101,102,200,201,202",
            description="Node IDs used by the live TF trajectory fixture.",
        ),
        DeclareLaunchArgument(
            "sample_hold_sec",
            default_value="0.35",
            description="How long to hold each TF sample while the route tracker samples pose.",
        ),
        DeclareLaunchArgument(
            "result_timeout_sec",
            default_value="30.0",
            description="Maximum runtime for the live route tracking probe.",
        ),
        Node(
            package="nav2_route",
            executable="route_server",
            name="route_server",
            output="screen",
            parameters=[
                route_params_file,
                {
                    "use_sim_time": False,
                    "graph_filepath": graph_file,
                    "operations": ["AdjustSpeedLimit"],
                    "AdjustSpeedLimit.plugin": "nav2_route::AdjustSpeedLimit",
                },
            ],
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_phase5a_route",
            output="screen",
            parameters=[
                {"use_sim_time": False},
                {"autostart": True},
                {"node_names": ["route_server"]},
            ],
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="go2w_mission",
            executable="go2w_phase5a_live_route_tracking",
            name="go2w_phase5a_live_route_tracking",
            output="screen",
            arguments=[
                "--graph-file",
                graph_file,
                "--trajectory-node-ids",
                trajectory_node_ids,
                "--sample-hold-sec",
                sample_hold_sec,
                "--result-timeout-sec",
                result_timeout_sec,
                "--ros-args",
                "--log-level",
                log_level,
            ],
        ),
    ])
