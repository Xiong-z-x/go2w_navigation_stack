import pytest

from go2w_mission.mission_api import (
    MissionGoalSpec,
    classify_mission_result,
    validate_mission_goal,
)


def test_validate_mission_goal_accepts_expected_request() -> None:
    spec = MissionGoalSpec(
        start_id=100,
        goal_id=202,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
    )

    validated = validate_mission_goal(spec)

    assert validated.start_id == 100
    assert validated.goal_id == 202
    assert validated.route_frame_id == "map"


def test_validate_mission_goal_rejects_same_start_and_goal() -> None:
    spec = MissionGoalSpec(
        start_id=100,
        goal_id=100,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
    )

    with pytest.raises(ValueError, match="same_start_goal"):
        validate_mission_goal(spec)


def test_mission_result_classification_covers_diagnostics() -> None:
    assert classify_mission_result("SUCCEEDED") == "MISSION_SUCCEEDED"
    assert classify_mission_result("CANCELED") == "MISSION_CANCELED"
    assert classify_mission_result("ROUTE_UNAVAILABLE") == "MISSION_FAILED"
