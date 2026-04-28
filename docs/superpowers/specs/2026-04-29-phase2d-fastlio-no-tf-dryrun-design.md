# Phase 2D FAST-LIO2 No-TF Runtime Dry-Run Design

## Task Card

- Task Goal: automate the controlled Phase 2D patched FAST_LIO_ROS2 no-TF runtime dry-run against the accepted `go2w_sim` `/lidar_points` and `/imu` streams.
- Current Phase: `Phase 2`
- Allowed Files: `tools/prepare_phase2d_fastlio_external.sh`, `tools/verify_phase2d_fastlio_no_tf_dryrun.sh`, `docs/superpowers/specs/*phase2d*`, `docs/superpowers/plans/*phase2d*`, `docs/verification/phase2_fastlio_no_tf_dryrun.md`, `docs/architecture/architecture_state.md`, `README.md`.
- Forbidden Files: Gazebo world files, URDF/Xacro files, controller YAML, sensor declarations, Nav2 files, mission orchestration files, staircase executor files, vendored FAST_LIO_ROS2 source under this repository.
- Required Commands: `bash -n` for new scripts, `tools/prepare_phase2d_fastlio_external.sh`, `tools/verify_phase2d_fastlio_no_tf_dryrun.sh`, `git diff --check`, and a scoped colcon build/check for touched local packages when needed.
- Definition of Done: external FAST_LIO_ROS2 source can be acquired or reused in `/tmp`, the Phase 2C patch is applied, external `fast_lio` can be built with Livox disabled, the patched node can be launched in a controlled dry-run with `publish.tf_publish_en=false`, evidence records FAST-LIO output-topic observations and absence or presence of forbidden TF, and `odom -> base_link` remains unclaimed.

## Boundary

Phase 2D is a runtime evidence task only. It does not vendor external FAST-LIO2
source, does not change the accepted simulator model, and does not activate
perception TF authority.

The task answers three questions:

- Can the patched external wrapper launch against current `/lidar_points` and
  `/imu` without reintroducing a Livox build dependency?
- Does the no-TF gate hold at runtime when `publish.tf_publish_en=false`?
- Do current simulated pointcloud fields produce usable FAST-LIO output topics,
  or is a `go2w_perception` adapter still required?

## Automation Components

### External Preparation Script

`tools/prepare_phase2d_fastlio_external.sh` owns external source acquisition,
patching, auditing, and isolated external build.

Default scratch paths:

- FAST-LIO source: `/tmp/fast_lio_ros2_probe`
- FAST-LIO workspace: `/tmp/go2w_phase2d_fastlio_ws`

The script prefers reuse when those paths already contain a valid source/build.
Operators can force a refresh with environment variables instead of editing the
repository.

### Runtime Dry-Run Script

`tools/verify_phase2d_fastlio_no_tf_dryrun.sh` owns runtime launch and evidence
collection.

The script:

- prepares the patched external source unless explicitly skipped;
- launches `go2w_sim` with `use_gpu:=false`, `headless:=true`, and
  `launch_rviz:=false`;
- starts `fast_lio/fastlio_mapping` with a temporary no-TF parameter file;
- samples `/Odometry`, `/cloud_registered`, `/cloud_registered_body`,
  `/Laser_map`, and `/path`;
- samples `/tf` and `/tf_static` to check for `camera_init -> body` and
  `odom -> base_link`;
- cleans up all launched processes on exit.

## Runtime Parameters

The dry-run uses a non-Livox Velodyne-style configuration because current
simulation pointclouds contain `x`, `y`, `z`, `intensity`, and `ring`.

The key forced parameters are:

- `common.lid_topic: /lidar_points`
- `common.imu_topic: /imu`
- `preprocess.lidar_type: 2`
- `preprocess.scan_line: 16`
- `publish.tf_publish_en: false`
- `use_sim_time: true`

This is intentionally conservative. If the wrapper requires per-point timing
fields for stable output, the expected Phase 2D result is a recorded adapter
requirement, not an unbounded runtime refactor.

## Failure Semantics

The dry-run script distinguishes infrastructure failures from perception
readiness findings:

- simulator startup, required input topics, external build, or forbidden TF
  presence are hard failures;
- missing FAST-LIO output messages are collected as Phase 2D evidence and
  should drive the next adapter/config decision.

## Out of Scope

- `odom -> base_link` TF publication.
- Nav2 or `nav2_route`.
- Mission orchestration.
- Stair execution.
- Elevation mapping or traversability.
- GPU re-baselining.
