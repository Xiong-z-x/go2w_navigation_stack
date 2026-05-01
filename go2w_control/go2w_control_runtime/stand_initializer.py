from __future__ import annotations

import argparse
import time

from std_msgs.msg import Float64MultiArray

from go2w_control_runtime.motion_profiles import get_go2w_motion_profiles


def build_stand_command() -> Float64MultiArray:
    profiles = get_go2w_motion_profiles()
    msg = Float64MultiArray()
    msg.data = list(profiles.legged.stand_pose)
    return msg


def main() -> None:
    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--leg-command-topic",
        default="/leg_position_controller/commands",
    )
    parser.add_argument("--duration-sec", type=float, default=2.0)
    parser.add_argument("--rate-hz", type=float, default=20.0)
    args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)

    class StandInitializerNode(Node):
        def __init__(self) -> None:
            super().__init__("go2w_stand_initializer")
            self._stand_pub = self.create_publisher(
                Float64MultiArray,
                args.leg_command_topic,
                10,
            )

        def publish_stand_pose(self) -> None:
            duration_sec = max(0.1, float(args.duration_sec))
            rate_hz = max(1.0, float(args.rate_hz))
            interval_sec = 1.0 / rate_hz
            end_time = time.monotonic() + duration_sec
            command = build_stand_command()

            while rclpy.ok() and time.monotonic() < end_time:
                self._stand_pub.publish(command)
                rclpy.spin_once(self, timeout_sec=0.0)
                time.sleep(interval_sec)

            self.get_logger().info(
                "go2w_stand_initializer_result: PASS "
                f"topic={args.leg_command_topic} "
                f"commands={len(command.data)}"
            )

    node = StandInitializerNode()
    try:
        node.publish_stand_pose()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

