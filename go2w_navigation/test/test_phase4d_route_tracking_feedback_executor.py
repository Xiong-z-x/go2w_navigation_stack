from go2w_navigation_runtime.route_tracking_feedback_executor import (
    build_feedback_sequence,
)


def test_feedback_sequence_contains_stair_operation() -> None:
    sequence = build_feedback_sequence(include_operation=True)

    assert [sample.current_edge_id for sample in sequence] == [300, 301, 500, 400, 401]
    assert sequence[2].operations_triggered == ("stair_exec",)


def test_feedback_sequence_can_omit_operation_for_failure_gate() -> None:
    sequence = build_feedback_sequence(include_operation=False)

    assert [sample.current_edge_id for sample in sequence] == [300, 301, 500, 400, 401]
    assert sequence[2].operations_triggered == ()
