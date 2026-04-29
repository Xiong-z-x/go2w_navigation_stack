from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config = PathJoinSubstitution([
        FindPackageShare("go2w_perception"),
        "config",
        "phase2e_fastlio_contract.yaml",
    ])

    return LaunchDescription([
        Node(
            package="go2w_perception",
            executable="go2w_fastlio_input_adapter",
            name="go2w_fastlio_input_adapter",
            output="screen",
            parameters=[config],
        ),
        Node(
            package="go2w_perception",
            executable="go2w_fastlio_output_adapter",
            name="go2w_fastlio_output_adapter",
            output="screen",
            parameters=[config],
        ),
    ])
