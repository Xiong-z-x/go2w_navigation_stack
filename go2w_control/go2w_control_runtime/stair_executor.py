from __future__ import annotations

import time

from go2w_control_runtime.motion_profiles import (
    MotionModeProfile,
    get_go2w_motion_profiles,
)


DEFAULT_STAIR_LINEAR_VELOCITY_MPS = 0.03


def build_leg_hold_command_data(
    profile: MotionModeProfile | None = None,
) -> tuple[float, ...]:
    resolved_profile = profile or get_go2w_motion_profiles().legged
    return tuple(resolved_profile.stand_pose)


def build_leg_hold_command(profile: MotionModeProfile | None = None):
    from std_msgs.msg import Float64MultiArray

    command = Float64MultiArray()
    command.data = list(build_leg_hold_command_data(profile))
    return command


class StairExecutionPolicy:
    def __init__(
        self,
        min_duration_sec: float = 0.05,
        timeout_duration_sec: float = 5.0,
        profile: MotionModeProfile | None = None,
        stair_linear_velocity_mps: float = DEFAULT_STAIR_LINEAR_VELOCITY_MPS,
    ) -> None:
        self.min_duration_sec = min_duration_sec
        self.timeout_duration_sec = timeout_duration_sec
        self.profile = profile or get_go2w_motion_profiles().legged
        self.motion_mode = self.profile.mode
        self.stand_pose_joint_count = len(self.profile.stand_pose)
        self.stair_linear_velocity_mps = min(
            max(0.0, stair_linear_velocity_mps),
            self.profile.max_linear_velocity_mps,
        )

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


def _duration_msg(elapsed_sec: float):
    from builtin_interfaces.msg import Duration

    duration = Duration()
    duration.sec = int(elapsed_sec)
    duration.nanosec = int((elapsed_sec - duration.sec) * 1_000_000_000)
    return duration


def _string_msg(value: str):
    from std_msgs.msg import String

    msg = String()
    msg.data = value
    return msg


def _stair_twist(linear_x: float = DEFAULT_STAIR_LINEAR_VELOCITY_MPS):
    from geometry_msgs.msg import Twist

    msg = Twist()
    msg.linear.x = linear_x
    return msg


def _zero_twist():
    from geometry_msgs.msg import Twist

    return Twist()


def main() -> None:
    import rclpy
    from rclpy.action import ActionServer, CancelResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.node import Node

    from go2w_control.action import StairExec

    class StairExecutorNode(Node):
        def __init__(self) -> None:
            from std_msgs.msg import Float64MultiArray

            super().__init__("go2w_stair_executor")
            self._policy = StairExecutionPolicy()
            self._callback_group = ReentrantCallbackGroup()
            self._owner_pub = self.create_publisher(
                _string_msg("").__class__,
                "/go2w/control/command_owner",
                10,
            )
            self._stair_cmd_pub = self.create_publisher(
                _stair_twist(self._policy.stair_linear_velocity_mps).__class__,
                "/go2w/control/stair_cmd_vel",
                10,
            )
            self._leg_hold_pub = self.create_publisher(
                Float64MultiArray,
                "/leg_position_controller/commands",
                10,
            )
            self._server = ActionServer(
                self,
                StairExec,
                "/stair_exec",
                self._execute_callback,
                callback_group=self._callback_group,
                cancel_callback=self._cancel_callback,
            )

        def _cancel_callback(self, _cancel_request):
            return CancelResponse.ACCEPT

        def _execute_callback(self, goal_handle):
            goal = goal_handle.request
            started = time.monotonic()
            duration = self._policy.execution_duration(
                float(goal.expected_duration_sec),
                force_timeout=bool(goal.force_timeout),
            )
            self._owner_pub.publish(_string_msg("stair"))
            self._leg_hold_pub.publish(build_leg_hold_command(self._policy.profile))

            while rclpy.ok():
                elapsed = time.monotonic() - started
                progress = min(1.0, elapsed / duration)
                feedback = StairExec.Feedback()
                feedback.phase = "executing_stair"
                feedback.progress = float(progress)
                feedback.owner = "stair"
                goal_handle.publish_feedback(feedback)
                self._leg_hold_pub.publish(build_leg_hold_command(self._policy.profile))
                self._stair_cmd_pub.publish(
                    _stair_twist(self._policy.stair_linear_velocity_mps)
                )

                if goal_handle.is_cancel_requested:
                    self._stair_cmd_pub.publish(_zero_twist())
                    self._owner_pub.publish(_string_msg("flat"))
                    goal_handle.canceled()
                    return self._result(
                        StairExec,
                        success=False,
                        result_code="CANCELED",
                        message="stair execution canceled",
                        elapsed=time.monotonic() - started,
                    )

                if elapsed >= duration:
                    break
                time.sleep(0.1)

            self._stair_cmd_pub.publish(_zero_twist())
            self._leg_hold_pub.publish(build_leg_hold_command(self._policy.profile))
            self._owner_pub.publish(_string_msg("flat"))

            if goal.force_fail:
                goal_handle.abort()
                return self._result(
                    StairExec,
                    success=False,
                    result_code="FAILED",
                    message="forced stair execution failure",
                    elapsed=time.monotonic() - started,
                )

            goal_handle.succeed()
            return self._result(
                StairExec,
                success=True,
                result_code="SUCCEEDED",
                message="stair execution skeleton completed",
                elapsed=time.monotonic() - started,
            )

        def _result(
            self,
            action_type,
            *,
            success: bool,
            result_code: str,
            message: str,
            elapsed: float,
        ):
            result = action_type.Result()
            result.success = success
            result.result_code = result_code
            result.message = message
            result.elapsed_time = _duration_msg(elapsed)
            return result

    rclpy.init()
    node = StairExecutorNode()
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
