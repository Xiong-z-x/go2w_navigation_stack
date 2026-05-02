from pathlib import Path
import threading

import pytest

from go2w_mission.mission_api import (
    MissionApiRuntime,
    MissionGoalSpec,
    classify_mission_result,
    configure_flat_goal_behavior_tree,
    normalize_flat_behavior_tree,
    parse_args,
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


def test_flat_behavior_tree_can_be_disabled_for_real_nav2() -> None:
    class Goal:
        behavior_tree = "unset"

    goal = Goal()
    configure_flat_goal_behavior_tree(goal, "")
    assert goal.behavior_tree == ""

    configure_flat_goal_behavior_tree(goal, "success")
    assert goal.behavior_tree == "success"

    configure_flat_goal_behavior_tree(goal, "__empty__")
    assert goal.behavior_tree == ""


def test_mission_api_accepts_empty_flat_behavior_tree_argument() -> None:
    args, _ = parse_args(["--graph-file", "graph.geojson", "--flat-behavior-tree", ""])
    assert args.flat_behavior_tree == ""
    assert normalize_flat_behavior_tree("__empty__") == ""


def test_mission_api_single_flight_admission_gate_is_non_blocking() -> None:
    runtime = object.__new__(MissionApiRuntime)
    runtime._mission_lock = threading.Lock()

    assert runtime._admit_mission_slot() is True
    assert runtime._admit_mission_slot() is False

    runtime._release_mission_slot()

    assert runtime._admit_mission_slot() is True
    runtime._release_mission_slot()


def test_mission_real_flat_execution_verifier_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_mission_real_flat_execution.sh"
    content = script_path.read_text(encoding="utf-8")

    assert "mission_real_flat_execution_result" in content
    assert "launch_flat_nav_executor:=false" in content
    assert "launch_stair_executor:=false" in content
    assert "flat_behavior_tree:=__empty__" in content
    assert "/go2w_flat_nav_executor" in content
