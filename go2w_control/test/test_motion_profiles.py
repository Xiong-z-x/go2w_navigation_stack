import pytest

from go2w_control_runtime.motion_profiles import (
    describe_motion_profile,
    get_go2w_motion_profiles,
    profile_for_motion_mode,
)
from go2w_control_runtime.stand_initializer import build_stand_command_data


def test_go2w_motion_profiles_cover_wheeled_and_legged_modes() -> None:
    profiles = get_go2w_motion_profiles()

    assert profiles.wheeled.owner == "flat"
    assert profiles.wheeled.mode == "wheeled"
    assert profiles.legged.owner == "stair"
    assert profiles.legged.mode == "legged"
    assert profiles.legged.stand_pose[:3] == (0.0, 0.67, -1.3)


def test_stand_pose_matches_leg_joint_order() -> None:
    profiles = get_go2w_motion_profiles()

    assert profiles.legged.leg_joints == (
        "FL_hip_joint",
        "FL_thigh_joint",
        "FL_calf_joint",
        "FR_hip_joint",
        "FR_thigh_joint",
        "FR_calf_joint",
        "RL_hip_joint",
        "RL_thigh_joint",
        "RL_calf_joint",
        "RR_hip_joint",
        "RR_thigh_joint",
        "RR_calf_joint",
    )
    assert profiles.legged.stand_pose == (
        0.0,
        0.67,
        -1.3,
        0.0,
        0.67,
        -1.3,
        0.0,
        0.67,
        -1.3,
        0.0,
        0.67,
        -1.3,
    )


def test_wheeled_profile_uses_four_foot_wheels() -> None:
    profiles = get_go2w_motion_profiles()

    assert profiles.wheeled.wheel_joints == (
        "FL_foot_joint",
        "FR_foot_joint",
        "RL_foot_joint",
        "RR_foot_joint",
    )
    assert profiles.wheeled.wheels_per_side == 2
    assert profiles.wheeled.wheel_radius_m == 0.10
    assert profiles.wheeled.wheel_separation_m == 0.38


def test_motion_profiles_include_explicit_mode_metadata() -> None:
    profiles = get_go2w_motion_profiles()

    assert profiles.wheeled.body_height_m == 0.32
    assert profiles.wheeled.foot_raise_height_m == 0.03
    assert profiles.wheeled.gait_type == 1
    assert profiles.wheeled.speed_level == 0
    assert profiles.wheeled.default_stair_linear_velocity_mps == 0.0

    assert profiles.legged.body_height_m == 0.32
    assert profiles.legged.foot_raise_height_m == 0.09
    assert profiles.legged.gait_type == 3
    assert profiles.legged.speed_level == 0
    assert profiles.legged.max_linear_velocity_mps == 0.15
    assert profiles.legged.default_stair_linear_velocity_mps == 0.025


def test_profile_lookup_and_summary_are_stable() -> None:
    legged = profile_for_motion_mode("legged")
    wheeled = profile_for_motion_mode("wheeled")

    assert legged.mode == "legged"
    assert wheeled.mode == "wheeled"
    with pytest.raises(ValueError, match="unsupported motion mode"):
        profile_for_motion_mode("crawl")

    summary = describe_motion_profile(legged)

    assert "mode=legged" in summary
    assert "body_height_m=0.32" in summary
    assert "foot_raise_height_m=0.09" in summary
    assert "gait_type=3" in summary
    assert "default_stair_linear_velocity_mps=0.025" in summary


def test_stand_command_data_can_use_selected_motion_profile() -> None:
    legged = profile_for_motion_mode("legged")

    command_data = build_stand_command_data(legged)

    assert command_data == legged.stand_pose
    assert build_stand_command_data() == legged.stand_pose
