from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    phase2e_launch = PathJoinSubstitution([
        FindPackageShare("go2w_perception"),
        "launch",
        "phase2e_fastlio_contract.launch.py",
    ])
    tf_config = PathJoinSubstitution([
        FindPackageShare("go2w_perception"),
        "config",
        "phase2f_tf_authority.yaml",
    ])

    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(phase2e_launch)),
        Node(
            package="go2w_perception",
            executable="go2w_fastlio_tf_authority",
            name="go2w_fastlio_tf_authority",
            output="screen",
            parameters=[tf_config],
        ),
    ])
