# Go2W Control-Chain Regression Verification

## Scope
This document records the stable real-model control-chain regression wrapper.

It verifies the currently repeatable control surfaces:

- real-model controller and stand initialization baseline
- phase-aware `/stair_exec` fixture
- mission checkpoint/resume recovery
- explicit stair tuning override smoke test

This is not a same-floor route-following gate, production Mission Orchestrator,
real stair locomotion tuning, `map_server`, AMCL, elevation mapping,
traversability, or automatic connector generation.

## Verification Run
- Date: `2026-05-02T12:16+08:00`, refreshed during migration-freeze packaging on
  `2026-05-02T13:33+08:00`
- Command: `./tools/verify_go2w_control_chain_regression.sh`
- Result: `go2w_control_chain_regression_result: PASS`

## Evidence Directories
```text
real_model_baseline: /tmp/go2w_real_model_baseline_25485
stair_fixture: /tmp/go2w_phase4e_stair_fixture_26175
mission_recovery: /tmp/go2w_phase4e_mission_recovery_26829
stair_tuning_overrides: /tmp/go2w_phase4e_stair_fixture_27547
refresh_real_model_baseline: /tmp/go2w_real_model_baseline_1978
refresh_stair_fixture: /tmp/go2w_phase4e_stair_fixture_2574
refresh_mission_recovery: /tmp/go2w_phase4e_mission_recovery_3161
refresh_stair_tuning_overrides: /tmp/go2w_phase4e_stair_fixture_3765
```

## Result Keys
```text
go2w_control_chain_regression_result: RUNNING
go2w_real_model_baseline_result: PASS
control_chain_regression_baseline: PASS
phase4e_stair_fixture_result: PASS
control_chain_regression_stair_fixture: PASS
phase4e_mission_recovery_result: PASS
control_chain_regression_mission_recovery: PASS
phase4e_stair_tuning_overrides_result: PASS
control_chain_regression_stair_tuning: PASS
go2w_control_chain_regression_result: PASS
```

## Verified Facts
- `verify_go2w_real_model_baseline.sh` passed and confirmed controller states,
  `diff_drive_controller.enable_odom_tf: false`, leg joints, foot wheel joints,
  required sensor topics, and legged stand initialization.
- `verify_phase4e_stair_fixture.sh` passed and confirmed `/stair_exec`,
  command-gate handoff, phase-aware stair executor state, profile-limited stair
  command, and leg hold/release diagnostics.
- `verify_phase4e_mission_recovery.sh` passed and confirmed a recoverable
  checkpoint after stair executor unavailability, then same-goal resume to
  `MISSION_SUCCEEDED`.
- `verify_phase4e_stair_tuning_overrides.sh` passed with explicit body height,
  foot raise, gait, speed, max velocity, and stair velocity overrides.
- The wrapper intentionally does not call
  `verify_go2w_real_model_route_following.sh`; after dedicated hardening that
  verifier is a repeatable regression candidate, but this wrapper remains the
  conservative migration control-chain gate.

## Open Validation Items
- Same-floor real-model route-following has its own dedicated verifier and
  three clean-domain PASS evidence, but it remains separate from this stable
  control-chain wrapper until a future task explicitly expands the gate.
- This wrapper does not prove production route tracking against robot motion.
- This wrapper does not prove real staircase dynamics or hardware gait tuning.
- The real-model path remains opt-in and does not replace the default
  placeholder simulation baseline.
