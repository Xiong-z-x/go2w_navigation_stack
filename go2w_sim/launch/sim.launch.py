import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def sanitize_path_entries(env_value: str, install_root: str) -> str:
    home = os.path.expanduser('~')
    kept = []
    for entry in env_value.split(os.pathsep):
        if not entry:
            continue
        normalized = os.path.normpath(entry)
        if normalized.startswith(install_root) or normalized.startswith('/opt/ros/humble'):
            kept.append(entry)
            continue
        if normalized.startswith(home) and '/install/' in normalized:
            continue
        kept.append(entry)
    return os.pathsep.join(dict.fromkeys(kept))


def generate_launch_description():
    sim_share = get_package_share_directory('go2w_sim')
    description_share = get_package_share_directory('go2w_description')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')

    sim_prefix = Path(sim_share).resolve().parents[1]
    install_root = str(sim_prefix.parent)
    use_gpu = LaunchConfiguration('use_gpu')
    headless = LaunchConfiguration('headless')
    launch_rviz = LaunchConfiguration('launch_rviz')
    world_path = os.path.join(sim_share, 'worlds', 'empty_world.sdf')
    rviz_config = os.path.join(description_share, 'rviz', 'go2w_phase1.rviz')
    description_launch = os.path.join(description_share, 'launch', 'description.launch.py')
    gz_launch = os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
    controller_yaml_path = os.path.join(sim_share, 'config', 'controllers.yaml')

    sanitized_ament_prefix_path = sanitize_path_entries(os.environ.get('AMENT_PREFIX_PATH', ''), install_root)
    sanitized_cmake_prefix_path = sanitize_path_entries(os.environ.get('CMAKE_PREFIX_PATH', ''), install_root)
    sanitized_colcon_prefix_path = sanitize_path_entries(os.environ.get('COLCON_PREFIX_PATH', ''), install_root)
    sanitized_ld_library_path = sanitize_path_entries(os.environ.get('LD_LIBRARY_PATH', ''), install_root)
    sanitized_pythonpath = sanitize_path_entries(os.environ.get('PYTHONPATH', ''), install_root)
    sanitized_path = sanitize_path_entries(os.environ.get('PATH', ''), install_root)

    robot_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(description_launch),
        launch_arguments={
            'use_sim_time': 'true',
            'controllers_yaml': controller_yaml_path,
        }.items(),
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch),
        launch_arguments={
            'gz_args': PythonExpression([
                f"'-r -s --headless-rendering {world_path}' if '",
                headless,
                "' == 'true' else '-r ",
                world_path,
                "'",
            ]),
            'gz_version': '6',
            'on_exit_shutdown': 'true',
        }.items(),
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
    )

    sensor_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/lidar/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
        ],
        remappings=[
            ('/lidar/points', '/lidar_points'),
        ],
    )

    lidar_sensor_frame_alias = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        output='screen',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', '0',
            '--frame-id', 'lidar_link',
            '--child-frame-id', 'go2w_placeholder/base_footprint/lidar_sensor',
        ],
    )

    imu_sensor_frame_alias = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        output='screen',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', '0',
            '--frame-id', 'imu_link',
            '--child-frame-id', 'go2w_placeholder/base_footprint/imu_sensor',
        ],
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-world', 'go2w_empty_world',
            '-topic', 'robot_description',
            '-name', 'go2w_placeholder',
            '-z', '0.15',
        ],
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager', '/controller_manager',
            '--controller-manager-timeout', '120',
        ],
    )

    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=[
            'diff_drive_controller',
            '--controller-manager', '/controller_manager',
            '--controller-manager-timeout', '120',
            '--param-file', controller_yaml_path,
        ],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_gpu', default_value='false'),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('launch_rviz', default_value='true'),
        SetEnvironmentVariable('AMENT_PREFIX_PATH', sanitized_ament_prefix_path),
        SetEnvironmentVariable('CMAKE_PREFIX_PATH', sanitized_cmake_prefix_path),
        SetEnvironmentVariable('COLCON_PREFIX_PATH', sanitized_colcon_prefix_path),
        SetEnvironmentVariable('LD_LIBRARY_PATH', sanitized_ld_library_path),
        SetEnvironmentVariable('PYTHONPATH', sanitized_pythonpath),
        SetEnvironmentVariable('PATH', sanitized_path),
        SetEnvironmentVariable('GZ_SIM_SYSTEM_PLUGIN_PATH', '/opt/ros/humble/lib'),
        SetEnvironmentVariable('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', '/opt/ros/humble/lib'),
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '0', condition=IfCondition(use_gpu)),
        SetEnvironmentVariable('MESA_D3D12_DEFAULT_ADAPTER_NAME', 'NVIDIA', condition=IfCondition(use_gpu)),
        SetEnvironmentVariable('MESA_GL_VERSION_OVERRIDE', '4.2', condition=IfCondition(use_gpu)),
        SetEnvironmentVariable('MESA_GLSL_VERSION_OVERRIDE', '420', condition=IfCondition(use_gpu)),
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1', condition=UnlessCondition(use_gpu)),
        SetEnvironmentVariable('MESA_GL_VERSION_OVERRIDE', '3.3', condition=UnlessCondition(use_gpu)),
        SetEnvironmentVariable('MESA_GLSL_VERSION_OVERRIDE', '330', condition=UnlessCondition(use_gpu)),
        clock_bridge,
        sensor_bridge,
        robot_description,
        lidar_sensor_frame_alias,
        imu_sensor_frame_alias,
        gazebo,
        TimerAction(period=3.0, actions=[spawn_robot]),
        RegisterEventHandler(
            OnProcessExit(
                target_action=spawn_robot,
                on_exit=[joint_state_broadcaster_spawner],
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[diff_drive_controller_spawner],
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=diff_drive_controller_spawner,
                on_exit=[rviz],
            )
        ),
    ])
