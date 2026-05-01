from __future__ import annotations

import argparse
import time

from go2w_control_runtime.motion_profiles import (
    MotionModeProfile,
    describe_motion_profile,
    profile_for_motion_mode,
)


def build_stand_command_data(
    profile: MotionModeProfile | None = None,
) -> tuple[float, ...]:
    resolved_profile = profile or profile_for_motion_mode("legged")
    return tuple(resolved_profile.stand_pose)


def build_stand_command(profile: MotionModeProfile | None = None):
    from std_msgs.msg import Float64MultiArray

    msg = Float64MultiArray()
    msg.data = list(build_stand_command_data(profile))
    return msg


def main() -> None:
    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from std_msgs.msg import Float64MultiArray

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--leg-command-topic",
        default="/leg_position_controller/commands",
    )
    parser.add_argument(
        "--motion-mode",
        choices=("wheeled", "legged"),
        default="legged",
    )
    parser.add_argument("--duration-sec", type=float, default=2.0)
    parser.add_argument("--rate-hz", type=float, default=20.0)
    args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    profile = profile_for_motion_mode(args.motion_mode)

    class StandInitializerNode(Node):
        def __init__(self) -> None:
            super().__init__("go2w_stand_initializer")
            self._stand_pub = self.create_publisher(
                Float64MultiArray,
                args.leg_command_topic,
                10,
            )
            self._profile = profile
            self.get_logger().info(
                "go2w_stand_initializer_profile: "
                f"{describe_motion_profile(self._profile)}"
            )

        def publish_stand_pose(self) -> None:
            duration_sec = max(0.1, float(args.duration_sec))
            rate_hz = max(1.0, float(args.rate_hz))
            interval_sec = 1.0 / rate_hz
            end_time = time.monotonic() + duration_sec
            command = build_stand_command(self._profile)

            while rclpy.ok() and time.monotonic() < end_time:
                self._stand_pub.publish(command)
                rclpy.spin_once(self, timeout_sec=0.0)
                time.sleep(interval_sec)

            self.get_logger().info(
                "go2w_stand_initializer_result: PASS "
                f"motion_mode={self._profile.mode} "
                f"body_height_m={self._profile.body_height_m:.2f} "
                f"foot_raise_height_m={self._profile.foot_raise_height_m:.2f} "
                f"gait_type={self._profile.gait_type} "
                f"speed_level={self._profile.speed_level} "
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
