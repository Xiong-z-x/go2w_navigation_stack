# Phase 2H Nav2 Costmap Consumer Gate

## Purpose

This document records the Phase 2H acceptance gate for the first Nav2 consumer
of the Phase 2 perception baseline.

Phase 2H verifies that a minimal standalone Nav2 local costmap can consume the
verified FAST-LIO perception contract output while preserving all frozen Phase 2
boundaries.

## Phase Boundary

Allowed in this task:

- add `go2w_navigation` standalone costmap config and launch assets
- consume `/go2w/perception/cloud_body` as a PointCloud2 observation source
- use the activated `odom -> base_link` perception TF authority
- record costmap lifecycle, subscription, topic, and frame evidence
- verify the Humble standalone `nav2_costmap_2d` node as `/costmap/costmap`

Forbidden in this task:

- enabling planner, controller, BT Navigator, waypoint follower, smoother, or
  recovery behavior servers
- enabling `nav2_route` or authoring route graphs
- modifying mission orchestration or staircase execution logic
- modifying Gazebo, URDF, controller, or perception algorithm assets
- adding elevation, traversability, or multi-floor behavior

## Automation

Runtime verifier:

```bash
./tools/verify_phase2h_costmap_consumer.sh
```

The default costmap observation window is 20 seconds. It can be changed without
editing the repository:

```bash
GO2W_PHASE2H_WINDOW_SECONDS=30 ./tools/verify_phase2h_costmap_consumer.sh
```

## Observed Result

Observed on 2026-04-30.

Unit regression:

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
colcon build --symlink-install --packages-select go2w_navigation go2w_perception go2w_description go2w_sim
```

Observed result:

```text
Summary: 4 packages finished [0.41s]
```

Static checks:

```bash
bash -n tools/verify_phase2h_costmap_consumer.sh
shellcheck tools/verify_phase2h_costmap_consumer.sh
git diff --check
```

Observed result:

```text
no output
```

Navigation package test harness:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --cmake-clean-cache --packages-select go2w_navigation
colcon test --packages-select go2w_navigation --event-handlers console_direct+
```

Observed result:

```text
Summary: 1 package finished [0.17s]
```

Runtime verifier:

```bash
./tools/verify_phase2h_costmap_consumer.sh
```

Observed summary:

```text
window_seconds: 20
required_topic__clock: PASS
required_topic__imu: PASS
required_topic__lidar_points: PASS
diff_drive_enable_odom_tf: False
pre_activation_odom_base_link: ABSENT
perception_process_alive: PASS
adapted_pointcloud_time_field: PASS
fastlio_process_alive: PASS
contract_topic__odom: PASS
contract_topic__cloud_body: PASS
contract_topic__cloud_registered: PASS
contract_cloud_body_frame: base_link
fastlio_tf_camera_init_body: ABSENT
odom_base_link_authority: PRESENT
costmap_launch_process_alive: PASS
costmap_lifecycle: active
costmap_global_frame: odom
costmap_robot_base_frame: base_link
costmap_observation_topic: /go2w/perception/cloud_body
costmap_cloud_subscription: PASS
costmap_topic_once: PASS
costmap_frame: odom
forbidden_phase3_plus_nodes: ABSENT
costmap_average_rate: 1.667
cloud_body_average_rate: 9.608
odom_average_rate: 9.597
sim_process_alive_after_window: PASS
perception_process_alive_after_window: PASS
fastlio_process_alive_after_window: PASS
costmap_process_alive_after_window: PASS
forbidden_phase3_plus_nodes: ABSENT
fastlio_missing_time_warning_count: 0
perception_contract_error_count: 0
fastlio_runtime_exception_count: 0
costmap_runtime_exception_count: 0
post_costmap_fastlio_tf_camera_init_body: ABSENT
post_costmap_odom_base_link_authority: PRESENT
phase2h_result: PASS
```

Evidence directory:

```text
/tmp/go2w_phase2h_costmap_consumer_13828
```

## Current Decision

Phase 2H is accepted as the first Nav2 costmap consumer gate:

- standalone `/costmap/costmap` reaches lifecycle `active`;
- the costmap consumes `/go2w/perception/cloud_body` as PointCloud2 input;
- the costmap publishes `/costmap/costmap` in `odom`;
- `odom -> base_link` remains owned by perception;
- upstream FAST-LIO `camera_init -> body` TF remains absent;
- missing pointcloud `time` warnings remain zero;
- no planner, controller, BT, route, mission, stair, elevation, or
  traversability nodes are launched.

With Phase 2H accepted, the Phase 2 system-blueprint acceptance criterion
"Nav2 costmap can consume FAST-LIO point cloud output" is satisfied on the
current headless Fortress baseline.
