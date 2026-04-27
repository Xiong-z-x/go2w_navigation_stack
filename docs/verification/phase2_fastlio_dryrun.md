# Phase 2B FAST-LIO2 External Dry-Run Gate

## Purpose

This document records the Phase 2B check for building and safely dry-running a
ROS 2 FAST-LIO2 wrapper against the current Go2W simulation inputs.

Phase 2B does not activate `odom -> base_link`.

## Phase Boundary

Allowed in this task:

- clone and inspect external FAST_LIO_ROS2 source outside this repository
- attempt an isolated external build
- inspect whether the wrapper can consume `sensor_msgs/msg/PointCloud2`
- inspect wrapper output topics
- determine whether a no-TF dry-run can be launched safely
- record whether an adapter or external wrapper patch is required

Forbidden in this task:

- changing Gazebo world, URDF, controller YAML, or sensor declarations
- enabling Gazebo GPU rendering
- publishing or claiming `odom -> base_link`
- adding Nav2, `nav2_route`, mission orchestration, or staircase behavior
- vendoring FAST-LIO2 source into this repository

## External Source

Candidate wrapper:

```text
https://github.com/Ericsii/FAST_LIO_ROS2
branch: ros2
```

Reference facts from the upstream README:

- the wrapper expects Livox ROS driver support before FAST-LIO launch/build
- missing per-point `time` is explicitly warned as important for motion
  undistortion

## Required Commands

Initial repository state:

```bash
git status --short --branch
```

Clone external source into scratch space:

```bash
rm -rf /tmp/fast_lio_ros2_probe
git clone --depth 1 --branch ros2 https://github.com/Ericsii/FAST_LIO_ROS2.git /tmp/fast_lio_ros2_probe
```

Run source and dependency audit:

```bash
tools/check_phase2_fastlio_external.sh /tmp/fast_lio_ros2_probe
```

Attempt isolated build:

```bash
rm -rf /tmp/go2w_phase2b_fastlio_ws
mkdir -p /tmp/go2w_phase2b_fastlio_ws/src
ln -s /tmp/fast_lio_ros2_probe /tmp/go2w_phase2b_fastlio_ws/src/FAST_LIO_ROS2
source /opt/ros/humble/setup.bash
cd /tmp/go2w_phase2b_fastlio_ws
colcon build --symlink-install --packages-select fast_lio
```

Verify accepted simulation baseline remains intact:

```bash
./tools/verify_go2w_sim_launch.sh
```

## Observed External Audit

Observed on 2026-04-27.

```text
# Phase 2B FAST-LIO2 External Audit
repo_root: /home/xiongzx/go2w_ws/src/go2w_navigation_stack
fastlio_source_path: /tmp/fast_lio_ros2_probe
fastlio_source_present: true
fastlio_git_remote: https://github.com/Ericsii/FAST_LIO_ROS2.git
fastlio_git_branch: ros2
fastlio_git_commit: 2fffc570a25d0df172720bac034fbdb6a13d2162
ros_package_fast_lio: missing
ros_package_livox_ros_driver2: missing
ros_package_pcl_ros: present
ros_package_pcl_conversions: present
fastlio_project_declared: present
fastlio_executable_declared: present
fastlio_livox_dependency_cmake: present
fastlio_livox_dependency_package: present
fastlio_pointcloud2_subscription: present
fastlio_livox_custom_subscription: present
fastlio_tf_broadcaster_declared: present
fastlio_tf_sendtransform: present
fastlio_tf_parent_camera_init: present
fastlio_tf_child_body: present
fastlio_output_topic_cloud_registered: present
fastlio_output_topic_cloud_registered_body: present
fastlio_output_topic_laser_map: present
fastlio_output_topic_odometry: present
fastlio_no_tf_dryrun_gate: blocked_by_source_tf_broadcaster
audit_status: complete
```

## Observed Build Result

Observed on 2026-04-27.

```text
Starting >>> fast_lio
--- stderr: fast_lio
Current CPU archtecture: x86_64
Processer number:  14
core for MP: 3
CMake Error at CMakeLists.txt:62 (find_package):
  By not providing "Findlivox_ros_driver2.cmake" in CMAKE_MODULE_PATH this
  project has asked CMake to find a package configuration file provided by
  "livox_ros_driver2", but CMake did not find one.

  Could not find a package configuration file provided by "livox_ros_driver2"
  with any of the following names:

    livox_ros_driver2Config.cmake
    livox_ros_driver2-config.cmake

  Add the installation prefix of "livox_ros_driver2" to CMAKE_PREFIX_PATH or
  set "livox_ros_driver2_DIR" to a directory containing one of the above
  files.  If "livox_ros_driver2" provides a separate development package or
  SDK, be sure it has been installed.

---
Failed   <<< fast_lio [3.12s, exited with code 1]

Summary: 0 packages finished [3.47s]
  1 package failed: fast_lio
  1 package had stderr output: fast_lio
```

## No-TF Dry-Run Result

Observed on 2026-04-27.

```text
not_launched
```

Reason:

- the external wrapper build is blocked by missing `livox_ros_driver2`
- the inspected source declares `tf2_ros::TransformBroadcaster` and
  `sendTransform`
- the inspected source has hard-coded TF frames `camera_init -> body`

Launching the wrapper before addressing those facts would violate the Phase 2B
no-TF dry-run boundary.

## Current Decision

Direct FAST-LIO2 runtime dry-run is not yet allowed.

The next task must choose one narrow route:

- close the external dependency chain for `livox_ros_driver2` and required Livox
  SDK components, then patch or wrap FAST-LIO2 so TF publication is disabled for
  no-TF dry-run
- or choose a `go2w_perception` adapter plus a validated FAST-LIO2 config/fork
  strategy that can consume `x,y,z,intensity,ring` without per-point timing

`odom -> base_link` remains unclaimed.

## Repository Baseline Validation

Observed on 2026-04-27.

`go2w_perception` still builds:

```text
Starting >>> go2w_perception
Finished <<< go2w_perception [0.13s]

Summary: 1 package finished [0.49s]
```

Accepted simulation baseline still passes:

```text
[INFO] launch-chain verification summary
gazebo_runtime: ign gazebo-6
joint_state_broadcaster: active
diff_drive_controller: active
clock_message: PASS
imu_message: PASS
lidar_points_message: PASS
```
