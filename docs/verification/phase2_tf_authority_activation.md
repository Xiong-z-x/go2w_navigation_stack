# Phase 2F TF Authority Activation

## Purpose

This document records the Phase 2F perception TF authority activation dry-run.

Phase 2F adds a repository-local `go2w_perception` TF authority node that
subscribes to the Phase 2E contract odometry topic and publishes the canonical
`odom -> base_link` TF edge.

Phase 2F does not introduce Nav2, mission orchestration, staircase behavior,
route graphs, elevation mapping, or simulator model changes.

## Phase Boundary

Allowed in this task:

- add a local perception TF authority node
- publish `odom -> base_link` from `/go2w/perception/odom`
- add a Phase 2F launch path that composes Phase 2E adapters with the TF node
- verify pre-activation absence of `odom -> base_link`
- verify `diff_drive_controller.enable_odom_tf` remains `False`
- verify patched FAST-LIO still does not publish `camera_init -> body`
- verify FAST-LIO missing-time warnings remain zero

Forbidden in this task:

- modifying Gazebo world, URDF, controller YAML, or sensor declarations
- modifying Nav2, `nav2_route`, mission orchestration, or staircase behavior
- vendoring FAST_LIO_ROS2 source into this repository
- re-enabling FAST-LIO upstream TF publication
- treating this as Nav2 readiness

## Automation

Runtime verifier:

```bash
./tools/verify_phase2f_tf_authority.sh
```

The verifier runs the accepted headless simulation path, starts Phase 2F
perception, launches patched FAST-LIO with `publish.tf_publish_en=false`, and
treats duplicate/forbidden/missing TF authority evidence as hard failures.

## Observed Result

Observed on 2026-04-30.

Unit tests:

```bash
python3 -m pytest go2w_perception/test -q
```

Observed result:

```text
12 passed in 0.20s
```

Scoped build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim
```

Observed result:

```text
Summary: 3 packages finished [0.49s]
```

Static checks:

```bash
bash -n tools/verify_phase2f_tf_authority.sh
shellcheck tools/verify_phase2f_tf_authority.sh
```

Observed result:

```text
no output
```

Runtime verifier:

```bash
./tools/verify_phase2f_tf_authority.sh
```

Observed summary:

```text
required_topic__clock: PASS
required_topic__imu: PASS
required_topic__lidar_points: PASS
diff_drive_enable_odom_tf: False
pre_activation_odom_base_link: ABSENT
perception_process_alive: PASS
adapted_pointcloud_time_field: PASS
fastlio_process_alive: PASS
raw_fastlio_topic_odometry: PASS
raw_fastlio_topic_cloud_registered: PASS
raw_fastlio_topic_laser_map: PASS
contract_odometry_frame: odom
contract_odometry_child_frame: base_link
fastlio_missing_time_warning_count: 0
fastlio_tf_camera_init_body: ABSENT
odom_base_link_authority: PRESENT
phase2f_result: PASS
```

Evidence directory:

```text
/tmp/go2w_phase2f_tf_authority_4308
```

## Current Decision

Phase 2F is complete as a perception TF authority activation dry-run:

- `diff_drive_controller` remains non-authoritative for `odom -> base_link`;
- no `odom -> base_link` TF exists before Phase 2F activation;
- Phase 2F publishes `odom -> base_link` from `/go2w/perception/odom`;
- FAST-LIO upstream `camera_init -> body` TF remains absent;
- FAST-LIO pointcloud timing warnings remain zero.

The next task must stay within Phase 2 perception baseline. It should verify
runtime stability of the activated odometry, TF, point cloud, and map outputs
over a longer motion window before any Nav2 work starts.
