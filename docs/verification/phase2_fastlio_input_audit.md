# Phase 2 FAST-LIO Input Audit

## Purpose

This document records the Phase 2A audit for connecting the current Gazebo
simulation sensor outputs to a future FAST-LIO2 ROS 2 wrapper.

Phase 2A does not run FAST-LIO2 and does not activate `odom -> base_link`.

## Phase Boundary

Allowed in this audit:

- inspect `/lidar_points`
- inspect `/imu`
- document FAST-LIO2 input/output expectations
- decide whether a thin adapter is required before FAST-LIO2 launch integration

Forbidden in this audit:

- changing Gazebo world, URDF, or controller behavior
- enabling Gazebo GPU rendering
- launching FAST-LIO2 as project runtime
- publishing `odom -> base_link`
- adding Nav2, `nav2_route`, mission orchestration, or staircase behavior

## FAST-LIO2 Contract For This Project

Expected input side:

- LiDAR point cloud input from the simulation bridge
- IMU input from the simulation bridge
- consistent timestamps under `/clock`
- sensor frames that can be related to `base_link`

Expected future output side:

- odometry suitable for later `odom -> base_link` authority
- registered point cloud baseline
- map or point cloud persistence baseline

Phase 2A only audits the input side. Output activation is a later Phase 2 task.

## Required Commands

Build or refresh the workspace:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_description go2w_sim go2w_perception
```

Validate the accepted simulation baseline:

```bash
./tools/verify_go2w_sim_launch.sh
```

Start the accepted simulation path for input inspection:

```bash
./tools/cleanup_sim_runtime.sh
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch go2w_sim sim.launch.py use_gpu:=false headless:=true launch_rviz:=false
```

Run the input audit tool in another shell:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
python3 tools/inspect_phase2_fastlio_inputs.py --timeout-sec 20
```

## Observed Input Audit

Observed on 2026-04-27.

```text
# Phase 2 FAST-LIO Input Audit
pointcloud_topic: /lidar_points
imu_topic: /imu
pointcloud_seen: True
pointcloud_frame_id: go2w_placeholder/base_footprint/lidar_sensor
pointcloud_width: 360
pointcloud_height: 16
pointcloud_is_dense: False
pointcloud_point_step: 32
pointcloud_row_step: 11520
pointcloud_fields: x,y,z,intensity,ring
required_xyz_fields_present: True
timing_fields: none
intensity_fields: intensity
ring_fields: ring
imu_seen: True
imu_frame_id: go2w_placeholder/base_footprint/imu_sensor
imu_orientation_covariance: all_zero
imu_angular_velocity_covariance: all_zero
imu_linear_acceleration_covariance: all_zero
fastlio_timing_field_status: missing
fastlio_ring_field_status: present
adapter_recommendation: required_or_config_exception
adapter_reasons: pointcloud lacks per-point timing field
```

## Preliminary Decision Rule

- If `/lidar_points` exposes `x`, `y`, `z`, and a per-point timing field, the
  next task may attempt a direct FAST-LIO2 wrapper/config.
- If `/lidar_points` lacks per-point timing, the next task must either create a
  minimal adapter or explicitly choose a FAST-LIO2 configuration that tolerates
  simulation data without per-point timing.
- If `/lidar_points` lacks `x`, `y`, or `z`, Phase 2 must stop and fix the
  simulation bridge contract before FAST-LIO2 launch work.

## Current Decision

The current `/lidar_points` topic has the required XYZ fields plus `intensity`
and `ring`, but it does not expose a per-point timing field. The next Phase 2
task must not assume a direct FAST-LIO2 launch is sufficient.

The next task must choose one of these two narrow routes:

- create a minimal perception-side adapter that produces FAST-LIO2-compatible
  point cloud timing semantics from the simulation data
- explicitly configure and validate a FAST-LIO2 ROS 2 path that can tolerate
  the current Gazebo `PointCloud2` fields without per-point timing

`odom -> base_link` remains unclaimed.

## Next Task Boundary

After this audit is complete, the next allowed Phase 2 task is one of:

- a validated FAST-LIO2 wrapper/config path that explicitly tolerates
  `/lidar_points` without per-point timing
- a minimal `go2w_perception` adapter that adds the missing compatibility
  semantics before FAST-LIO2 launch integration

Neither option may activate `odom -> base_link` until FAST-LIO2 runtime output
is verified stable.
