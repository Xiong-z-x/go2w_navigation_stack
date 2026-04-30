from __future__ import annotations

from typing import Iterable, Sequence

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2

REQUIRED_POINT_FIELDS = ("x", "y", "z", "intensity", "ring")

_POINT_FIELD_SIZES = {
    PointField.INT8: 1,
    PointField.UINT8: 1,
    PointField.INT16: 2,
    PointField.UINT16: 2,
    PointField.INT32: 4,
    PointField.UINT32: 4,
    PointField.FLOAT32: 4,
    PointField.FLOAT64: 8,
}


def compute_relative_times(point_count: int, scan_period_sec: float) -> list[float]:
    if point_count < 0:
        raise ValueError("point_count must be non-negative")
    if scan_period_sec <= 0.0:
        raise ValueError("scan_period_sec must be positive")
    if point_count == 0:
        return []
    if point_count == 1:
        return [0.0]
    step = scan_period_sec / float(point_count - 1)
    return [float(index) * step for index in range(point_count)]


def validate_required_fields(fields: Sequence[PointField]) -> None:
    present = {field.name for field in fields}
    missing = [field_name for field_name in REQUIRED_POINT_FIELDS if field_name not in present]
    if missing:
        raise ValueError(f"missing required point fields: {', '.join(missing)}")


def _copy_field(field: PointField) -> PointField:
    copied = PointField()
    copied.name = field.name
    copied.offset = field.offset
    copied.datatype = field.datatype
    copied.count = field.count
    return copied


def _field_size(field: PointField) -> int:
    try:
        datatype_size = _POINT_FIELD_SIZES[field.datatype]
    except KeyError as exc:
        raise ValueError(
            f"unsupported point field datatype for {field.name}: {field.datatype}"
        ) from exc
    return datatype_size * max(field.count, 1)


def _align_to_four_bytes(offset: int) -> int:
    remainder = offset % 4
    if remainder == 0:
        return offset
    return offset + (4 - remainder)


def fields_with_time(fields: Sequence[PointField], time_field_name: str) -> list[PointField]:
    if not time_field_name:
        raise ValueError("time_field_name must be non-empty")

    copied_fields = [_copy_field(field) for field in fields if field.name != time_field_name]
    next_offset = 0
    for field in copied_fields:
        next_offset = max(next_offset, field.offset + _field_size(field))

    time_field = PointField()
    time_field.name = time_field_name
    time_field.offset = _align_to_four_bytes(next_offset)
    time_field.datatype = PointField.FLOAT32
    time_field.count = 1
    copied_fields.append(time_field)
    return copied_fields


def _to_python_scalar(value):
    if hasattr(value, "item"):
        return value.item()
    return value


def pointcloud_with_time(
    msg: PointCloud2,
    scan_period_sec: float,
    time_field_name: str = "time",
    force_recompute_time: bool = True,
) -> PointCloud2:
    validate_required_fields(msg.fields)

    existing_names = [field.name for field in msg.fields]
    if time_field_name in existing_names and not force_recompute_time:
        return msg

    source_fields = [field for field in msg.fields if field.name != time_field_name]
    source_names = [field.name for field in source_fields]
    adapted_fields = fields_with_time(msg.fields, time_field_name)

    points_array = point_cloud2.read_points(msg, field_names=source_names, skip_nans=False)
    relative_times = compute_relative_times(len(points_array), scan_period_sec)

    adapted_points = []
    for point, relative_time in zip(points_array, relative_times):
        values = [_to_python_scalar(point[field_name]) for field_name in source_names]
        values.append(relative_time)
        adapted_points.append(tuple(values))

    adapted = point_cloud2.create_cloud(msg.header, adapted_fields, adapted_points)
    adapted.height = msg.height
    adapted.width = msg.width
    adapted.is_dense = msg.is_dense
    adapted.row_step = adapted.point_step * adapted.width
    return adapted


class PointCloudTimingAdapter(Node):
    def __init__(self) -> None:
        super().__init__("go2w_fastlio_input_adapter")

        self.declare_parameter("input_topic", "/lidar_points")
        self.declare_parameter("output_topic", "/fastlio/input/lidar_points")
        self.declare_parameter("scan_period_sec", 0.1)
        self.declare_parameter("time_field_name", "time")
        self.declare_parameter("force_recompute_time", True)

        self._scan_period_sec = float(self.get_parameter("scan_period_sec").value)
        self._time_field_name = str(self.get_parameter("time_field_name").value)
        self._force_recompute_time = bool(self.get_parameter("force_recompute_time").value)
        input_topic = str(self.get_parameter("input_topic").value)
        output_topic = str(self.get_parameter("output_topic").value)

        self._publisher = self.create_publisher(PointCloud2, output_topic, qos_profile_sensor_data)
        self._subscription = self.create_subscription(
            PointCloud2,
            input_topic,
            self._on_pointcloud,
            qos_profile_sensor_data,
        )
        self.get_logger().info(
            f"FAST-LIO input adapter active: {input_topic} -> {output_topic}, "
            f"time_field={self._time_field_name}"
        )

    def _on_pointcloud(self, msg: PointCloud2) -> None:
        try:
            adapted = pointcloud_with_time(
                msg,
                self._scan_period_sec,
                self._time_field_name,
                self._force_recompute_time,
            )
        except ValueError as exc:
            self.get_logger().error(f"pointcloud timing adaptation failed: {exc}")
            return
        self._publisher.publish(adapted)


def main(args: Iterable[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PointCloudTimingAdapter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
