from dataclasses import replace

from go2w_control_runtime.stair_executor import (
    StairExecutionPolicy,
    build_stair_execution_state_text,
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
    assert policy.stair_linear_velocity_mps == 0.025
    assert policy.profile.default_stair_linear_velocity_mps == 0.025


def test_stair_velocity_is_clamped_by_profile_limit() -> None:
    legged = get_go2w_motion_profiles().legged
    limited_profile = replace(legged, max_linear_velocity_mps=0.02)

    policy = StairExecutionPolicy(
        profile=limited_profile,
        stair_linear_velocity_mps=0.03,
    )

    assert policy.stair_linear_velocity_mps == 0.02


def test_stair_velocity_override_is_preserved_within_profile_limit() -> None:
    policy = StairExecutionPolicy(stair_linear_velocity_mps=0.01)

    assert policy.stair_linear_velocity_mps == 0.01


def test_leg_hold_command_uses_profile_stand_pose() -> None:
    legged = get_go2w_motion_profiles().legged

    command_data = build_leg_hold_command_data(legged)

    assert command_data == legged.stand_pose
    assert len(command_data) == 12


def test_state_text_includes_phase_and_profile_metadata() -> None:
    legged = get_go2w_motion_profiles().legged
    plan = StairExecutionPolicy(profile=legged).build_phase_plan(
        0.5,
        force_timeout=False,
    )
    phase = plan.phases[3]

    state_text = build_stair_execution_state_text(
        phase=phase,
        profile=legged,
        owner="stair",
        progress=0.625,
    )

    assert "phase=execute_stairs" in state_text
    assert "owner=stair" in state_text
    assert "mode=legged" in state_text
    assert "body_height_m=0.32" in state_text
    assert "foot_raise_height_m=0.09" in state_text
    assert "wheel_lock_required=true" in state_text
    assert "publish_leg_hold=true" in state_text
    assert "progress=0.625" in state_text


def test_phase_plan_keeps_expected_order_and_velocity_profile() -> None:
    policy = StairExecutionPolicy()
    plan = policy.build_phase_plan(0.5, force_timeout=False)

    assert plan.phase_names() == (
        "prepare",
        "wheel_lock",
        "body_height_transition_down",
        "execute_stairs",
        "body_height_transition_up",
        "release",
    )
    assert plan.total_duration_sec >= 0.5
    assert plan.phases[3].command_velocity_mps == policy.stair_linear_velocity_mps
    assert plan.phases[0].publish_leg_hold is True
    assert plan.phases[-1].publish_leg_hold is False


def test_phase_plan_marks_wheel_lock_and_execute_body_height_target() -> None:
    policy = StairExecutionPolicy(execute_body_height_m=0.29)
    plan = policy.build_phase_plan(0.5, force_timeout=False)
    phases = {phase.name: phase for phase in plan.phases}

    assert phases["prepare"].body_height_m == policy.profile.body_height_m
    assert phases["wheel_lock"].body_height_m == policy.profile.body_height_m
    assert phases["body_height_transition_down"].body_height_m == 0.29
    assert phases["execute_stairs"].body_height_m == 0.29
    assert phases["body_height_transition_up"].body_height_m == policy.profile.body_height_m
    assert phases["release"].body_height_m == policy.profile.body_height_m
    assert phases["prepare"].wheel_lock_required is False
    assert phases["wheel_lock"].wheel_lock_required is True
    assert phases["body_height_transition_down"].wheel_lock_required is True
    assert phases["execute_stairs"].wheel_lock_required is True
    assert phases["body_height_transition_up"].wheel_lock_required is True
    assert phases["release"].wheel_lock_required is False
