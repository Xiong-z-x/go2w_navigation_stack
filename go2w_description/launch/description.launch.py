import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def load_robot_description(controllers_yaml_path: str) -> str:
    pkg_share = get_package_share_directory('go2w_description')
    urdf_path = os.path.join(pkg_share, 'urdf', 'go2w_placeholder.urdf')

    with open(urdf_path, 'r', encoding='utf-8') as urdf_file:
        robot_description = urdf_file.read()

    if controllers_yaml_path:
        robot_description = robot_description.replace(
            '__GO2W_CONTROLLERS_YAML__',
            controllers_yaml_path,
        )

    return robot_description


def launch_setup(context, *args, **kwargs):
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context)
    controllers_yaml = LaunchConfiguration('controllers_yaml').perform(context)
    robot_description = load_robot_description(controllers_yaml)

    return [Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time == 'true',
            'robot_description': robot_description,
        }],
    )]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('controllers_yaml', default_value=''),
        OpaqueFunction(function=launch_setup),
    ])
