#!/usr/bin/env python3
"""Inspect Phase 2 FAST-LIO candidate inputs from the running simulation."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Sequence

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, PointCloud2


REQUIRED_POINT_FIELDS = ("x", "y", "z")
TIMING_FIELD_CANDIDATES = ("time", "t", "timestamp", "offset_time")
INTENSITY_FIELD_CANDIDATES = ("intensity", "reflectivity")
RING_FIELD_CANDIDATES = ("ring", "line")


@dataclass(frozen=True)
class AuditResult:
    pointcloud_seen: bool
    imu_seen: bool
    missing_required_fields: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return (
            self.pointcloud_seen
            and self.imu_seen
            and not self.missing_required_fields
        )


class FastlioInputInspector(Node):
    def __init__(self, pointcloud_topic: str, imu_topic: str) -> None:
        super().__init__("phase2_fastlio_input_inspector")
        self.pointcloud_topic = pointcloud_topic
        self.imu_topic = imu_topic
        self.pointcloud_msg: PointCloud2 | None = None
        self.imu_msg: Imu | None = None
        self.create_subscription(
            PointCloud2,
            pointcloud_topic,
            self._on_pointcloud,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Imu,
            imu_topic,
            self._on_imu,
            qos_profile_sensor_data,
        )

    def _on_pointcloud(self, msg: PointCloud2) -> None:
        if self.pointcloud_msg is None:
            self.pointcloud_msg = msg

    def _on_imu(self, msg: Imu) -> None:
        if self.imu_msg is None:
            self.imu_msg = msg

    def complete(self) -> bool:
        return self.pointcloud_msg is not None and self.imu_msg is not None


def field_names(msg: PointCloud2 | None) -> tuple[str, ...]:
    if msg is None:
        return ()
    return tuple(field.name for field in msg.fields)


def matching_fields(names: Sequence[str], candidates: Sequence[str]) -> tuple[str, ...]:
    available = set(names)
    return tuple(candidate for candidate in candidates if candidate in available)


def covariance_status(values: Sequence[float]) -> str:
    if len(values) != 9:
        return "invalid"
    if values[0] == -1.0:
        return "not_provided"
    if any(value != 0.0 for value in values):
        return "provided"
    return "all_zero"


def print_report(node: FastlioInputInspector) -> AuditResult:
    pc_msg = node.pointcloud_msg
    imu_msg = node.imu_msg
    names = field_names(pc_msg)
    missing_required = tuple(
        field for field in REQUIRED_POINT_FIELDS if field not in set(names)
    )
    timing_fields = matching_fields(names, TIMING_FIELD_CANDIDATES)
    intensity_fields = matching_fields(names, INTENSITY_FIELD_CANDIDATES)
    ring_fields = matching_fields(names, RING_FIELD_CANDIDATES)

    print("# Phase 2 FAST-LIO Input Audit")
    print(f"pointcloud_topic: {node.pointcloud_topic}")
    print(f"imu_topic: {node.imu_topic}")
    print(f"pointcloud_seen: {pc_msg is not None}")
    if pc_msg is not None:
        print(f"pointcloud_frame_id: {pc_msg.header.frame_id}")
        print(f"pointcloud_width: {pc_msg.width}")
        print(f"pointcloud_height: {pc_msg.height}")
        print(f"pointcloud_is_dense: {pc_msg.is_dense}")
        print(f"pointcloud_point_step: {pc_msg.point_step}")
        print(f"pointcloud_row_step: {pc_msg.row_step}")
        print("pointcloud_fields: " + ",".join(names))
        print("required_xyz_fields_present: " + str(not missing_required))
        print("timing_fields: " + (",".join(timing_fields) if timing_fields else "none"))
        print(
            "intensity_fields: "
            + (",".join(intensity_fields) if intensity_fields else "none")
        )
        print("ring_fields: " + (",".join(ring_fields) if ring_fields else "none"))
    else:
        print("pointcloud_frame_id: none")
        print("pointcloud_fields: none")
        print("required_xyz_fields_present: false")
        print("timing_fields: none")
        print("intensity_fields: none")
        print("ring_fields: none")

    print(f"imu_seen: {imu_msg is not None}")
    if imu_msg is not None:
        print(f"imu_frame_id: {imu_msg.header.frame_id}")
        print(
            "imu_orientation_covariance: "
            + covariance_status(imu_msg.orientation_covariance)
        )
        print(
            "imu_angular_velocity_covariance: "
            + covariance_status(imu_msg.angular_velocity_covariance)
        )
        print(
            "imu_linear_acceleration_covariance: "
            + covariance_status(imu_msg.linear_acceleration_covariance)
        )
    else:
        print("imu_frame_id: none")
        print("imu_orientation_covariance: none")
        print("imu_angular_velocity_covariance: none")
        print("imu_linear_acceleration_covariance: none")

    adapter_reasons = []
    if timing_fields:
        timing_status = "present"
    else:
        timing_status = "missing"
        adapter_reasons.append("pointcloud lacks per-point timing field")
    if not intensity_fields:
        adapter_reasons.append("pointcloud lacks intensity-like field")
    if ring_fields:
        ring_status = "present"
    else:
        ring_status = "missing"

    print(f"fastlio_timing_field_status: {timing_status}")
    print(f"fastlio_ring_field_status: {ring_status}")
    if adapter_reasons:
        print("adapter_recommendation: required_or_config_exception")
        print("adapter_reasons: " + "; ".join(adapter_reasons))
    else:
        print("adapter_recommendation: direct_wrapper_candidate")
        print("adapter_reasons: none")

    return AuditResult(
        pointcloud_seen=pc_msg is not None,
        imu_seen=imu_msg is not None,
        missing_required_fields=missing_required,
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect current simulation topics for Phase 2 FAST-LIO input planning.",
    )
    parser.add_argument("--pointcloud-topic", default="/lidar_points")
    parser.add_argument("--imu-topic", default="/imu")
    parser.add_argument("--timeout-sec", type=float, default=20.0)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    rclpy.init()
    node = FastlioInputInspector(args.pointcloud_topic, args.imu_topic)
    deadline = time.monotonic() + args.timeout_sec
    try:
        while time.monotonic() < deadline and not node.complete():
            rclpy.spin_once(node, timeout_sec=0.1)
        result = print_report(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    if not result.pointcloud_seen or not result.imu_seen:
        return 2
    if result.missing_required_fields:
        print(
            "missing_required_fields: "
            + ",".join(result.missing_required_fields),
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
