# Phase 2E FAST-LIO Contract Stabilization Design

## Task Card

- Task Goal: stabilize the FAST-LIO input/output contract before any TF authority activation by adding a repository-local perception adapter that supplies per-point timing to FAST-LIO and republishes FAST-LIO outputs on project contract topics with project frame IDs.
- Current Phase: `Phase 2`
- Allowed Files: `go2w_perception/CMakeLists.txt`, `go2w_perception/package.xml`, `go2w_perception/go2w_perception/*`, `go2w_perception/scripts/go2w_fastlio_input_adapter`, `go2w_perception/scripts/go2w_fastlio_output_adapter`, `go2w_perception/test/*`, `go2w_perception/config/phase2e_fastlio_contract.yaml`, `go2w_perception/launch/phase2e_fastlio_contract.launch.py`, `tools/verify_phase2e_fastlio_contract.sh`, `docs/superpowers/specs/*phase2e*`, `docs/superpowers/plans/*phase2e*`, `docs/verification/phase2_fastlio_contract_stabilization.md`, `docs/architecture/architecture_state.md`, `README.md`.
- Forbidden Files: `go2w_sim` world/launch/sensor/controller files, `go2w_description` URDF/Xacro/RViz files, `go2w_control`, `go2w_navigation`, `go2w_mission`, `go2w_perception/patches/fast_lio_ros2/*`, vendored FAST_LIO_ROS2 source, Nav2 files, mission orchestration files, staircase executor files.
- Required Commands: `pytest go2w_perception/test`, `colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim`, `shellcheck tools/verify_phase2e_fastlio_contract.sh`, `bash -n tools/verify_phase2e_fastlio_contract.sh`, `./tools/verify_phase2e_fastlio_contract.sh`, `./tools/verify_go2w_sim_launch.sh`, `git diff --check`.
- Definition of Done: FAST-LIO is fed by a pointcloud topic that contains a valid `time` field, the FAST-LIO log has zero `Failed to find match for field 'time'` warnings during the Phase 2E verifier, project contract output topics use `odom` and `base_link` frame IDs, no FAST-LIO TF or `odom -> base_link` TF is published, Phase 1 simulation baseline still passes, and `odom -> base_link` remains unclaimed.

## Context

Phase 2D proved that patched external FAST_LIO_ROS2 can launch against current
simulation input and publish output topics with TF disabled. It also exposed two
blocking contract issues:

- current `/lidar_points` has `x`, `y`, `z`, `intensity`, and `ring`, but no
  per-point `time` field;
- FAST-LIO output messages still use upstream frames
  `camera_init` and `body`.

Phase 2E fixes these contract issues without activating TF authority.

## Brainstormed Approaches

### Option A: Expand the external FAST-LIO patch

Patch FAST_LIO_ROS2 so it tolerates missing `time` and emits project frame IDs.

Trade-off: fewer local nodes, but it deepens dependency on a patched external
wrapper and makes upstream merges harder. It also mixes project contract
adaptation into third-party source.

### Option B: Add a local `go2w_perception` adapter

Keep the external wrapper generic. Add local adapter nodes:

- input adapter: `/lidar_points` -> FAST-LIO input topic with `time` field;
- output adapter: FAST-LIO raw outputs -> project contract topics with
  `odom/base_link` frame IDs.

Trade-off: one local runtime layer is added, but ownership and tests stay inside
the repository. This is the recommended approach.

### Option C: Change the Gazebo sensor output directly

Modify the simulator sensor pipeline to emit timing-ready pointclouds.

Trade-off: this may become useful later, but Phase 2 rules currently forbid
changing simulator sensor declarations. It also risks disturbing the accepted
Phase 1 baseline.

## Decision

Use Option B.

The Phase 2E implementation should create focused Python nodes in
`go2w_perception` because the package is currently scaffold-only and this task
is contract plumbing, not high-rate production optimization.

The adapter must fail closed:

- if incoming pointclouds lack required base fields;
- if generated `time` values are invalid;
- if raw FAST-LIO output frames are not the expected `camera_init/body` pair;
- if any TF edge is published during verification.

## Runtime Contract

### Input Adapter

Default topics:

- subscribe: `/lidar_points`
- publish: `/fastlio/input/lidar_points`

The published `sensor_msgs/msg/PointCloud2` must contain a float32 `time` field.
For simulation, the initial timing model is deterministic:

```text
time = point_index / max(point_count - 1, 1) * scan_period_sec
```

Default `scan_period_sec` is `0.1` for the current 10 Hz simulation baseline.

### Output Adapter

Default raw FAST-LIO topics:

- `/Odometry`
- `/path`
- `/cloud_registered`
- `/cloud_registered_body`
- `/Laser_map`

Default project contract topics:

- `/go2w/perception/odom`
- `/go2w/perception/path`
- `/go2w/perception/cloud_registered`
- `/go2w/perception/cloud_body`
- `/go2w/perception/laser_map`

Frame mapping:

- raw world frame `camera_init` -> contract world frame `odom`
- raw body frame `body` -> contract body frame `base_link`

The output adapter must not publish TF.

## Verification Strategy

The Phase 2E verifier must orchestrate the full no-TF chain:

1. prepare patched external FAST-LIO using the existing Phase 2D script;
2. launch accepted headless `go2w_sim`;
3. launch `go2w_perception` adapters;
4. launch FAST-LIO with `common.lid_topic=/fastlio/input/lidar_points`;
5. assert the adapted pointcloud contains `time`;
6. assert FAST-LIO output topics and contract topics produce messages;
7. assert contract frames are `odom/base_link`;
8. assert the FAST-LIO log does not contain the missing `time` warning;
9. assert `/tf` does not contain `camera_init -> body` or `odom -> base_link`;
10. clean all runtime processes with bounded termination.

## Out of Scope

- Publishing `odom -> base_link` TF.
- Claiming perception TF authority.
- Nav2 or `nav2_route`.
- Mission orchestration.
- Stair execution.
- Gazebo sensor/model changes.
- External FAST-LIO source vendoring.
