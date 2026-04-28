# Phase 2C FAST-LIO2 Patch Gate Design

## Purpose

Phase 2C establishes a reproducible external patch gate for the selected
FAST_LIO_ROS2 wrapper before any runtime launch or TF authority activation.

The goal is to prove whether the wrapper can be built for the current
simulation-first path with:

- Livox message support disabled unless explicitly enabled
- FAST-LIO TF publication disabled by default
- no `odom -> base_link` publication

This task does not run FAST-LIO2 as project runtime and does not activate
perception odometry authority.

## Current Facts

- Active phase: `Phase 2`.
- Phase 2A observed `/lidar_points` fields: `x,y,z,intensity,ring`.
- Phase 2A observed no per-point timing field.
- Phase 2B found the current candidate wrapper requires
  `livox_ros_driver2` at build time.
- Phase 2B found hard-coded TF publication from `camera_init` to `body`.
- `diff_drive_controller` remains non-authoritative for `odom -> base_link`.

## Recommended Route

Use an external patch route, not a vendored source route.

Committed repository artifacts may include:

- patch files under `go2w_perception/patches/`
- tools that fetch/apply/build-check external FAST_LIO_ROS2 in `/tmp`
- verification records under `docs/verification/`

Committed repository artifacts must not include:

- FAST_LIO_ROS2 source code
- Livox SDK source code
- generated build/install/log artifacts
- runtime launch files that activate FAST-LIO2 odometry authority

## Patch Scope

The Phase 2C patch must be minimal and auditable:

- make `livox_ros_driver2` an optional build path controlled by a CMake option
- compile the PointCloud2 path without Livox message headers
- disable TF publication by default through a ROS parameter such as
  `publish.tf_publish_en`
- preserve odometry topic publication for later no-TF dry-run validation
- preserve original FAST-LIO2 output topic names for audit visibility

The patch may leave runtime data-shape compatibility unresolved. The missing
per-point timing field is a separate Phase 2D decision unless the build/no-TF
gate proves that it must be handled earlier.

## No-TF Gate

The wrapper is considered no-TF build-gate ready only if all are true:

- external patched source builds successfully in an isolated workspace
- `livox_ros_driver2` is not required when Livox support is disabled
- the source contains an explicit TF publication gate
- default configuration keeps TF publication disabled
- the project does not launch FAST-LIO2 during this task

## Out Of Scope

- installing system dependencies with `sudo`
- making Gazebo publish a different point cloud schema
- implementing a `go2w_perception` runtime adapter
- adding a FAST-LIO launch entrypoint to the accepted runtime path
- activating `odom -> base_link`
- modifying Nav2, route graph, mission orchestration, stair logic, URDF,
  controller YAML, or Gazebo world assets

## Validation

Required validation:

- `git status --short --branch`
- external source acquisition into `/tmp`
- patch apply check against the external source
- isolated `colcon build --symlink-install --packages-select fast_lio`
- source audit proving optional Livox and gated TF state
- `colcon build --symlink-install --packages-select go2w_perception`
- `./tools/verify_go2w_sim_launch.sh`
- `git diff --check`

## Decision Gate

After Phase 2C:

- If patched FAST_LIO_ROS2 builds and no-TF gate is confirmed, Phase 2D may
  create a controlled no-TF runtime dry-run using current `/lidar_points` and
  `/imu`.
- If build still fails, Phase 2D must address only the remaining build blocker.
- If build succeeds but data-shape compatibility fails later, Phase 2D must
  choose between a minimal `go2w_perception` adapter and a FAST-LIO2 config/fork
  adjustment.

`odom -> base_link` remains unclaimed in all cases.
