from __future__ import annotations

import argparse
from dataclasses import dataclass
import time

from go2w_control_runtime.motion_profiles import (
    MotionModeProfile,
    describe_motion_profile,
    derive_motion_profile,
    get_go2w_motion_profiles,
)


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


def _duration_from_seconds(seconds: float):
    from builtin_interfaces.msg import Duration

    bounded_seconds = max(0.0, float(seconds))
    duration = Duration()
    duration.sec = int(bounded_seconds)
    duration.nanosec = int(
        round((bounded_seconds - duration.sec) * 1_000_000_000)
    )
    if duration.nanosec >= 1_000_000_000:
        duration.sec += 1
        duration.nanosec -= 1_000_000_000
    return duration


@dataclass(frozen=True)
class StairExecutionPhase:
    name: str
    duration_sec: float
    command_velocity_mps: float
    body_height_m: float
    foot_raise_height_m: float
    wheel_lock_required: bool
    publish_leg_hold: bool


@dataclass(frozen=True)
class StairExecutionPlan:
    phases: tuple[StairExecutionPhase, ...]
    total_duration_sec: float

    def phase_names(self) -> tuple[str, ...]:
        return tuple(phase.name for phase in self.phases)


def build_stair_phase_trajectory_command_data(
    phase: StairExecutionPhase,
    profile: MotionModeProfile | None = None,
) -> tuple[float, ...]:
    resolved_profile = profile or get_go2w_motion_profiles().legged
    target = list(resolved_profile.stand_pose)
    nominal_height = max(0.01, resolved_profile.body_height_m)
    height_delta = resolved_profile.body_height_m - phase.body_height_m
    thigh_delta = round(height_delta * 1.0, 6)
    calf_delta = round(-height_delta * 2.0, 6)
    swing_delta = 0.0
    if phase.name == "execute_stairs":
        swing_delta = min(phase.foot_raise_height_m, 0.03)

    for leg_index in range(4):
        base = leg_index * 3
        target[base + 1] = round(target[base + 1] + thigh_delta, 6)
        target[base + 2] = round(target[base + 2] + calf_delta, 6)

    if swing_delta > 0.0:
        for leg_index in (0, 1):
            base = leg_index * 3
            target[base + 1] = round(
                resolved_profile.stand_pose[base + 1] - swing_delta,
                6,
            )
            target[base + 2] = round(
                resolved_profile.stand_pose[base + 2] + swing_delta,
                6,
            )

    # Keep the synthetic target inside a conservative envelope around the stand
    # pose. This is a command outlet skeleton, not a tuned gait generator.
    bounded = []
    for value, stand_value in zip(target, resolved_profile.stand_pose, strict=True):
        lower = stand_value - nominal_height
        upper = stand_value + nominal_height
        bounded.append(round(min(max(value, lower), upper), 6))
    return tuple(bounded)


def build_stair_phase_trajectory_command(
    phase: StairExecutionPhase,
    profile: MotionModeProfile | None = None,
):
    from std_msgs.msg import Float64MultiArray

    command = Float64MultiArray()
    command.data = list(build_stair_phase_trajectory_command_data(phase, profile))
    return command


def build_stair_phase_trajectory_message(
    phase: StairExecutionPhase,
    profile: MotionModeProfile | None = None,
):
    from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

    resolved_profile = profile or get_go2w_motion_profiles().legged
    point = JointTrajectoryPoint()
    point.positions = list(
        build_stair_phase_trajectory_command_data(phase, resolved_profile)
    )
    point.time_from_start = _duration_from_seconds(phase.duration_sec)

    msg = JointTrajectory()
    msg.joint_names = list(resolved_profile.leg_joints)
    msg.points = [point]
    return msg


def summarize_stair_phase_trajectory(
    phase: StairExecutionPhase,
    profile: MotionModeProfile | None = None,
) -> str:
    command_data = build_stair_phase_trajectory_command_data(phase, profile)
    checksum = sum(command_data)
    return (
        f"trajectory_joint_count={len(command_data)} "
        f"trajectory_checksum={checksum:.6f}"
    )


def build_stair_execution_state_text(
    *,
    phase: StairExecutionPhase,
    profile: MotionModeProfile,
    owner: str,
    progress: float,
) -> str:
    return (
        f"phase={phase.name} "
        f"owner={owner} "
        f"mode={profile.mode} "
        f"body_height_m={phase.body_height_m:.2f} "
        f"foot_raise_height_m={phase.foot_raise_height_m:.2f} "
        f"cmd_vel_mps={phase.command_velocity_mps:.3f} "
        f"wheel_lock_required={str(phase.wheel_lock_required).lower()} "
        f"publish_leg_hold={str(phase.publish_leg_hold).lower()} "
        f"{summarize_stair_phase_trajectory(phase, profile)} "
        f"progress={progress:.3f}"
    )


