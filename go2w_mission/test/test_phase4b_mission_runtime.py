import math

import pytest

from go2w_mission.mission_pose import yaw_to_quaternion_components
from go2w_mission.phase4b_mission_runtime import (
    FlatGoalSpec,
    build_flat_goal_from_segment,
    build_stair_goal_from_segment,
    final_result_for_flat_timeout,
    final_result_for_timeout,
    _to_pose_stamped,
)
from go2w_mission.phase4a_route_graph import Phase4ARouteGraph, RouteEdge, RouteNode
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


def _flat_graph() -> Phase4ARouteGraph:
    return Phase4ARouteGraph(
        nodes={
            1: RouteNode(node_id=1, x=0.0, y=0.0, properties={"id": 1}),
            2: RouteNode(node_id=2, x=1.0, y=0.0, properties={"id": 2}),
            3: RouteNode(node_id=3, x=2.0, y=0.0, properties={"id": 3}),
        },
        edges={
            10: RouteEdge(
                edge_id=10,
                start_id=1,
                end_id=2,
                coordinates=[(0.0, 0.0), (1.0, 0.0)],
                properties={"id": 10, "startid": 1, "endid": 2},
            ),
            11: RouteEdge(
                edge_id=11,
                start_id=2,
                end_id=3,
                coordinates=[(1.0, 0.0), (2.0, 0.0)],
                properties={"id": 11, "startid": 2, "endid": 3},
            ),
        },
    )


def test_build_flat_goal_from_segment_uses_last_edge_target() -> None:
    goal = build_flat_goal_from_segment(
        _flat_graph(),
        MissionSegment(segment_type="flat", edge_ids=(10, 11)),
        frame_id="map",
    )

    assert goal.frame_id == "map"
    assert goal.x == 2.0
    assert goal.y == 0.0
    assert goal.yaw == 0.0


def test_build_flat_goal_from_segment_prefers_target_yaw_property() -> None:
    graph = Phase4ARouteGraph(
        nodes={
            1: RouteNode(node_id=1, x=0.0, y=0.0, properties={"id": 1}),
            2: RouteNode(node_id=2, x=1.0, y=0.0, properties={"id": 2}),
        },
        edges={
            10: RouteEdge(
                edge_id=10,
                start_id=1,
                end_id=2,
                coordinates=[(0.0, 0.0), (1.0, 0.0)],
                properties={"id": 10, "startid": 1, "endid": 2},
            )
        },
    )
    graph.nodes[2] = RouteNode(
        node_id=2,
        x=1.0,
        y=0.0,
        properties={"id": 2, "yaw": 1.25},
    )

    goal = build_flat_goal_from_segment(
        graph,
        MissionSegment(segment_type="flat", edge_ids=(10,)),
        frame_id="map",
    )

    assert goal.frame_id == "map"
    assert goal.x == 1.0
    assert goal.y == 0.0
    assert goal.yaw == 1.25


def test_flat_timeout_result_mapping() -> None:
    assert final_result_for_flat_timeout("flat_timeout") == "MISSION_TIMEOUT"
    assert final_result_for_flat_timeout("flat_cancel") == "MISSION_FAILED"


def test_yaw_to_quaternion_components_uses_half_angle() -> None:
    z, w = yaw_to_quaternion_components(math.pi)

    assert z == pytest.approx(1.0)
    assert w == pytest.approx(0.0)


def test_flat_pose_conversion_uses_shared_yaw_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_pose_stamped_from_xy_yaw(*, frame_id: str, x: float, y: float, yaw: float):
        captured["frame_id"] = frame_id
        captured["x"] = x
        captured["y"] = y
        captured["yaw"] = yaw
        return object()

    monkeypatch.setattr(
        "go2w_mission.phase4b_mission_runtime.pose_stamped_from_xy_yaw",
        fake_pose_stamped_from_xy_yaw,
    )

    sentinel = _to_pose_stamped(FlatGoalSpec(frame_id="map", x=1.0, y=2.0, yaw=0.75))

    assert sentinel is not None
    assert captured == {"frame_id": "map", "x": 1.0, "y": 2.0, "yaw": 0.75}
