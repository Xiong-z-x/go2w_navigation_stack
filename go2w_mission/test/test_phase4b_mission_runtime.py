from go2w_mission.phase4b_mission_runtime import (
    build_stair_goal_from_segment,
    final_result_for_timeout,
)
from go2w_mission.phase4b_mission_segments import MissionSegment


def test_build_stair_goal_from_segment_success_mode() -> None:
    spec = build_stair_goal_from_segment(
        MissionSegment(
            segment_type="stair",
            edge_ids=(500,),
            connector_id="stair_a",
            floor_from="F1",
            floor_to="F2",
        ),
        mode="success",
        expected_duration_sec=0.3,
    )

    assert spec.connector_id == "stair_a"
    assert spec.edge_id == 500
    assert spec.direction == "F1_to_F2"
    assert spec.expected_duration_sec == 0.3
    assert spec.force_fail is False
    assert spec.force_timeout is False


def test_build_stair_goal_failure_and_timeout_modes() -> None:
    segment = MissionSegment(
        segment_type="stair",
        edge_ids=(500,),
        connector_id="stair_a",
        floor_from="F1",
        floor_to="F2",
    )

    failure = build_stair_goal_from_segment(segment, mode="failure", expected_duration_sec=0.3)
    timeout = build_stair_goal_from_segment(segment, mode="timeout", expected_duration_sec=0.3)
    cancel = build_stair_goal_from_segment(segment, mode="cancel", expected_duration_sec=0.3)

    assert failure.force_fail is True
    assert failure.force_timeout is False
    assert timeout.force_timeout is True
    assert cancel.force_timeout is True


def test_final_result_for_timeout() -> None:
    assert final_result_for_timeout("timeout") == "MISSION_TIMEOUT"
    assert final_result_for_timeout("success") == "MISSION_FAILED"