class StairExecutionPolicy:
    def __init__(
        self,
        min_duration_sec: float = 0.05,
        timeout_duration_sec: float = 5.0,
        profile: MotionModeProfile | None = None,
        body_height_m: float | None = None,
        execute_body_height_m: float | None = None,
        foot_raise_height_m: float | None = None,
        gait_type: int | None = None,
        speed_level: int | None = None,
        max_linear_velocity_mps: float | None = None,
        stair_linear_velocity_mps: float | None = None,
    ) -> None:
        self.min_duration_sec = min_duration_sec
        self.timeout_duration_sec = timeout_duration_sec
        base_profile = profile or get_go2w_motion_profiles().legged
        self.profile = derive_motion_profile(
            base_profile,
            body_height_m=body_height_m,
            foot_raise_height_m=foot_raise_height_m,
            gait_type=gait_type,
            speed_level=speed_level,
            max_linear_velocity_mps=max_linear_velocity_mps,
        )
        self.motion_mode = self.profile.mode
        self.stand_pose_joint_count = len(self.profile.stand_pose)
        self.execute_body_height_m = (
            self.profile.body_height_m
            if execute_body_height_m is None
            else max(0.0, float(execute_body_height_m))
        )
        requested_velocity = (
            self.profile.default_stair_linear_velocity_mps
            if stair_linear_velocity_mps is None
            else stair_linear_velocity_mps
        )
        self.stair_linear_velocity_mps = min(
            max(0.0, requested_velocity),
            self.profile.max_linear_velocity_mps,
        )

    def build_phase_plan(
        self,
        requested_sec: float,
        *,
        force_timeout: bool,
    ) -> StairExecutionPlan:
        total_duration_sec = self.execution_duration(
            requested_sec,
            force_timeout=force_timeout,
        )
        nominal_body_height_m = self.profile.body_height_m
        execute_body_height_m = self.execute_body_height_m
        phase_specs = (
            ("prepare", 0.12, 0.0, nominal_body_height_m, False, True),
            ("wheel_lock", 0.10, 0.0, nominal_body_height_m, True, True),
            (
                "body_height_transition_down",
                0.18,
                0.0,
                execute_body_height_m,
                True,
                True,
            ),
            (
                "execute_stairs",
                0.32,
                self.stair_linear_velocity_mps,
                execute_body_height_m,
                True,
                True,
            ),
            (
                "body_height_transition_up",
                0.18,
                0.0,
                nominal_body_height_m,
                True,
                True,
            ),
            ("release", 0.10, 0.0, nominal_body_height_m, False, False),
        )
        phases = []
        for (
            name,
            weight,
            velocity_mps,
            phase_body_height_m,
            wheel_lock_required,
            publish_leg_hold,
        ) in phase_specs:
            duration_sec = max(self.min_duration_sec, total_duration_sec * weight)
            phases.append(
                StairExecutionPhase(
                    name=name,
                    duration_sec=duration_sec,
                    command_velocity_mps=velocity_mps,
                    body_height_m=phase_body_height_m,
                    foot_raise_height_m=self.profile.foot_raise_height_m,
                    wheel_lock_required=wheel_lock_required,
                    publish_leg_hold=publish_leg_hold,
                )
            )
        summed_duration_sec = sum(phase.duration_sec for phase in phases)
        plan = StairExecutionPlan(
            phases=tuple(phases),
            total_duration_sec=max(total_duration_sec, summed_duration_sec),
        )
        return plan

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


