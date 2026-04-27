# Phase 2B FAST-LIO2 External Dry-Run Design

## Purpose

Phase 2B establishes whether the selected ROS 2 FAST-LIO2 wrapper can be built
and safely dry-run against the current simulation inputs before any perception
TF authority is activated.

This task does not publish `odom -> base_link`, does not change the Gazebo
sensor model, and does not add navigation, mission, or staircase behavior.

## Current Facts

- Active phase: `Phase 2`.
- Phase 2A observed `/lidar_points` fields: `x,y,z,intensity,ring`.
- Phase 2A observed no per-point timing field on `/lidar_points`.
- Current ROS environment exposes `pcl_ros` and `pcl_conversions`.
- Current ROS environment does not expose `fast_lio` or `livox_ros_driver2`.
- `diff_drive_controller` must remain non-authoritative for `odom -> base_link`.

## External FAST-LIO2 Candidate

The current candidate wrapper is the ROS 2 branch of:

- `https://github.com/Ericsii/FAST_LIO_ROS2`

The external source is not vendored into this repository. Phase 2B may clone it
into a temporary or sibling workspace for build inspection, but committed
artifacts stay in this repository as audit scripts and verification records.

## Design

Phase 2B adds a repository-local audit path:

- a small shell tool under `tools/` that inspects an external FAST-LIO2 source
  checkout and the current ROS package environment
- a verification document under `docs/verification/` that records clone,
  dependency, build, and no-TF dry-run results
- a state update that narrows the next task according to the evidence
- a README note that prevents operators from treating FAST-LIO2 as active

The audit tool must answer:

- whether an external FAST-LIO2 source checkout exists
- which commit and branch were inspected
- whether required ROS packages are currently available
- whether the source declares a `livox_ros_driver2` build dependency
- whether the source subscribes to `sensor_msgs/msg/PointCloud2`
- which output topics are hard-coded by the wrapper
- whether the wrapper sends TF internally

## No-TF Dry-Run Gate

The direct runtime dry-run is allowed only if the wrapper can be launched
without publishing TF, or if a controlled patch/wrapper disables TF publication.

If the inspected wrapper has a hard-coded `tf2_ros::TransformBroadcaster` path,
Phase 2B must record the no-TF runtime dry-run as blocked instead of launching
it and creating an untracked TF authority.

## Out Of Scope

- vendoring FAST-LIO2 into this repository
- patching external FAST-LIO2 source inside this task
- installing system-wide Livox SDK components without a separate task boundary
- changing Gazebo world, URDF, controller YAML, or bridge behavior
- activating `odom -> base_link`
- adding Nav2, route graphs, mission orchestration, or staircase behavior
- adding CUDA or ML runtime dependencies

## Validation

Required validation for Phase 2B:

- `git status --short --branch`
- external FAST-LIO2 clone/commit inspection
- external FAST-LIO2 build attempt in a scratch workspace
- `tools/check_phase2_fastlio_external.sh`
- `./tools/verify_go2w_sim_launch.sh`
- `git diff --check`

## Decision Gate

After Phase 2B:

- If FAST-LIO2 builds and can be launched without TF publication, the next task
  may perform a controlled no-TF topic consumption dry-run.
- If the build is blocked by external dependencies, the next task must address
  only that dependency chain.
- If the build succeeds but TF publication is hard-coded, the next task must
  choose a minimal external patch/wrapper strategy before runtime launch.
- If point cloud timing remains incompatible, the next task must choose a
  `go2w_perception` adapter or a verified FAST-LIO2 configuration path.

`odom -> base_link` remains unclaimed in all cases.
