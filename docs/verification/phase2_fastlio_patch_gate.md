# Phase 2C FAST-LIO2 Patch Gate

## Purpose

This document records the Phase 2C external patch gate for FAST_LIO_ROS2.

Phase 2C verifies that the selected external wrapper can build without a
mandatory Livox runtime dependency and can keep FAST-LIO TF publication disabled
by default.

Phase 2C does not launch FAST-LIO2 as project runtime and does not activate
`odom -> base_link`.

## Phase Boundary

Allowed in this task:

- acquire external FAST_LIO_ROS2 source in `/tmp`
- apply a repository-local patch to that external source
- verify optional Livox build support
- verify default-disabled FAST-LIO TF publication
- attempt isolated external build
- record next runtime dry-run boundary

Forbidden in this task:

- vendoring FAST_LIO_ROS2 source into this repository
- installing system packages with `sudo`
- changing Gazebo world, URDF, controller YAML, or sensor declarations
- launching FAST-LIO2 against the accepted runtime path
- publishing or claiming `odom -> base_link`
- adding Nav2, `nav2_route`, mission orchestration, or staircase behavior

## External Source Acquisition

Observed on 2026-04-28.

Direct shallow `git clone` of `Ericsii/FAST_LIO_ROS2` stalled during
`index-pack`, so the source was acquired through the GitHub branch archive and
the required `ikd-Tree` submodule was cloned separately.

```bash
rm -rf /tmp/fast_lio_ros2_probe /tmp/FAST_LIO_ROS2-ros2
curl -L --connect-timeout 20 --max-time 180 \
  https://github.com/Ericsii/FAST_LIO_ROS2/archive/refs/heads/ros2.tar.gz \
  | tar -xz -C /tmp
mv /tmp/FAST_LIO_ROS2-ros2 /tmp/fast_lio_ros2_probe
rm -rf /tmp/fast_lio_ros2_probe/include/ikd-Tree
git clone --depth 1 --branch fast_lio \
  https://github.com/hku-mars/ikd-Tree.git \
  /tmp/fast_lio_ros2_probe/include/ikd-Tree
```

Branch heads observed:

```text
FAST_LIO_ROS2 ros2: 2fffc570a25d0df172720bac034fbdb6a13d2162
ikd-Tree fast_lio: e2e3f4e9d3b95a9e66b1ba83dc98d4a05ed8a3c4
```

## Patch Artifact

Repository-local patch:

```text
go2w_perception/patches/fast_lio_ros2/phase2c_no_livox_no_tf.patch
```

Patch apply command:

```bash
tools/apply_phase2c_fastlio_patch.sh /tmp/fast_lio_ros2_probe
```

Observed result:

```text
# Phase 2C FAST-LIO2 Patch Apply
repo_root: /home/xiongzx/go2w_ws/src/go2w_navigation_stack
fastlio_source_path: /tmp/fast_lio_ros2_probe
patch_file: /home/xiongzx/go2w_ws/src/go2w_navigation_stack/go2w_perception/patches/fast_lio_ros2/phase2c_no_livox_no_tf.patch
patching file CMakeLists.txt
patching file package.xml
patching file src/laserMapping.cpp
patching file src/preprocess.cpp
patching file src/preprocess.h
patch_status: applied
```

## Patched Source Audit

Command:

```bash
tools/check_phase2_fastlio_external.sh /tmp/fast_lio_ros2_probe
```

Observed result:

