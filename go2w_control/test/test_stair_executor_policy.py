from dataclasses import replace

from go2w_control_runtime.stair_executor import (
    StairExecutionPolicy,
    build_leg_hold_command_data,
)
from go2w_control_runtime.motion_profiles import get_go2w_motion_profiles


def test_success_goal_finishes_with_success_code() -> None:
    policy = StairExecutionPolicy()

    assert policy.result_code(force_fail=False, canceled=False) == "SUCCEEDED"


def test_force_fail_goal_finishes_with_failure_code() -> None:
    policy = StairExecutionPolicy()

    assert policy.result_code(force_fail=True, canceled=False) == "FAILED"


def test_cancel_preempts_failure_code() -> None:
    policy = StairExecutionPolicy()

    assert policy.result_code(force_fail=True, canceled=True) == "CANCELED"


def test_force_timeout_extends_execution_window() -> None:
    policy = StairExecutionPolicy()

    assert policy.execution_duration(0.2, force_timeout=False) == 0.2
    assert policy.execution_duration(0.2, force_timeout=True) >= 5.0
    assert policy.execution_duration(0.0, force_timeout=False) > 0.0


def test_policy_uses_legged_motion_profile() -> None:
    policy = StairExecutionPolicy()

    assert policy.motion_mode == "legged"
    assert policy.stand_pose_joint_count == 12
    assert policy.stair_linear_velocity_mps == 0.03


def test_stair_velocity_is_clamped_by_profile_limit() -> None:
    legged = get_go2w_motion_profiles().legged
    limited_profile = replace(legged, max_linear_velocity_mps=0.02)

    policy = StairExecutionPolicy(
        profile=limited_profile,
        stair_linear_velocity_mps=0.03,
    )

    assert policy.stair_linear_velocity_mps == 0.02


def test_leg_hold_command_uses_profile_stand_pose() -> None:
    legged = get_go2w_motion_profiles().legged

    command_data = build_leg_hold_command_data(legged)

    assert command_data == legged.stand_pose
    assert len(command_data) == 12
