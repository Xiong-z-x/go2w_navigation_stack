from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.conditions import UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node


def generate_launch_description():
    headless = LaunchConfiguration("headless")
    use_gpu = LaunchConfiguration("use_gpu")
    world_name = LaunchConfiguration("world_name")

    navigation_share = Path(get_package_share_directory("go2w_navigation")).resolve()
    perception_share = Path(get_package_share_directory("go2w_perception")).resolve()
    sim_share = Path(get_package_share_directory("go2w_sim")).resolve()
    description_share = Path(get_package_share_directory("go2w_description")).resolve()
    repo_root = navigation_share.parents[3]
    fastlio_setup = repo_root / ".go2w_external" / "workspaces" / "fast_lio_ros2" / "install" / "setup.bash"

    sim_launch = str(sim_share / "launch" / "sim_go2w_real.launch.py")
    perception_launch = str(perception_share / "launch" / "phase2f_tf_authority.launch.py")
    nav_launch = str(navigation_share / "launch" / "phase3a_nav2_same_floor.launch.py")
    hospital_world = str(sim_share / "worlds" / "phase3c_hospital_multifloor_world.sdf")
    fastlio_params = str(perception_share / "config" / "phase2d_fastlio_sim.yaml")
    nav2_params = str(navigation_share / "config" / "phase5_real_model_nav2_same_floor.yaml")
    rviz_config = str(description_share / "rviz" / "go2w_real_hospital_nav.rviz")
    rviz_gpu_env = {
        "LIBGL_ALWAYS_SOFTWARE": "0",
        "MESA_D3D12_DEFAULT_ADAPTER_NAME": "NVIDIA",
        "MESA_GL_VERSION_OVERRIDE": "4.2",
        "MESA_GLSL_VERSION_OVERRIDE": "420",
    }

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sim_launch),
        launch_arguments={
            "use_gpu": use_gpu,
            "headless": headless,
            "launch_rviz": "false",
            "world": hospital_world,
            "world_name": world_name,
        }.items(),
    )
    perception = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(perception_launch),
    )
    fastlio = ExecuteProcess(
        cmd=[
            "bash",
            "-lc",
            (
                f"source {fastlio_setup} && "
                "exec ros2 run fast_lio fastlio_mapping --ros-args "
                f"--params-file {fastlio_params}"
            ),
        ],
        shell=False,
        output="screen",
    )
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav_launch),
        launch_arguments={
            "params_file": nav2_params,
        }.items(),
    )
    rviz_goal_bridge = Node(
        package="go2w_navigation",
        executable="go2w_rviz_goal_bridge",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[{"use_sim_time": True}],
        additional_env=rviz_gpu_env,
        condition=UnlessCondition(headless),
    )

    return LaunchDescription([
        DeclareLaunchArgument("headless", default_value="false"),
        DeclareLaunchArgument("use_gpu", default_value="false"),
        DeclareLaunchArgument(
            "world_name",
            default_value="go2w_phase3c_hospital_multifloor_world",
        ),
        sim,
        TimerAction(period=3.0, actions=[perception]),
        TimerAction(period=6.0, actions=[fastlio]),
        TimerAction(period=12.0, actions=[nav2]),
        TimerAction(period=15.0, actions=[rviz_goal_bridge]),
        TimerAction(period=16.0, actions=[rviz]),
    ])
