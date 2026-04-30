from go2w_control_runtime.stair_executor import StairExecutionPolicy


def test_success_goal_finishes_with_success_code() -> None:
    policy = StairExecutionPolicy()

    assert policy.result_code(force_fail=False, canceled=False) == "SUCCEEDED"


def test_force_fail_goal_finishes_with_failure_code() -> None:
    policy = StairExecutionPolicy()

    assert policy.result_code(force_fail=True, canceled=False) == "FAILED"


def test_cancel_preempts_failure_code() -> None:
    policy = StairExecutionPolicy()

    assert policy.result_code(force_fail=True, canceled=True) == "CANCELED"


def test_force_timeout_extends_execution_window() -> None:
    policy = StairExecutionPolicy()

    assert policy.execution_duration(0.2, force_timeout=False) == 0.2
    assert policy.execution_duration(0.2, force_timeout=True) >= 5.0
    assert policy.execution_duration(0.0, force_timeout=False) > 0.0
