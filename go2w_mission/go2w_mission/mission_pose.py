from __future__ import annotations

import math


def yaw_to_quaternion_components(yaw: float) -> tuple[float, float]:
    half_yaw = float(yaw) * 0.5
    return math.sin(half_yaw), math.cos(half_yaw)


def pose_stamped_from_xy_yaw(
    *,
    frame_id: str,
    x: float,
    y: float,
    yaw: float,
):
    from geometry_msgs.msg import PoseStamped, Quaternion

    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    z, w = yaw_to_quaternion_components(yaw)
    pose.pose.orientation = Quaternion(z=z, w=w)
    return pose
