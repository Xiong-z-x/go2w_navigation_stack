from nav_msgs.msg import Odometry


def _contract_odometry() -> Odometry:
    msg = Odometry()
    msg.header.stamp.sec = 12
    msg.header.stamp.nanosec = 34
    msg.header.frame_id = "odom"
    msg.child_frame_id = "base_link"
    msg.pose.pose.position.x = 1.0
    msg.pose.pose.position.y = 2.0
    msg.pose.pose.position.z = 3.0
    msg.pose.pose.orientation.x = 0.1
    msg.pose.pose.orientation.y = 0.2
    msg.pose.pose.orientation.z = 0.3
    msg.pose.pose.orientation.w = 0.9
    return msg


def test_odometry_to_transform_preserves_contract_stamp_and_pose():
    from go2w_perception.fastlio_tf_authority import odometry_to_transform

    tf_msg = odometry_to_transform(_contract_odometry(), "odom", "base_link")

    assert tf_msg.header.stamp.sec == 12
    assert tf_msg.header.stamp.nanosec == 34
    assert tf_msg.header.frame_id == "odom"
    assert tf_msg.child_frame_id == "base_link"
    assert tf_msg.transform.translation.x == 1.0
    assert tf_msg.transform.translation.y == 2.0
    assert tf_msg.transform.translation.z == 3.0
    assert tf_msg.transform.rotation.x == 0.1
    assert tf_msg.transform.rotation.y == 0.2
    assert tf_msg.transform.rotation.z == 0.3
    assert tf_msg.transform.rotation.w == 0.9


def test_validate_odometry_contract_rejects_wrong_parent_frame():
    from go2w_perception.fastlio_tf_authority import validate_odometry_contract

    msg = _contract_odometry()
    msg.header.frame_id = "map"

    try:
        validate_odometry_contract(msg, "odom", "base_link")
    except ValueError as exc:
        assert "unexpected odometry frame" in str(exc)
    else:
        raise AssertionError("wrong parent frame was accepted")


def test_validate_odometry_contract_rejects_wrong_child_frame():
    from go2w_perception.fastlio_tf_authority import validate_odometry_contract

    msg = _contract_odometry()
    msg.child_frame_id = "body"

    try:
        validate_odometry_contract(msg, "odom", "base_link")
    except ValueError as exc:
        assert "unexpected odometry frame" in str(exc)
    else:
        raise AssertionError("wrong child frame was accepted")
