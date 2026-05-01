from go2w_control_runtime.motion_profiles import get_go2w_motion_profiles


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

