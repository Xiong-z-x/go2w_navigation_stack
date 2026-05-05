from go2w_control_runtime.stair_executor import StairExecutionPolicy


def test_force_timeout_extends_phase_plan_total_duration() -> None:
    policy = StairExecutionPolicy()

    normal_plan = policy.build_phase_plan(0.2, force_timeout=False)
    timeout_plan = policy.build_phase_plan(0.2, force_timeout=True)

    assert timeout_plan.total_duration_sec >= normal_plan.total_duration_sec
    assert timeout_plan.phase_names() == normal_plan.phase_names()


def test_phase_plan_uses_legged_profile_metadata() -> None:
    policy = StairExecutionPolicy()
    plan = policy.build_phase_plan(0.3, force_timeout=False)

    for phase in plan.phases:
        assert phase.body_height_m == policy.profile.body_height_m
        assert phase.foot_raise_height_m == policy.profile.foot_raise_height_m


def test_policy_accepts_explicit_stair_tuning_overrides() -> None:
    policy = StairExecutionPolicy(
        body_height_m=0.31,
        execute_body_height_m=0.29,
        foot_raise_height_m=0.08,
        gait_type=3,
        speed_level=1,
        max_linear_velocity_mps=0.12,
        stair_linear_velocity_mps=0.03,
    )

    assert policy.profile.body_height_m == 0.31
    assert policy.execute_body_height_m == 0.29
    assert policy.profile.foot_raise_height_m == 0.08
    assert policy.profile.gait_type == 3
    assert policy.profile.speed_level == 1
    assert policy.profile.max_linear_velocity_mps == 0.12
    assert policy.stair_linear_velocity_mps == 0.03