def _stair_twist(linear_x: float = 0.0):
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

    parser = argparse.ArgumentParser()
    parser.add_argument("--min-duration-sec", type=float, default=0.05)
    parser.add_argument("--timeout-duration-sec", type=float, default=5.0)
    parser.add_argument("--stair-body-height-m", type=float, default=None)
    parser.add_argument("--stair-execute-body-height-m", type=float, default=None)
    parser.add_argument("--stair-foot-raise-height-m", type=float, default=None)
    parser.add_argument("--stair-gait-type", type=int, default=None)
    parser.add_argument("--stair-speed-level", type=int, default=None)
    parser.add_argument("--stair-max-linear-velocity-mps", type=float, default=None)
    parser.add_argument("--stair-linear-velocity-mps", type=float, default=None)
    args, ros_args = parser.parse_known_args()

    class StairExecutorNode(Node):
        def __init__(self) -> None:
            from std_msgs.msg import Float64MultiArray
            from std_msgs.msg import String
            from trajectory_msgs.msg import JointTrajectory

            super().__init__("go2w_stair_executor")
            self._policy = StairExecutionPolicy(
                min_duration_sec=float(args.min_duration_sec),
                timeout_duration_sec=float(args.timeout_duration_sec),
                body_height_m=args.stair_body_height_m,
                execute_body_height_m=args.stair_execute_body_height_m,
                foot_raise_height_m=args.stair_foot_raise_height_m,
                gait_type=args.stair_gait_type,
                speed_level=args.stair_speed_level,
                max_linear_velocity_mps=args.stair_max_linear_velocity_mps,
                stair_linear_velocity_mps=args.stair_linear_velocity_mps,
            )
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
            self._trajectory_pub = self.create_publisher(
                JointTrajectory,
                "/go2w/control/stair_leg_trajectory",
                10,
            )
            self._state_pub = self.create_publisher(
                String,
                "/go2w/control/stair_execution_state",
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
            self.get_logger().info(
                "go2w_stair_executor_profile: "
                f"{describe_motion_profile(self._policy.profile)} "
                f"execute_body_height_m={self._policy.execute_body_height_m:.2f} "
                f"stair_linear_velocity_mps={self._policy.stair_linear_velocity_mps:.3f}"
            )

        def _cancel_callback(self, _cancel_request):
            return CancelResponse.ACCEPT

        def _execute_callback(self, goal_handle):
            goal = goal_handle.request
            started = time.monotonic()
            plan = self._policy.build_phase_plan(
                float(goal.expected_duration_sec),
                force_timeout=bool(goal.force_timeout),
            )
            self.get_logger().info(
                "go2w_stair_executor_plan: "
                f"phases={','.join(plan.phase_names())} "
                f"total_duration_sec={plan.total_duration_sec:.2f}"
            )
            self._owner_pub.publish(_string_msg("stair"))
            self._publish_state(plan.phases[0], progress=0.0)
            self._publish_leg_target(plan.phases[0])

            elapsed = 0.0
            for phase in plan.phases:
                phase_started = time.monotonic()
                self._publish_state(phase, progress=min(1.0, elapsed / plan.total_duration_sec))
                self._publish_phase_feedback(goal_handle, phase, elapsed, plan.total_duration_sec)
                while rclpy.ok():
                    elapsed = time.monotonic() - started
                    phase_elapsed = time.monotonic() - phase_started
                    progress = min(1.0, elapsed / plan.total_duration_sec)
                    if goal_handle.is_cancel_requested:
                        self._stair_cmd_pub.publish(_zero_twist())
                        self._owner_pub.publish(_string_msg("flat"))
                        self._publish_state(
                            phase,
                            progress=progress,
                            suffix="canceled",
                        )
                        goal_handle.canceled()
                        return self._result(
                            StairExec,
                            success=False,
                            result_code="CANCELED",
                            message="stair execution canceled",
                            elapsed=time.monotonic() - started,
                        )

                    if phase_elapsed >= phase.duration_sec:
                        break

                    if phase.command_velocity_mps > 0.0:
                        self._stair_cmd_pub.publish(
                            _stair_twist(phase.command_velocity_mps)
                        )
                    else:
                        self._stair_cmd_pub.publish(_zero_twist())
                    if phase.publish_leg_hold:
                        self._publish_leg_target(phase)
                    self._publish_state(phase, progress=progress)
                    self._publish_phase_feedback(
                        goal_handle,
                        phase,
                        elapsed,
                        plan.total_duration_sec,
                    )
                    time.sleep(0.1)

                elapsed = time.monotonic() - started
                self._publish_state(phase, progress=min(1.0, elapsed / plan.total_duration_sec))

            self._stair_cmd_pub.publish(_zero_twist())
            self._publish_leg_target(plan.phases[-1])
            self._owner_pub.publish(_string_msg("flat"))
            self._publish_state(
                plan.phases[-1],
                progress=1.0,
                suffix="complete",
            )

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

        def _publish_state(
            self,
            phase: StairExecutionPhase,
            *,
            progress: float,
            suffix: str = "",
        ) -> None:
            from std_msgs.msg import String

            state_text = build_stair_execution_state_text(
                phase=phase,
                profile=self._policy.profile,
                owner="stair",
                progress=progress,
            )
            if suffix:
                state_text = f"{state_text} {suffix}"
            state_msg = String()
            state_msg.data = state_text
            self._state_pub.publish(state_msg)
            self.get_logger().info(f"go2w_stair_executor_state: {state_text}")

        def _publish_leg_target(self, phase: StairExecutionPhase) -> None:
            self._leg_hold_pub.publish(
                build_stair_phase_trajectory_command(phase, self._policy.profile)
            )
            self._trajectory_pub.publish(
                build_stair_phase_trajectory_message(phase, self._policy.profile)
            )
            self.get_logger().info(
                "go2w_stair_executor_trajectory: "
                f"phase={phase.name} "
                f"{summarize_stair_phase_trajectory(phase, self._policy.profile)}"
            )

        def _publish_phase_feedback(
            self,
            goal_handle,
            phase: StairExecutionPhase,
            elapsed: float,
            total_duration_sec: float,
        ) -> None:
            feedback = StairExec.Feedback()
            feedback.phase = phase.name
            feedback.progress = float(min(1.0, elapsed / total_duration_sec))
            feedback.owner = "stair"
            goal_handle.publish_feedback(feedback)

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

    rclpy.init(args=ros_args)
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