```text
# Phase 2 FAST-LIO2 External Audit
repo_root: /home/xiongzx/go2w_ws/src/go2w_navigation_stack
fastlio_source_path: /tmp/fast_lio_ros2_probe
fastlio_source_present: true
fastlio_git_remote: unknown
fastlio_git_branch: unknown
fastlio_git_commit: unknown
ros_package_fast_lio: missing
ros_package_livox_ros_driver2: missing
ros_package_pcl_ros: present
ros_package_pcl_conversions: present
fastlio_project_declared: present
fastlio_executable_declared: present
fastlio_livox_build_option: present
fastlio_livox_dependency_cmake: optional_gated
fastlio_livox_dependency_package: missing
fastlio_pointcloud2_subscription: present
fastlio_livox_custom_subscription: present
fastlio_ikdtree_submodule_source: present
fastlio_tf_broadcaster_declared: present
fastlio_tf_parent_camera_init: present
fastlio_tf_child_body: present
fastlio_tf_sendtransform: present
fastlio_tf_gate_parameter: present
fastlio_tf_default_disabled: present
fastlio_tf_sendtransform_guard: present
fastlio_no_tf_dryrun_gate: candidate_gated_default_off
fastlio_output_topic_cloud_registered: present
fastlio_output_topic_cloud_registered_body: present
fastlio_output_topic_laser_map: present
fastlio_output_topic_odometry: present
audit_status: complete
```

## Isolated Build

Command:

```bash
rm -rf /tmp/go2w_phase2c_fastlio_ws
mkdir -p /tmp/go2w_phase2c_fastlio_ws/src
ln -s /tmp/fast_lio_ros2_probe /tmp/go2w_phase2c_fastlio_ws/src/FAST_LIO_ROS2
source /opt/ros/humble/setup.bash
cd /tmp/go2w_phase2c_fastlio_ws
colcon build --symlink-install --packages-select fast_lio --cmake-args -DFAST_LIO_ENABLE_LIVOX=OFF
```

Observed result:

```text
Finished <<< fast_lio [49.8s]

Summary: 1 package finished [49.9s]
  1 package had stderr output: fast_lio
```

The stderr output contained CMake developer warnings and a Boost placeholder
deprecation note, but the build exit code was `0`.

Post-build package check:

```bash
source /tmp/go2w_phase2c_fastlio_ws/install/setup.bash
ros2 pkg prefix fast_lio
test -x /tmp/go2w_phase2c_fastlio_ws/install/fast_lio/lib/fast_lio/fastlio_mapping
```

Observed result:

```text
/tmp/go2w_phase2c_fastlio_ws/install/fast_lio
fastlio_mapping_executable: present
```

## Intermediate Blockers Resolved

Phase 2C encountered and resolved two external-source blockers:

- GitHub branch archive does not include the `include/ikd-Tree` submodule
  content; the `ikd-Tree` `fast_lio` branch must be cloned separately.
- The upstream ROS 2 wrapper had a PointCloud2 callback / preprocessing symbol
  mismatch after Livox code was compiled out; the patch now keeps the
  PointCloud2 preprocess path outside the Livox compile guard.

## Current Decision

The Phase 2C build/no-TF gate is cleared:

- `livox_ros_driver2` is no longer required when
  `FAST_LIO_ENABLE_LIVOX=OFF`
- patched FAST_LIO_ROS2 builds in an isolated workspace
- TF send remains present in source but is guarded by
  `publish.tf_publish_en`
- `publish.tf_publish_en` defaults to `false`

`odom -> base_link` remains unclaimed.

## Repository Baseline Validation

Observed on 2026-04-28.

`go2w_perception` still builds:

```text
Starting >>> go2w_perception
Finished <<< go2w_perception [0.07s]

Summary: 1 package finished [0.24s]
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

Whitespace check:

```text
git diff --check: pass
```

## Next Task Boundary

The next allowed Phase 2 task is a controlled Phase 2D no-TF runtime dry-run:

- launch patched external FAST_LIO_ROS2 against current `/lidar_points` and
  `/imu`
- force `publish.tf_publish_en:=false`
- use a non-Livox `preprocess.lidar_type` path
- observe `/Odometry`, `/cloud_registered`, `/cloud_registered_body`,
  `/Laser_map`, and `/path`
- verify no FAST-LIO TF is published
- decide whether missing per-point timing requires a `go2w_perception` adapter

Phase 2D must still not claim `odom -> base_link`.
