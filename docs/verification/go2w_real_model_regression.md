# Go2W Real Model Opt-In Regression Verification

## Scope
This document records the post-Phase-4 real-model regression policy and
verification wrapper.

The accepted policy is to expand the real-model path into a broader opt-in
regression wrapper. The default `go2w_sim sim.launch.py` placeholder path is
not replaced by the real-model path in this task.

## Source Basis
The wrapper composes three replayable gates:

1. `tools/verify_go2w_real_model_baseline.sh`
2. `tools/verify_go2w_real_model_route_following.sh`
3. `tools/verify_phase4e_stair_fixture.sh`

The wrapper is:

```bash
tools/verify_go2w_real_model_regression.sh
```

## Verification Run
- Date: `2026-05-02T03:39+08:00`
- Command: `GO2W_REAL_ROUTE_REBUILD_REPO=0 ./tools/verify_go2w_real_model_regression.sh`
- Baseline evidence directory: `/tmp/go2w_real_model_baseline_14871`
- Route-following evidence directory: `/tmp/go2w_real_model_route_following_15518`
- Stair fixture evidence directory: `/tmp/go2w_phase4e_stair_fixture_16665`
- Result: `go2w_real_model_regression_result: PASS`

## Verified Facts
- The real-model baseline gate passed:
  - real Go2W URDF/assets loaded through the opt-in launch path;
  - `joint_state_broadcaster`, `leg_position_controller`, and
    `diff_drive_controller` reached `active`;
  - `/clock`, `/imu`, `/lidar_points`, and `/joint_states` published;
  - startup stand initializer logged and published the selected `legged`
    profile.
- The real-model same-floor route-following gate passed:
  - Nav2 lifecycle reached active;
  - a short `NavigateToPose` goal returned `SUCCEEDED`;
  - `/cmd_vel` was nonzero during execution;
  - perception odometry and diff-drive odometry changed;
  - `odom -> base_link` remained perception-owned.
- The real-model stair fixture gate passed:
  - `/stair_exec` action was available;
  - `flat/wheeled -> stair/legged -> flat/wheeled` ownership was observed;
  - all stair executor phases were observed;
  - the goal returned `SUCCEEDED`.

## Result Keys
```text
go2w_real_model_baseline_result: PASS
real_model_regression_baseline: PASS
go2w_real_model_route_following_result: PASS
real_model_regression_route_following: PASS
phase4e_stair_fixture_result: PASS
real_model_regression_stair_fixture: PASS
go2w_real_model_regression_result: PASS
```

## Dependency Note
In the isolated worktree used for this run, the first wrapper attempt found the
FAST-LIO external setup missing under `.go2w_external/workspaces/fast_lio_ros2`.
The dependency was prepared with:

```bash
./tools/prepare_phase2d_fastlio_external.sh
```

The preparation completed with `fastlio_build_status: PASS` and
`prepare_status: complete`, after which the wrapper passed with
`GO2W_REAL_ROUTE_REBUILD_REPO=0`.

## Open Validation Items
- The real-model path remains opt-in.
- This wrapper is broader than the earlier baseline, but it is still not a
  replacement for all historical placeholder-world Phase 1-5 gates.
- The stair fixture remains a phase-aware skeleton and does not prove physical
  stair traversal.
- No default launch re-baseline was performed.
