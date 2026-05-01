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


@dataclass(frozen=True)
class Go2WMotionProfiles:
    wheeled: MotionModeProfile
    legged: MotionModeProfile


def motion_mode_for_owner(owner: str) -> str:
    normalized = owner.strip().lower()
    if normalized not in OWNER_TO_MODE:
        raise ValueError(f"unsupported command owner for motion mode: {owner}")
    return OWNER_TO_MODE[normalized]


def get_go2w_motion_profiles() -> Go2WMotionProfiles:
    common = {
        "leg_joints": LEG_JOINTS,
        "wheel_joints": WHEEL_JOINTS,
        "stand_pose": STAND_POSE,
        "wheels_per_side": 2,
        "wheel_radius_m": 0.10,
        "wheel_separation_m": 0.38,
        "max_linear_velocity_mps": 1.0,
        "max_angular_velocity_rps": 1.5,
        "stand_transition_sec": 2.0,
    }
    return Go2WMotionProfiles(
        wheeled=MotionModeProfile(
            owner="flat",
            mode="wheeled",
            **common,
        ),
        legged=MotionModeProfile(
            owner="stair",
            mode="legged",
            **common,
        ),
    )

