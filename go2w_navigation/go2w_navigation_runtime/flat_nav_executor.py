from __future__ import annotations

import argparse
import sys
import time


class FlatNavPolicy:
    def __init__(
        self,
        min_duration_sec: float = 0.05,
        timeout_duration_sec: float = 5.0,
    ) -> None:
        self.min_duration_sec = min_duration_sec
        self.timeout_duration_sec = timeout_duration_sec

    def result_code(self, *, force_fail: bool, canceled: bool) -> str:
        if canceled:
            return "CANCELED"
        if force_fail:
            return "FAILED"
        return "SUCCEEDED"

    def execution_duration(self, requested_sec: float, *, force_timeout: bool) -> float:
        if force_timeout:
            return max(self.timeout_duration_sec, requested_sec)
        return max(self.min_duration_sec, requested_sec)


def _string_msg(value: str):
    from std_msgs.msg import String

    msg = String()
    msg.data = value
    return msg


def _flat_twist():
    from geometry_msgs.msg import Twist

    msg = Twist()
    msg.linear.x = 0.04
    return msg


def _zero_twist():
    from geometry_msgs.msg import Twist

    return Twist()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-name", default="/navigate_to_pose")
    parser.add_argument("--mode", choices=("success", "failure", "timeout"), default="success")
    parser.add_argument("--duration-sec", type=float, default=0.2)
    parser.add_argument("--timeout-duration-sec", type=float, default=5.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    import rclpy
    from nav2_msgs.action import NavigateToPose
    from rclpy.action import ActionServer, CancelResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.node import Node

    args = parse_args(sys.argv[1:] if argv is None else argv)

    class FlatNavExecutorNode(Node):
        def __init__(self) -> None:
            super().__init__("go2w_flat_nav_executor")
            self._policy = FlatNavPolicy(timeout_duration_sec=args.timeout_duration_sec)
            self._callback_group = ReentrantCallbackGroup()
            self._owner_pub = self.create_publisher(
                _string_msg("").__class__,
                "/go2w/control/command_owner",
                10,
            )
            self._flat_cmd_pub = self.create_publisher(
                _flat_twist().__class__,
                "/go2w/control/flat_cmd_vel",
                10,
            )
            self._server = ActionServer(
                self,
                NavigateToPose,
                args.action_name,
                self._execute_callback,
                callback_group=self._callback_group,
                cancel_callback=self._cancel_callback,
            )

        def _cancel_callback(self, _cancel_request):
            return CancelResponse.ACCEPT

        def _execute_callback(self, goal_handle):
            _ = goal_handle.request
            started = time.monotonic()
            force_timeout = args.mode == "timeout"
            force_fail = args.mode == "failure"
            duration = self._policy.execution_duration(
                args.duration_sec,
                force_timeout=force_timeout,
            )
            self._owner_pub.publish(_string_msg("flat"))

            while rclpy.ok():
                elapsed = time.monotonic() - started
                feedback = NavigateToPose.Feedback()
                feedback.navigation_time.sec = int(elapsed)
                feedback.navigation_time.nanosec = int(
                    (elapsed - feedback.navigation_time.sec) * 1_000_000_000
                )
                feedback.distance_remaining = max(0.0, 1.0 - (elapsed / duration))
                goal_handle.publish_feedback(feedback)
                self._flat_cmd_pub.publish(_flat_twist())

                if goal_handle.is_cancel_requested:
                    self._flat_cmd_pub.publish(_zero_twist())
                    goal_handle.canceled()
                    return NavigateToPose.Result()

                if elapsed >= duration:
                    break
                time.sleep(0.1)

            self._flat_cmd_pub.publish(_zero_twist())

            if force_fail:
                goal_handle.abort()
                return NavigateToPose.Result()

            goal_handle.succeed()
            return NavigateToPose.Result()

    rclpy.init()
    node = FlatNavExecutorNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
