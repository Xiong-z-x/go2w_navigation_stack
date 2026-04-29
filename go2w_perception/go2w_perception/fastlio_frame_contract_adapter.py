from __future__ import annotations

import copy
from typing import Iterable

import rclpy
from nav_msgs.msg import Odometry, Path
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2


def rewrite_odometry_frames(
    msg: Odometry,
    raw_world_frame: str,
    raw_body_frame: str,
    target_world_frame: str,
    target_body_frame: str,
) -> Odometry:
    if msg.header.frame_id != raw_world_frame or msg.child_frame_id != raw_body_frame:
        raise ValueError(f"unexpected odometry frame: {msg.header.frame_id}->{msg.child_frame_id}")
    out = copy.deepcopy(msg)
    out.header.frame_id = target_world_frame
    out.child_frame_id = target_body_frame
    return out


def rewrite_path_frame(msg: Path, raw_world_frame: str, target_world_frame: str) -> Path:
    if msg.header.frame_id != raw_world_frame:
        raise ValueError(f"unexpected path frame: {msg.header.frame_id}")
    out = copy.deepcopy(msg)
    out.header.frame_id = target_world_frame
    for pose in out.poses:
        if pose.header.frame_id and pose.header.frame_id != raw_world_frame:
            raise ValueError(f"unexpected path pose frame: {pose.header.frame_id}")
        pose.header.frame_id = target_world_frame
    return out


def rewrite_cloud_frame(
    msg: PointCloud2,
    target_frame: str,
    raw_frame: str | None = None,
) -> PointCloud2:
    if raw_frame is not None and msg.header.frame_id != raw_frame:
        raise ValueError(f"unexpected cloud frame: {msg.header.frame_id}")
    out = PointCloud2()
    out.header = copy.deepcopy(msg.header)
    out.header.frame_id = target_frame
    out.height = msg.height
    out.width = msg.width
    out.fields = msg.fields
    out.is_bigendian = msg.is_bigendian
    out.point_step = msg.point_step
    out.row_step = msg.row_step
    out.data = msg.data
    out.is_dense = msg.is_dense
    return out


class FastlioFrameContractAdapter(Node):
    def __init__(self) -> None:
        super().__init__("go2w_fastlio_output_adapter")

        self.declare_parameter("raw_world_frame", "camera_init")
        self.declare_parameter("raw_body_frame", "body")
        self.declare_parameter("target_world_frame", "odom")
        self.declare_parameter("target_body_frame", "base_link")
        self.declare_parameter("raw_odometry_topic", "/Odometry")
        self.declare_parameter("raw_path_topic", "/path")
        self.declare_parameter("raw_cloud_registered_topic", "/cloud_registered")
        self.declare_parameter("raw_cloud_body_topic", "/cloud_registered_body")
        self.declare_parameter("raw_laser_map_topic", "/Laser_map")
        self.declare_parameter("contract_odometry_topic", "/go2w/perception/odom")
        self.declare_parameter("contract_path_topic", "/go2w/perception/path")
        self.declare_parameter("contract_cloud_registered_topic", "/go2w/perception/cloud_registered")
        self.declare_parameter("contract_cloud_body_topic", "/go2w/perception/cloud_body")
        self.declare_parameter("contract_laser_map_topic", "/go2w/perception/laser_map")

        self._raw_world_frame = str(self.get_parameter("raw_world_frame").value)
        self._raw_body_frame = str(self.get_parameter("raw_body_frame").value)
        self._target_world_frame = str(self.get_parameter("target_world_frame").value)
        self._target_body_frame = str(self.get_parameter("target_body_frame").value)

        self._odom_pub = self.create_publisher(
            Odometry,
            str(self.get_parameter("contract_odometry_topic").value),
            10,
        )
        self._path_pub = self.create_publisher(
            Path,
            str(self.get_parameter("contract_path_topic").value),
            10,
        )
        self._cloud_registered_pub = self.create_publisher(
            PointCloud2,
            str(self.get_parameter("contract_cloud_registered_topic").value),
            10,
        )
        self._cloud_body_pub = self.create_publisher(
            PointCloud2,
            str(self.get_parameter("contract_cloud_body_topic").value),
            10,
        )
        self._laser_map_pub = self.create_publisher(
            PointCloud2,
            str(self.get_parameter("contract_laser_map_topic").value),
            10,
        )

        self._subscriptions = [
            self.create_subscription(
                Odometry,
                str(self.get_parameter("raw_odometry_topic").value),
                self._on_odometry,
                10,
            ),
            self.create_subscription(
                Path,
                str(self.get_parameter("raw_path_topic").value),
                self._on_path,
                10,
            ),
            self.create_subscription(
                PointCloud2,
                str(self.get_parameter("raw_cloud_registered_topic").value),
                self._on_cloud_registered,
                10,
            ),
            self.create_subscription(
                PointCloud2,
                str(self.get_parameter("raw_cloud_body_topic").value),
                self._on_cloud_body,
                10,
            ),
            self.create_subscription(
                PointCloud2,
                str(self.get_parameter("raw_laser_map_topic").value),
                self._on_laser_map,
                10,
            ),
        ]

        self.get_logger().info(
            "FAST-LIO output contract adapter active: "
            f"{self._raw_world_frame}/{self._raw_body_frame} -> "
            f"{self._target_world_frame}/{self._target_body_frame}"
        )

    def _on_odometry(self, msg: Odometry) -> None:
        try:
            adapted = rewrite_odometry_frames(
                msg,
                self._raw_world_frame,
                self._raw_body_frame,
                self._target_world_frame,
                self._target_body_frame,
            )
        except ValueError as exc:
            self.get_logger().error(f"odometry contract adaptation failed: {exc}")
            return
        self._odom_pub.publish(adapted)

    def _on_path(self, msg: Path) -> None:
        try:
            adapted = rewrite_path_frame(msg, self._raw_world_frame, self._target_world_frame)
        except ValueError as exc:
            self.get_logger().error(f"path contract adaptation failed: {exc}")
            return
        self._path_pub.publish(adapted)

    def _on_cloud_registered(self, msg: PointCloud2) -> None:
        self._publish_cloud(
            msg,
            self._cloud_registered_pub,
            self._target_world_frame,
            self._raw_world_frame,
            "cloud_registered",
        )

    def _on_cloud_body(self, msg: PointCloud2) -> None:
        self._publish_cloud(
            msg,
            self._cloud_body_pub,
            self._target_body_frame,
            self._raw_body_frame,
            "cloud_body",
        )

    def _on_laser_map(self, msg: PointCloud2) -> None:
        self._publish_cloud(
            msg,
            self._laser_map_pub,
            self._target_world_frame,
            self._raw_world_frame,
            "laser_map",
        )

    def _publish_cloud(
        self,
        msg: PointCloud2,
        publisher,
        target_frame: str,
        raw_frame: str,
        label: str,
    ) -> None:
        try:
            adapted = rewrite_cloud_frame(msg, target_frame, raw_frame)
        except ValueError as exc:
            self.get_logger().error(f"{label} contract adaptation failed: {exc}")
            return
        publisher.publish(adapted)


def main(args: Iterable[str] | None = None) -> None:
    rclpy.init(args=args)
    node = FastlioFrameContractAdapter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
