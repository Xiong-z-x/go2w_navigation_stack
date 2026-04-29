from __future__ import annotations

from typing import Iterable

import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


def validate_odometry_contract(msg: Odometry, parent_frame: str, child_frame: str) -> None:
    if msg.header.frame_id != parent_frame or msg.child_frame_id != child_frame:
        raise ValueError(f"unexpected odometry frame: {msg.header.frame_id}->{msg.child_frame_id}")


def odometry_to_transform(
    msg: Odometry,
    parent_frame: str,
    child_frame: str,
) -> TransformStamped:
    validate_odometry_contract(msg, parent_frame, child_frame)

    transform = TransformStamped()
    transform.header.stamp = msg.header.stamp
    transform.header.frame_id = parent_frame
    transform.child_frame_id = child_frame
    transform.transform.translation.x = msg.pose.pose.position.x
    transform.transform.translation.y = msg.pose.pose.position.y
    transform.transform.translation.z = msg.pose.pose.position.z
    transform.transform.rotation = msg.pose.pose.orientation
    return transform


class FastlioTfAuthority(Node):
    def __init__(self) -> None:
        super().__init__("go2w_fastlio_tf_authority")

        self.declare_parameter("odometry_topic", "/go2w/perception/odom")
        self.declare_parameter("parent_frame", "odom")
        self.declare_parameter("child_frame", "base_link")

        self._odometry_topic = str(self.get_parameter("odometry_topic").value)
        self._parent_frame = str(self.get_parameter("parent_frame").value)
        self._child_frame = str(self.get_parameter("child_frame").value)
        self._broadcaster = TransformBroadcaster(self)
        self._subscription = self.create_subscription(
            Odometry,
            self._odometry_topic,
            self._on_odometry,
            10,
        )

        self.get_logger().info(
            "FAST-LIO TF authority active: "
            f"{self._odometry_topic} -> {self._parent_frame}->{self._child_frame}"
        )

    def _on_odometry(self, msg: Odometry) -> None:
        try:
            transform = odometry_to_transform(msg, self._parent_frame, self._child_frame)
        except ValueError as exc:
            self.get_logger().error(f"TF authority rejected odometry: {exc}")
            return
        self._broadcaster.sendTransform(transform)


def main(args: Iterable[str] | None = None) -> None:
    rclpy.init(args=args)
    node = FastlioTfAuthority()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
