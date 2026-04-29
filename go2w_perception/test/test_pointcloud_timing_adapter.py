from sensor_msgs.msg import PointField


def test_compute_relative_times_three_points():
    from go2w_perception.pointcloud_timing_adapter import compute_relative_times

    assert compute_relative_times(3, 0.1) == [0.0, 0.05, 0.1]


def test_compute_relative_times_single_point():
    from go2w_perception.pointcloud_timing_adapter import compute_relative_times

    assert compute_relative_times(1, 0.1) == [0.0]


def test_compute_relative_times_rejects_negative_scan_period():
    from go2w_perception.pointcloud_timing_adapter import compute_relative_times

    try:
        compute_relative_times(3, -0.1)
    except ValueError as exc:
        assert "scan_period_sec must be positive" in str(exc)
    else:
        raise AssertionError("negative scan period was accepted")


def test_fields_with_time_adds_float32_time_after_existing_fields():
    from go2w_perception.pointcloud_timing_adapter import fields_with_time

    fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
        PointField(name="intensity", offset=12, datatype=PointField.FLOAT32, count=1),
        PointField(name="ring", offset=16, datatype=PointField.UINT16, count=1),
    ]

    adapted = fields_with_time(fields, "time")

    assert [field.name for field in adapted] == ["x", "y", "z", "intensity", "ring", "time"]
    assert adapted[-1].offset == 20
    assert adapted[-1].datatype == PointField.FLOAT32


def test_validate_required_fields_rejects_missing_ring():
    from go2w_perception.pointcloud_timing_adapter import validate_required_fields

    fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
        PointField(name="intensity", offset=12, datatype=PointField.FLOAT32, count=1),
    ]

    try:
        validate_required_fields(fields)
    except ValueError as exc:
        assert "missing required point fields: ring" in str(exc)
    else:
        raise AssertionError("missing ring field was accepted")
