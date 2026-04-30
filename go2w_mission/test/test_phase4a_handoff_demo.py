from go2w_mission.phase4a_handoff_demo import build_stair_goal_spec
from go2w_mission.phase4a_route_graph import RouteEdge


def _stair_edge() -> RouteEdge:
    return RouteEdge(
        edge_id=500,
        start_id=102,
        end_id=200,
        coordinates=[(3.0, 0.0), (6.0, 0.0)],
        properties={
            "mode": "stair",
            "connector_id": "stair_a",
            "floor_from": "F1",
            "floor_to": "F2",
            "stair_exec_required": True,
        },
    )


def test_success_mode_builds_nominal_stair_goal() -> None:
    spec = build_stair_goal_spec(_stair_edge(), mode="success", expected_duration_sec=0.2)

    assert spec.connector_id == "stair_a"
    assert spec.edge_id == 500
    assert spec.direction == "F1_to_F2"
    assert spec.expected_duration_sec == 0.2
    assert spec.force_fail is False
    assert spec.force_timeout is False


def test_failure_mode_sets_force_fail() -> None:
    spec = build_stair_goal_spec(_stair_edge(), mode="failure", expected_duration_sec=0.2)

    assert spec.force_fail is True
    assert spec.force_timeout is False


def test_timeout_and_cancel_modes_extend_stair_execution() -> None:
    timeout_spec = build_stair_goal_spec(_stair_edge(), mode="timeout", expected_duration_sec=0.2)
    cancel_spec = build_stair_goal_spec(_stair_edge(), mode="cancel", expected_duration_sec=0.2)

    assert timeout_spec.force_timeout is True
    assert cancel_spec.force_timeout is True
