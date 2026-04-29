from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path
from sensor_msgs.msg import PointCloud2


def test_contract_odometry_frames_are_rewritten():
    from go2w_perception.fastlio_frame_contract_adapter import rewrite_odometry_frames

    msg = Odometry()
    msg.header.frame_id = "camera_init"
    msg.child_frame_id = "body"

    rewritten = rewrite_odometry_frames(msg, "camera_init", "body", "odom", "base_link")

    assert rewritten.header.frame_id == "odom"
    assert rewritten.child_frame_id == "base_link"


def test_unexpected_raw_odometry_frame_is_rejected():
    from go2w_perception.fastlio_frame_contract_adapter import rewrite_odometry_frames

    msg = Odometry()
    msg.header.frame_id = "map"
    msg.child_frame_id = "body"

    try:
        rewrite_odometry_frames(msg, "camera_init", "body", "odom", "base_link")
    except ValueError as exc:
        assert "unexpected odometry frame" in str(exc)
    else:
        raise AssertionError("unexpected raw frame was accepted")


def test_path_header_and_pose_frames_are_rewritten():
    from go2w_perception.fastlio_frame_contract_adapter import rewrite_path_frame

    msg = Path()
    msg.header.frame_id = "camera_init"
    pose = PoseStamped()
    pose.header.frame_id = "camera_init"
    msg.poses.append(pose)

    rewritten = rewrite_path_frame(msg, "camera_init", "odom")

    assert rewritten.header.frame_id == "odom"
    assert rewritten.poses[0].header.frame_id == "odom"


def test_cloud_frame_is_rewritten_without_mutating_input():
    from go2w_perception.fastlio_frame_contract_adapter import rewrite_cloud_frame

    msg = PointCloud2()
    msg.header.frame_id = "camera_init"

    rewritten = rewrite_cloud_frame(msg, "odom")

    assert msg.header.frame_id == "camera_init"
    assert rewritten.header.frame_id == "odom"
