from __future__ import annotations

from dataclasses import dataclass


LEG_JOINTS = (
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

WHEEL_JOINTS = (
    "FL_foot_joint",
    "FR_foot_joint",
    "RL_foot_joint",
    "RR_foot_joint",
)

STAND_POSE = (
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

OWNER_TO_MODE = {
    "flat": "wheeled",
    "stair": "legged",
}


@dataclass(frozen=True)
class MotionModeProfile:
    owner: str
    mode: str
    leg_joints: tuple[str, ...]
    wheel_joints: tuple[str, ...]
    stand_pose: tuple[float, ...]
    wheels_per_side: int
    wheel_radius_m: float
    wheel_separation_m: float
    max_linear_velocity_mps: float
    max_angular_velocity_rps: float
    stand_transition_sec: float
    body_height_m: float
    foot_raise_height_m: float
    gait_type: int
    speed_level: int
    default_stair_linear_velocity_mps: float


@dataclass(frozen=True)
class Go2WMotionProfiles:
    wheeled: MotionModeProfile
    legged: MotionModeProfile


def motion_mode_for_owner(owner: str) -> str:
    normalized = owner.strip().lower()
    if normalized not in OWNER_TO_MODE:
        raise ValueError(f"unsupported command owner for motion mode: {owner}")
    return OWNER_TO_MODE[normalized]


def profile_for_motion_mode(mode: str) -> MotionModeProfile:
    normalized = mode.strip().lower()
    profiles = get_go2w_motion_profiles()
    if normalized == "wheeled":
        return profiles.wheeled
    if normalized == "legged":
        return profiles.legged
    raise ValueError(f"unsupported motion mode: {mode}")


def describe_motion_profile(profile: MotionModeProfile) -> str:
    return (
        f"owner={profile.owner} "
        f"mode={profile.mode} "
        f"body_height_m={profile.body_height_m:.2f} "
        f"foot_raise_height_m={profile.foot_raise_height_m:.2f} "
        f"gait_type={profile.gait_type} "
        f"speed_level={profile.speed_level} "
        f"default_stair_linear_velocity_mps={profile.default_stair_linear_velocity_mps:.3f} "
        f"stand_transition_sec={profile.stand_transition_sec:.1f}"
    )


def get_go2w_motion_profiles() -> Go2WMotionProfiles:
    common = {
        "leg_joints": LEG_JOINTS,
        "wheel_joints": WHEEL_JOINTS,
        "stand_pose": STAND_POSE,
        "wheels_per_side": 2,
        "wheel_radius_m": 0.10,
        "wheel_separation_m": 0.38,
        "max_angular_velocity_rps": 1.5,
        "stand_transition_sec": 2.0,
        "body_height_m": 0.32,
        "speed_level": 0,
    }
    return Go2WMotionProfiles(
        wheeled=MotionModeProfile(
            owner="flat",
            mode="wheeled",
            max_linear_velocity_mps=1.0,
            foot_raise_height_m=0.03,
            gait_type=1,
            default_stair_linear_velocity_mps=0.0,
            **common,
        ),
        legged=MotionModeProfile(
            owner="stair",
            mode="legged",
            max_linear_velocity_mps=0.15,
            foot_raise_height_m=0.09,
            gait_type=3,
            default_stair_linear_velocity_mps=0.025,
            **common,
        ),
    )
