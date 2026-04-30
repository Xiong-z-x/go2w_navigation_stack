from go2w_mission.phase4d_route_tracking_observer import RouteTrackingObservation


def test_observation_detects_stair_edge_and_operation() -> None:
    observation = RouteTrackingObservation(stair_edge_id=500)

    observation.record_feedback(current_edge_id=300, operations=())
    observation.record_feedback(current_edge_id=500, operations=("stair_exec",))

    assert observation.feedback_seen is True
    assert observation.stair_edge_detected is True
    assert observation.operation_triggered == "stair_exec"
    assert observation.final_result(require_operation=True) == "PASS"


def test_observation_reports_missing_operation() -> None:
    observation = RouteTrackingObservation(stair_edge_id=500)

    observation.record_feedback(current_edge_id=500, operations=())

    assert observation.feedback_seen is True
    assert observation.stair_edge_detected is True
    assert observation.final_result(require_operation=True) == "ROUTE_OPERATION_NOT_OBSERVED"


def test_observation_reports_missing_feedback() -> None:
    observation = RouteTrackingObservation(stair_edge_id=500)

    assert observation.final_result(require_operation=True) == "ROUTE_TRACKING_FEEDBACK_MISSING"
