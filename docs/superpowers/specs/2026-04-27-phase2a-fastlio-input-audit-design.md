# Phase 2A FAST-LIO Input Audit Design

## Purpose

Phase 2A establishes the first perception-stage fact base before integrating
FAST-LIO2. It audits the current simulation sensor outputs, records the
FAST-LIO2 input/output contract, and decides whether an adapter is required.

This design does not launch FAST-LIO2, does not activate `odom -> base_link`,
and does not introduce Nav2, route, mission, or staircase logic.

## Current Constraints

- Active phase: `Phase 2`.
- Only allowed direction: FAST-LIO2 input/output plumbing and later perception
  ownership of `odom -> base_link`.
- Gazebo remains on the accepted software-rendering baseline:
  `use_gpu:=false`.
- RViz may use the already validated process-local WSLg/NVIDIA OpenGL path.
- `diff_drive_controller` must continue not publishing `odom -> base_link`.
- `go2w_perception` is currently scaffold-only and owns FAST-LIO2 integration
  artifacts.

## Design

Phase 2A adds a repository-local audit layer:

- a verification document under `docs/verification/`
- a small ROS 2 topic inspection tool under `tools/`
- an update to `architecture_state.md` after the audit evidence exists
- README notes that point operators to the Phase 2A audit

The audit tool subscribes to the current simulation topics:

- `/lidar_points` as `sensor_msgs/msg/PointCloud2`
- `/imu` as `sensor_msgs/msg/Imu`

It records:

- topic availability
- point cloud frame id
- point cloud width, height, density, and field names
- whether required XYZ fields exist
- whether FAST-LIO-friendly per-point timing fields exist
- IMU frame id and orientation / angular velocity / linear acceleration
  covariance indicators

## Contract Interpretation

FAST-LIO2 needs LiDAR point cloud input and IMU input. For this project, the
minimum Phase 2A question is not whether mapping is already correct; it is
whether the existing simulation outputs can be consumed directly or require a
thin adapter before FAST-LIO2 launch integration.

The expected project-level perception output contract remains:

- odometry baseline for later `odom -> base_link` authority
- registered point cloud baseline
- map / point cloud persistence baseline when FAST-LIO2 is actually running

Phase 2A only decides the input side and records output expectations.

## Out Of Scope

- vendoring FAST-LIO2 source into this repository
- changing Gazebo sensors, URDF, controller YAML, or world assets
- changing `enable_odom_tf`
- publishing any new TF edge
- adding Nav2, `nav2_route`, mission orchestration, or staircase behavior
- adding CUDA/PyTorch/ML runtime dependencies

## Validation

Required validation for Phase 2A:

- `git status --short --branch`
- `./tools/verify_go2w_sim_launch.sh`
- start the accepted simulation path with `use_gpu:=false`
- run the Phase 2A input audit tool against `/lidar_points` and `/imu`
- `colcon build --symlink-install --packages-select go2w_perception`
- `git diff --check`

## Decision Gate

After Phase 2A:

- If `/lidar_points` has FAST-LIO-friendly fields, Phase 2B may create the
  FAST-LIO2 wrapper/config directly.
- If `/lidar_points` lacks per-point timing or compatible fields, Phase 2B
  must first add a minimal `go2w_perception` adapter or explicitly choose a
  FAST-LIO2 configuration that can tolerate the current simulation data.

No later Phase 2 work may claim `odom -> base_link` authority until FAST-LIO2
runtime output is proven stable.
