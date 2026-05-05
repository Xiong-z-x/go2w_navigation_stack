# Copyright 2026 Xiong-z-x
# SPDX-License-Identifier: Proprietary

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    route_params_file = LaunchConfiguration("route_params_file")
    graph_file = LaunchConfiguration("graph_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    log_level = LaunchConfiguration("log_level")
    launch_flat_nav_executor = LaunchConfiguration("launch_flat_nav_executor")
    launch_stair_executor = LaunchConfiguration("launch_stair_executor")
    flat_nav_mode = LaunchConfiguration("flat_nav_mode")
    mission_action_name = LaunchConfiguration("mission_action_name")
    mission_state_file = LaunchConfiguration("mission_state_file")
    mission_orchestrator_state_file = LaunchConfiguration(
        "mission_orchestrator_state_file"
    )
    mission_queue_replay_state_file = LaunchConfiguration(
        "mission_queue_replay_state_file"
    )
    mission_task_history_file = LaunchConfiguration("mission_task_history_file")
    mission_task_history_retention_limit = LaunchConfiguration(
        "mission_task_history_retention_limit"
    )
    mission_retry_limit = LaunchConfiguration("mission_retry_limit")
    mission_retry_backoff_sec = LaunchConfiguration("mission_retry_backoff_sec")
    mission_recovery_enabled = LaunchConfiguration("mission_recovery_enabled")
    flat_behavior_tree = LaunchConfiguration("flat_behavior_tree")
    mission_queue_capacity = LaunchConfiguration("mission_queue_capacity")
    mission_robot_id = LaunchConfiguration("mission_robot_id")
    mission_control_service_name = LaunchConfiguration("mission_control_service_name")

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
            description="Use simulation time for mission API launch nodes.",
        ),
        DeclareLaunchArgument(
            "autostart",
            default_value="true",
            description="Automatically configure and activate route_server.",
        ),
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="ROS log level for mission API launch nodes.",
        ),
        DeclareLaunchArgument(
            "launch_flat_nav_executor",
            default_value="true",
            description="Launch the Phase 4C-min flat navigation verifier action server.",
        ),
        DeclareLaunchArgument(
            "launch_stair_executor",
            default_value="true",
            description="Launch the staircase executor action server.",
        ),
        DeclareLaunchArgument(
            "flat_nav_mode",
            default_value="success",
            description="Default mode for the Phase 4C-min flat navigation verifier.",
        ),
        DeclareLaunchArgument(
            "mission_action_name",
            default_value="/go2w/mission/run",
            description="Mission API Action name.",
        ),
        DeclareLaunchArgument(
            "mission_state_file",
            default_value="",
            description="Optional persistent mission state file path.",
        ),
        DeclareLaunchArgument(
            "mission_orchestrator_state_file",
            default_value="",
            description="Optional persistent mission orchestrator state file path.",
        ),
        DeclareLaunchArgument(
            "mission_queue_replay_state_file",
            default_value="",
            description="Optional persistent mission queue replay state file path.",
        ),
        DeclareLaunchArgument(
            "mission_task_history_file",
            default_value="",
            description="Optional persistent mission task history state file path.",
        ),
        DeclareLaunchArgument(
            "mission_task_history_retention_limit",
            default_value="50",
            description="Retention limit for terminal mission history records.",
        ),
        DeclareLaunchArgument(
            "mission_retry_limit",
            default_value="2",
            description="Retry budget for transient mission execution failures.",
        ),
        DeclareLaunchArgument(
            "mission_retry_backoff_sec",
            default_value="0.5",
            description="Backoff between transient mission retries.",
        ),
        DeclareLaunchArgument(
            "mission_recovery_enabled",
            default_value="true",
            description="Enable checkpoint resume and transient recovery.",
        ),
        DeclareLaunchArgument(
            "flat_behavior_tree",
            default_value="success",
            description=(
                "Behavior tree string sent with mission flat NavigateToPose goals. "
                "Use __empty__ when binding the mission API to a real Nav2 "
                "BT Navigator instead of the Phase 4C verifier action server."
            ),
        ),
        DeclareLaunchArgument(
            "mission_queue_capacity",
            default_value="2",
            description="Bounded outstanding mission capacity for RunMission.",
        ),
        DeclareLaunchArgument(
            "mission_robot_id",
            default_value="go2w_local",
            description="Local robot id accepted by RunMission assignment policy.",
        ),
        DeclareLaunchArgument(
            "mission_control_service_name",
            default_value="/go2w/mission/control",
            description="Mission control service name for pause/resume/status.",
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
            condition=IfCondition(launch_stair_executor),
            arguments=["--ros-args", "--log-level", log_level],
        ),
        Node(
            package="go2w_navigation",
            executable="go2w_flat_nav_executor",
            name="go2w_flat_nav_executor",
            output="screen",
            condition=IfCondition(launch_flat_nav_executor),
            arguments=[
                "--mode",
                flat_nav_mode,
                "--ros-args",
                "--log-level",
                log_level,
            ],
        ),
        Node(
            package="go2w_mission",
            executable="go2w_mission_api",
            name="go2w_mission_api",
            output="screen",
            arguments=[
                "--graph-file",
                graph_file,
                "--compute-route-action",
                "/compute_route",
                "--flat-nav-action",
                "/navigate_to_pose",
                "--stair-exec-action",
                "/stair_exec",
                "--mission-state-file",
                mission_state_file,
                "--mission-orchestrator-state-file",
                mission_orchestrator_state_file,
                "--mission-queue-replay-state-file",
                mission_queue_replay_state_file,
                "--mission-task-history-file",
                mission_task_history_file,
                "--mission-task-history-retention-limit",
                mission_task_history_retention_limit,
                "--mission-retry-limit",
                mission_retry_limit,
                "--mission-retry-backoff-sec",
                mission_retry_backoff_sec,
                "--mission-recovery-enabled",
                mission_recovery_enabled,
                "--flat-behavior-tree",
                flat_behavior_tree,
                "--mission-queue-capacity",
                mission_queue_capacity,
                "--mission-robot-id",
                mission_robot_id,
                "--mission-control-service-name",
                mission_control_service_name,
                "--action-name",
                mission_action_name,
                "--ros-args",
                "--log-level",
                log_level,
            ],
        ),
    ])
