# Phase 2 Runtime Acceptance

## Purpose

This document records the final Phase 2 acceptance state for the Go2W
simulation-first navigation stack.

Phase 2 covers FAST-LIO2 input/output plumbing, perception-side
`odom -> base_link` TF authority activation, stable odometry / point cloud /
map baseline output, and the first Nav2 costmap consumer gate.

## Accepted Gates

- Phase 2A input audit:
  `docs/verification/phase2_fastlio_input_audit.md`
- Phase 2B external FAST-LIO dry-run gate:
  `docs/verification/phase2_fastlio_dryrun.md`
- Phase 2C external patch gate:
  `docs/verification/phase2_fastlio_patch_gate.md`
- Phase 2D no-TF runtime dry-run:
  `docs/verification/phase2_fastlio_no_tf_dryrun.md`
- Phase 2E FAST-LIO contract stabilization:
  `docs/verification/phase2_fastlio_contract_stabilization.md`
- Phase 2F perception TF authority activation:
  `docs/verification/phase2_tf_authority_activation.md`
- Phase 2G perception runtime stability:
  `docs/verification/phase2_perception_stability_acceptance.md`
- Phase 2H Nav2 costmap consumer gate:
  `docs/verification/phase2_costmap_consumer_gate.md`

## Final Accepted Contract

- Simulation baseline remains ROS 2 Humble + Gazebo Fortress-only.
- Gazebo rendering remains software baseline with `use_gpu:=false`.
- `/lidar_points` is adapted to `/fastlio/input/lidar_points` with a `time`
  field.
- Patched FAST-LIO consumes `/fastlio/input/lidar_points` and `/imu`.
- Raw FAST-LIO outputs are republished on project contract topics:
  `/go2w/perception/odom`, `/go2w/perception/path`,
  `/go2w/perception/cloud_registered`, `/go2w/perception/cloud_body`, and
  `/go2w/perception/laser_map`.
- Contract odometry uses `odom -> base_link` message semantics.
- Perception publishes the `odom -> base_link` TF edge.
- `diff_drive_controller` remains non-authoritative for `odom -> base_link`.
- FAST-LIO upstream `camera_init -> body` TF remains disabled.
- A standalone Nav2 costmap consumes `/go2w/perception/cloud_body` and
  publishes `/costmap/costmap` in `odom`.

## Final Verification Command

```bash
./tools/verify_phase2h_costmap_consumer.sh
```

Observed on 2026-04-30:

```text
phase2h_result: PASS
```

Evidence directory:

```text
/tmp/go2w_phase2h_costmap_consumer_13828
```

## Current Decision

Phase 2 is accepted as complete on the current `main` baseline.

The next phase may start only as Phase 3 work. Phase 3 must still be split into
explicit task cards and must not bundle same-floor navigation, `nav2_route`,
route graph authoring, mission orchestration, staircase behavior, and
multi-floor logic into one task.
