from pathlib import Path
import threading

import pytest

from go2w_mission import mission_api as mission_api_module
from go2w_mission.mission_api import (
    MissionApiRuntime,
    MissionGoalSpec,
    classify_mission_result,
    configure_flat_goal_behavior_tree,
    flat_route_tracking_node_ids,
    normalize_flat_behavior_tree,
    parse_args,
    validate_mission_goal,
)
from go2w_mission.phase4a_route_graph import Phase4ARouteGraph, RouteEdge, RouteNode
from go2w_mission.phase4b_mission_segments import MissionSegment


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


def test_mission_api_route_tracking_action_is_opt_in() -> None:
    args, _ = parse_args(["--graph-file", "graph.geojson"])
    assert args.route_tracking_action == ""

    args, _ = parse_args([
        "--graph-file",
        "graph.geojson",
        "--route-tracking-action",
        "/compute_and_track_route",
    ])
    assert args.route_tracking_action == "/compute_and_track_route"


def test_mission_api_uses_reentrant_downstream_action_callback_group() -> None:
    source = Path(mission_api_module.__file__).read_text(encoding="utf-8")

    assert "ReentrantCallbackGroup" in source
    assert "self.action_client_callback_group = ReentrantCallbackGroup()" in source
    assert "callback_group=self.action_client_callback_group" in source


def test_mission_api_spin_helpers_service_action_client_responses() -> None:
    source = Path(mission_api_module.__file__).read_text(encoding="utf-8")

    assert "rclpy.spin_once(node, timeout_sec=0.05)" in source
    assert "time.sleep(0.05)" not in source


def test_flat_route_tracking_node_ids_use_segment_boundaries() -> None:
    graph = Phase4ARouteGraph(
        nodes={
            100: RouteNode(100, 0.0, 0.0, {}),
            101: RouteNode(101, 1.0, 0.0, {}),
            102: RouteNode(102, 2.0, 0.0, {}),
        },
        edges={
            10: RouteEdge(10, 100, 101, [(0.0, 0.0), (1.0, 0.0)], {}),
            11: RouteEdge(11, 101, 102, [(1.0, 0.0), (2.0, 0.0)], {}),
        },
    )

    assert flat_route_tracking_node_ids(
        graph,
        MissionSegment(segment_type="flat", edge_ids=(10, 11)),
    ) == (100, 102)


def test_mission_api_low_level_mission_lock_guard_is_non_blocking() -> None:
    runtime = object.__new__(MissionApiRuntime)
    runtime._mission_lock = threading.Lock()

    assert runtime._admit_mission_slot() is True
    assert runtime._admit_mission_slot() is False

    runtime._release_mission_slot()

    assert runtime._admit_mission_slot() is True
    runtime._release_mission_slot()


def test_mission_api_flat_pose_conversion_uses_shared_yaw_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_pose_stamped_from_xy_yaw(
        *, frame_id: str, x: float, y: float, yaw: float
    ):
        captured["frame_id"] = frame_id
        captured["x"] = x
        captured["y"] = y
        captured["yaw"] = yaw
        return object()

    monkeypatch.setattr(
        mission_api_module,
        "pose_stamped_from_xy_yaw",
        fake_pose_stamped_from_xy_yaw,
    )

    spec = type(
        "Spec",
        (),
        {
            "frame_id": "map",
            "x": 3.5,
            "y": -1.25,
            "yaw": 1.5,
        },
    )()

    sentinel = mission_api_module._to_pose_stamped(spec)

    assert sentinel is not None
    assert captured == {"frame_id": "map", "x": 3.5, "y": -1.25, "yaw": 1.5}


def test_mission_real_flat_execution_verifier_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_mission_real_flat_execution.sh"
    content = script_path.read_text(encoding="utf-8")

    assert "mission_real_flat_execution_result" in content
    assert "launch_flat_nav_executor:=false" in content
    assert "launch_stair_executor:=false" in content
    assert "flat_behavior_tree:=__empty__" in content
    assert "route_tracking_action:=/compute_and_track_route" in content
    assert "mission_route_tracking_result: PASS" in content
    assert "mission_route_tracking_feedback_edge: 10" in content
    assert "/go2w_flat_nav_executor" in content
