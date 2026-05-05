# Phase 4E Stair Phase Target Verification

## Scope
This document records the focused stair-executor phase-target slice for
`go2w_control`.

The current implementation is intentionally narrow:

- The stair phase plan reports whether each phase requires wheel lock.
- The stair executor accepts an opt-in `execute_body_height_m` target.
- `body_height_transition_down` and `execute_stairs` use that execute target
  when explicitly configured.
- `body_height_transition_up` and `release` return to the profile body-height
  target.
- State text exposes `wheel_lock_required=...` and the per-phase body-height
  target for verifier diagnostics.

This is still a diagnostic/control skeleton. It is not a hardware wheel-lock
controller, a body-height actuator backend, tuned gait generation, or physical
stair locomotion.

## Implemented Runtime Surface
- `go2w_control_runtime.stair_executor.StairExecutionPhase` now carries
  `wheel_lock_required`.
- `StairExecutionPolicy(execute_body_height_m=...)` can set the opt-in
  execution body-height target without changing the default legged profile.
- `go2w_stair_executor` accepts `--stair-execute-body-height-m`.
- `tools/verify_phase4e_stair_fixture.sh` passes the optional override and
  verifies phase-target diagnostics in executor logs.
- `tools/verify_phase4e_stair_tuning_overrides.sh` now exercises the override
  in the opt-in stair tuning smoke path.

## Verification Run
- Date: `2026-05-06`
- Command:

```bash
./tools/verify_phase4e_stair_phase_targets.sh
```

- Result:

```text
14 passed in 0.01s
phase4e_stair_phase_targets_result: PASS
```

## Verified Facts
- Default policy still uses the legged motion profile and default stair
  velocity.
- Opt-in `execute_body_height_m` changes only the down-transition and
  execute-stairs phase targets.
- Wheel lock is required for `wheel_lock`, `body_height_transition_down`,
  `execute_stairs`, and `body_height_transition_up`, but not for `prepare` or
  `release`.
- State diagnostics include `wheel_lock_required=...`.

## Package Verification
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_control`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_control`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
  reported `129 tests, 0 errors, 0 failures, 0 skipped`.

## Runtime Smoke
- `./tools/verify_phase4e_stair_tuning_overrides.sh` passed on
  `2026-05-06`.
- Evidence directory: `/tmp/go2w_phase4e_stair_fixture_20324`.
- The runtime override args included
  `--stair-execute-body-height-m 0.29`.

## Key Result Lines
```text
14 passed in 0.01s
phase4e_stair_phase_targets_result: PASS
phase4e_stair_tuning_overrides_result: PASS
```

## Open Validation Items
- This does not actuate a real body-height controller.
- This does not implement real wheel lock torque control.
- This does not tune a hardware stair gait or validate physical stair
  traversal.
