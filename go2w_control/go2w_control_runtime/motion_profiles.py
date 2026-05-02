from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace


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


def derive_motion_profile(
    profile: MotionModeProfile,
    *,
    body_height_m: float | None = None,
    foot_raise_height_m: float | None = None,
    gait_type: int | None = None,
    speed_level: int | None = None,
    max_linear_velocity_mps: float | None = None,
    default_stair_linear_velocity_mps: float | None = None,
    stand_transition_sec: float | None = None,
) -> MotionModeProfile:
    changes = {}
    if body_height_m is not None:
        changes["body_height_m"] = body_height_m
    if foot_raise_height_m is not None:
        changes["foot_raise_height_m"] = foot_raise_height_m
    if gait_type is not None:
        changes["gait_type"] = gait_type
    if speed_level is not None:
        changes["speed_level"] = speed_level
    if max_linear_velocity_mps is not None:
        changes["max_linear_velocity_mps"] = max_linear_velocity_mps
    if default_stair_linear_velocity_mps is not None:
        changes["default_stair_linear_velocity_mps"] = default_stair_linear_velocity_mps
    if stand_transition_sec is not None:
        changes["stand_transition_sec"] = stand_transition_sec
    if not changes:
        return profile
    return replace(profile, **changes)


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
    # Unitree ROS2 documentation exposes the sport-mode gait enum, including
    # `3.climb stair`, and the public `read_motion_state` example shows the
    # same conservative body height / foot raise height values we use here.
    # Treat these fields as a conservative metadata baseline, not as proof of
    # tuned stair locomotion.
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
