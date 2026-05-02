# Phase 4E Stair Tuning Overrides Verification

## Scope
This document records the opt-in stair tuning smoke test that exercises the
new explicit stair profile override flags without changing the default
baseline.

It verifies that the real-model stair fixture still closes the `/stair_exec`
loop when the stair executor is launched with conservative alternative body
height, foot raise height, gait type, speed level, and velocity limits.

This is not a claim that stair tuning is complete or hardware-validated. It is
only a safe parameter-override smoke test.

## Source Basis
- `go2w_control/go2w_control_runtime/stair_executor.py` now accepts explicit
  overrides for:
  - `--stair-body-height-m`
  - `--stair-foot-raise-height-m`
  - `--stair-gait-type`
  - `--stair-speed-level`
  - `--stair-max-linear-velocity-mps`
  - `--stair-linear-velocity-mps`
- The wrapper script sets conservative override values and delegates to the
  existing stair fixture verifier.

## Verification Run
- Date: `2026-05-02T10:40+08:00`
- Command: `./tools/verify_phase4e_stair_tuning_overrides.sh`
- Evidence directory: `/tmp/go2w_phase4e_stair_fixture_2494`
- Result: `phase4e_stair_tuning_overrides_result: PASS`

## Verified Facts
- The stair executor accepted explicit override arguments.
- The real-model launch still reached active controllers.
- `/stair_exec` was still available and accepted a goal.
- The command gate still observed `flat/wheeled -> stair/legged -> flat/wheeled`.
- The stair executor still emitted the full phase plan and succeeded.

## Result Keys
```text
phase4e_stair_tuning_overrides_result: PASS
```

## Open Validation Items
- The default stair baseline remains unchanged.
- These overrides are still a smoke test, not a physical stair tuning result.
- Future real stair tuning should be validated independently with dedicated
  runtime evidence.
