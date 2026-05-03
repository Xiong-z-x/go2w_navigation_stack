# Phase 4 Runtime Acceptance

## Scope
Phase 4 runtime acceptance records the completed manual-connector cross-floor baseline on the current `main` branch.

It combines the already accepted Phase 4A, Phase 4B-min, Phase 4C-min, and Phase 4D-min runtime gates with the Phase 4 pre-handoff consistency gate, package build, package tests, and final `colcon test-result` verification.

This is not production Mission Orchestrator, real Nav2 route tracking against robot motion, a real `nav2_route` operation plugin, real stair locomotion, real cross-floor autonomy, elevation mapping, traversability, automatic stair detection, automatic connector generation, `map_server`, AMCL, or `map -> odom` localization.

## Implemented Runtime Surface
- `tools/verify_phase4_runtime_acceptance.sh` is the top-level Phase 4 acceptance gate.
- It sequentially verifies:
  - `tools/verify_phase4_pre_handoff.sh`
  - `tools/verify_phase4a_stair_handoff.sh`
  - `tools/verify_phase4b_mission_segments.sh`
  - `tools/verify_phase4c_flat_segment_gate.sh`
  - `tools/verify_phase4d_route_tracking_feedback.sh`
  - `colcon build --symlink-install --packages-select go2w_navigation go2w_control go2w_mission`
  - `colcon test --packages-select go2w_navigation go2w_control go2w_mission`
  - `colcon test-result --verbose`

## Verified Facts
- Phase 4 pre-handoff consistency gate passes on the current accepted baseline.
- Phase 4A stair handoff gate passes.
- Phase 4B-min mission segment gate passes.
- Phase 4C-min flat segment gate passes.
- Phase 4D-min route tracking feedback gate passes.
- Phase 4 phase-related package build passes.
- Phase 4 phase-related package tests pass.
- `colcon test-result --verbose` reported `57 tests, 0 errors, 0 failures, 0 skipped`
  in the original acceptance run and `112 tests, 0 errors, 0 failures, 0 skipped`
  in the 2026-05-04 migration-seal refresh run.

## Verification Evidence
Timestamp: `2026-05-01T12:49+08:00`

Migration-freeze refresh timestamp: `2026-05-02T13:36+08:00`

Migration-seal refresh timestamp: `2026-05-04`

Top-level acceptance gate:

```bash
./tools/verify_phase4_runtime_acceptance.sh
```

Key output:

```text
phase4_runtime_acceptance_result: RUNNING
phase4_pre_handoff_result: PASS
phase4a_stair_handoff_result: PASS
phase4b_mission_segments_result: PASS
phase4c_flat_segment_gate_result: PASS
phase4d_route_tracking_feedback_result: PASS
phase4_packages_build_result: PASS
phase4_packages_test_result: PASS
phase4_test_result_result: PASS
phase4_runtime_acceptance_result: PASS
```

The runtime evidence directory for this run was:

```text
/tmp/go2w_phase4_runtime_acceptance_16465
/tmp/go2w_phase4_runtime_acceptance_4740
/tmp/go2w_phase4_runtime_acceptance_43727
```

Package test summary:

```text
Summary: 3 packages finished [2.04s]
Summary: 57 tests, 0 errors, 0 failures, 0 skipped
Summary: 3 packages finished [4.01s]
Summary: 112 tests, 0 errors, 0 failures, 0 skipped
```

## Reproduction Command
From the repository root:

```bash
./tools/verify_phase4_runtime_acceptance.sh
```

The script chains the pre-handoff consistency gate, the four Phase 4 runtime gates, the package build, the package tests, and the final test-result check.

## Open Validation Items
- Phase 4 accepted still does not mean production Mission Orchestrator.
- Phase 4 accepted still does not mean real robot-motion route tracking.
- Phase 4 accepted still does not mean real stair locomotion, AMCL, `map_server`, elevation mapping, traversability, or automatic connector generation.
