from go2w_navigation_runtime.flat_nav_executor import FlatNavPolicy


def test_flat_nav_policy_result_code() -> None:
    policy = FlatNavPolicy(min_duration_sec=0.05, timeout_duration_sec=5.0)

    assert policy.result_code(force_fail=False, canceled=False) == "SUCCEEDED"
    assert policy.result_code(force_fail=True, canceled=False) == "FAILED"
    assert policy.result_code(force_fail=False, canceled=True) == "CANCELED"


def test_flat_nav_policy_duration() -> None:
    policy = FlatNavPolicy(min_duration_sec=0.05, timeout_duration_sec=5.0)

    assert policy.execution_duration(0.01, force_timeout=False) == 0.05
    assert policy.execution_duration(0.25, force_timeout=False) == 0.25
    assert policy.execution_duration(0.25, force_timeout=True) == 5.0
