# Phase 4E Stair Trajectory Outlet Verification

## Scope
This document records the focused stair-executor trajectory outlet slice for
`go2w_control`.

The implementation is intentionally narrow:

- Each stair execution phase now has a deterministic 12-joint target.
- The stair executor publishes the current target to the existing
  `/leg_position_controller/commands` position-command surface.
- The stair executor also publishes a standard
  `trajectory_msgs/msg/JointTrajectory` diagnostic/future-integration surface
  on `/go2w/control/stair_leg_trajectory`.
- State and log diagnostics include `trajectory_joint_count` and
  `trajectory_checksum` for every phase.

This remains a control outlet skeleton. It is not a tuned gait generator,
hardware wheel-lock controller, body-height actuator backend, Unitree SDK2
hardware controller, or physical stair-locomotion proof.

## Implemented Runtime Surface
- `StairExecutionPolicy` still owns the phase plan:
  `prepare,wheel_lock,body_height_transition_down,execute_stairs,body_height_transition_up,release`.
- `build_stair_phase_trajectory_command_data()` returns a 12-value target for
  each phase.
- `build_stair_phase_trajectory_message()` converts the same target to a
  single-point `JointTrajectory` using the Go2W leg joint order.
- `go2w_stair_executor` keeps the current
  `/leg_position_controller/commands` compatible outlet and adds
  `/go2w/control/stair_leg_trajectory`.
- `tools/verify_phase4e_stair_fixture.sh` now checks trajectory diagnostics in
  the real-model stair fixture logs.

## Verification Run
- Date: `2026-05-06`
- Command:

```bash
./tools/verify_phase4e_stair_trajectory_outlet.sh
```

- Result:

```text
16 passed in 0.05s
phase4e_stair_trajectory_outlet_result: PASS
```

## Key Result Lines
```text
stair_trajectory_phase_prepare: trajectory_joint_count=12 trajectory_checksum=-2.520000
stair_trajectory_phase_wheel_lock: trajectory_joint_count=12 trajectory_checksum=-2.520000
stair_trajectory_phase_body_height_transition_down: trajectory_joint_count=12 trajectory_checksum=-2.640000
stair_trajectory_phase_execute_stairs: trajectory_joint_count=12 trajectory_checksum=-2.580000
stair_trajectory_phase_body_height_transition_up: trajectory_joint_count=12 trajectory_checksum=-2.520000
stair_trajectory_phase_release: trajectory_joint_count=12 trajectory_checksum=-2.520000
phase4e_stair_trajectory_outlet_result: PASS
```

## Verified Facts
- All six stair phases produce a 12-joint target.
- `body_height_transition_down` and `execute_stairs` produce distinct target
  summaries when `execute_body_height_m` is configured.
- The `JointTrajectory` message uses the same leg-joint order as the Go2W
  legged motion profile.
- The existing position-command outlet remains available for the current
  `JointGroupPositionController` baseline.

## Package Verification
- `source /opt/ros/humble/setup.bash && PYTHONPATH="$PWD/go2w_control:${PYTHONPATH:-}" python3 -m pytest go2w_control/test/test_stair_executor_policy.py go2w_control/test/test_stair_executor_phases.py -q`
  reported `16 passed`.

## Open Validation Items
- This does not switch the real-model baseline to `joint_trajectory_controller`.
- This does not tune a real stair gait.
- This does not actuate a body-height controller.
- This does not implement hardware wheel lock.
- Runtime real-model fixture evidence must still be collected separately when
  changing timing, controller type, or low-level actuator semantics.
