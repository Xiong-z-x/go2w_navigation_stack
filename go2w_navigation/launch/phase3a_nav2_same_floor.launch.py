# Copyright 2026 Xiong-z-x
# SPDX-License-Identifier: Proprietary

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params_file = LaunchConfiguration("params_file")
    bt_xml = LaunchConfiguration("bt_xml")
    bt_through_poses_xml = LaunchConfiguration("bt_through_poses_xml")
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    log_level = LaunchConfiguration("log_level")

    default_params_file = PathJoinSubstitution([
        FindPackageShare("go2w_navigation"),
        "config",
        "phase3a_nav2_same_floor.yaml",
    ])
    default_bt_xml = PathJoinSubstitution([
        FindPackageShare("go2w_navigation"),
        "behavior_trees",
        "phase3a_navigate_to_pose.xml",
    ])
    default_bt_through_poses_xml = PathJoinSubstitution([
        FindPackageShare("go2w_navigation"),
        "behavior_trees",
        "phase3a_navigate_through_poses.xml",
    ])

    common_parameters = [params_file, {"use_sim_time": use_sim_time}]
    bt_parameters = [
        params_file,
        {
            "use_sim_time": use_sim_time,
            "default_nav_to_pose_bt_xml": bt_xml,
            "default_nav_through_poses_bt_xml": bt_through_poses_xml,
        },
    ]

    return LaunchDescription([
        DeclareLaunchArgument(
            "params_file",
            default_value=default_params_file,
            description="Phase 3A minimal same-floor Nav2 parameters.",
        ),
        DeclareLaunchArgument(
            "bt_xml",
            default_value=default_bt_xml,
            description="Phase 3A minimal NavigateToPose behavior tree.",
        ),
        DeclareLaunchArgument(
            "bt_through_poses_xml",
            default_value=default_bt_through_poses_xml,
            description="Phase 3A minimal NavigateThroughPoses behavior tree.",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation time for Nav2.",
        ),
        DeclareLaunchArgument(
            "autostart",
            default_value="true",
            description="Automatically configure and activate Nav2 lifecycle nodes.",
        ),
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="ROS log level for Phase 3A Nav2 nodes.",
        ),
        Node(
            package="nav2_controller",
            executable="controller_server",
            name="controller_server",
            output="screen",
            parameters=common_parameters,
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="nav2_planner",
            executable="planner_server",
            name="planner_server",
            output="screen",
            parameters=common_parameters,
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="nav2_bt_navigator",
            executable="bt_navigator",
            name="bt_navigator",
            output="screen",
            parameters=bt_parameters,
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_phase3a_navigation",
            output="screen",
            parameters=[
                {"use_sim_time": use_sim_time},
                {"autostart": autostart},
                {"node_names": ["controller_server", "planner_server", "bt_navigator"]},
            ],
            arguments=["--ros-args", "--log-level", log_level],
        ),
    ])
