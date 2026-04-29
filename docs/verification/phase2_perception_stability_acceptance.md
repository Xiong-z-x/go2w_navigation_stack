# Phase 2G Perception Runtime Stability Acceptance

## Purpose

This document records the Phase 2G runtime stability acceptance gate for the
activated Phase 2 perception baseline.

Phase 2G verifies that the current headless simulation, Phase 2F perception TF
authority, Phase 2E contract adapters, and patched no-TF FAST-LIO chain can run
through a longer motion-command window while keeping odometry, TF, point cloud,
path, and map outputs alive.

Phase 2G does not introduce Nav2, `nav2_route`, mission orchestration,
staircase behavior, route graphs, elevation mapping, or simulator model
changes.

## Phase Boundary

Allowed in this task:

- add a runtime stability acceptance script
- reuse the accepted Phase 2F perception launch
- reuse patched external FAST-LIO in `/tmp`
- publish bounded `/cmd_vel` commands during the stability window
- sample topic rates and TF after activation
- record runtime evidence for odometry, TF, point cloud, path, and map outputs

Forbidden in this task:

- modifying Gazebo world, URDF, controller YAML, or sensor declarations
- modifying ROS package source code
- modifying Nav2, `nav2_route`, mission orchestration, or staircase behavior
- vendoring FAST_LIO_ROS2 source into this repository
- re-enabling FAST-LIO upstream TF publication
- treating this as route graph or navigation-goal readiness

## Automation

Runtime verifier:

```bash
./tools/verify_phase2g_perception_stability.sh
```

The default stability window is 30 seconds. It can be changed without editing
the repository:

```bash
GO2W_PHASE2G_STABILITY_SECONDS=60 ./tools/verify_phase2g_perception_stability.sh
```

## Observed Result

Observed on 2026-04-30.

Unit tests:

```bash
python3 -m pytest go2w_perception/test -q
```

Observed result:

```text
12 passed in 0.18s
```

Scoped build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim
```

Observed result:

```text
Summary: 3 packages finished [0.38s]
```

Static checks:

```bash
bash -n tools/verify_phase2g_perception_stability.sh
shellcheck tools/verify_phase2g_perception_stability.sh
```

Observed result:

```text
no output
```

Runtime verifier:

```bash
./tools/verify_phase2g_perception_stability.sh
```

Observed summary:

```text
stability_seconds: 30
required_topic__clock: PASS
required_topic__imu: PASS
required_topic__lidar_points: PASS
diff_drive_enable_odom_tf: False
pre_activation_odom_base_link: ABSENT
perception_process_alive: PASS
adapted_pointcloud_time_field: PASS
fastlio_process_alive: PASS
raw_fastlio_topic_odometry: PASS
contract_topic__odom: PASS
contract_topic__path: PASS
contract_topic__cloud_registered: PASS
contract_topic__cloud_body: PASS
contract_topic__laser_map: PASS
contract_odometry_frame: odom
contract_odometry_child_frame: base_link
odom_average_rate: 8.554
tf_average_rate: 25.382
adapted_lidar_average_rate: 8.535
cloud_registered_average_rate: 8.550
sim_process_alive_after_window: PASS
perception_process_alive_after_window: PASS
fastlio_process_alive_after_window: PASS
cmd_vel_publish_count: 131
odom_x_sample: 0.0065944910310534715->0.033913453738000206
fastlio_missing_time_warning_count: 0
perception_contract_error_count: 0
fastlio_runtime_exception_count: 0
fastlio_tf_camera_init_body: ABSENT
odom_base_link_authority: PRESENT
phase2g_result: PASS
```

Evidence directory:

```text
/tmp/go2w_phase2g_perception_stability_5180
```

## Current Decision

Phase 2G is accepted as the runtime stability gate for the current Phase 2
perception baseline:

- headless Fortress simulation remains stable;
- Phase 2F perception TF authority remains active;
- `diff_drive_controller` remains non-authoritative for `odom -> base_link`;
- patched FAST-LIO upstream `camera_init -> body` TF remains absent;
- FAST-LIO missing pointcloud `time` warnings remain zero;
- contract odometry, path, cloud, body cloud, and laser map topics produce
  messages;
- odometry, TF, adapted lidar, and registered cloud topics maintain non-zero
  rates through a 30 second command window.

The next task may begin the first Nav2/costmap consumer gate, but only as a
separate task that consumes the verified perception outputs. It must not yet
introduce route graphs, mission orchestration, staircase behavior, or
multi-floor logic.
