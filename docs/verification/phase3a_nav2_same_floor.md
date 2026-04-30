# Phase 3A Nav2 Same-Floor Minimal Bringup

## Purpose

This document records the Phase 3A acceptance gate for the first full Nav2
same-floor navigation closed loop.

Phase 3A verifies that Nav2 planner, controller, BT Navigator, and costmaps can
consume the accepted Phase 2 perception contracts and command the simulated base
through `/cmd_vel`.

## Phase Boundary

Allowed in this task:

- add a minimal Nav2 same-floor config and launch in `go2w_navigation`
- add a Phase 3A feature-rich verification world while preserving the default
  empty-world baseline
- run planner, controller, BT Navigator, and lifecycle manager
- use `odom` as the Phase 3A navigation frame
- consume `/go2w/perception/odom` and perception-owned `odom -> base_link`
- consume `/go2w/perception/cloud_body` in local and global costmaps
- send a short `NavigateToPose` goal in `odom`
- record lifecycle, action, `/cmd_vel`, odometry, costmap, TF, and log evidence

Forbidden in this task:

- publishing a temporary `map -> odom` TF edge
- enabling `map_server`, AMCL, `nav2_route`, route graphs, mission
  orchestration, staircase execution, multi-floor behavior, elevation mapping,
  or traversability
- modifying default Gazebo behavior, URDF, controller, or perception algorithm
  assets
- vendoring FAST_LIO_ROS2 source into the repository

## Automation

Runtime verifier:

```bash
./tools/verify_phase3a_nav2_same_floor.sh
```

The default navigation goal is a short `odom`-frame diagonal target. Runtime
parameters can be changed without editing the repository:

```bash
GO2W_PHASE3A_NAV_GOAL_OFFSET_X=0.035 \
GO2W_PHASE3A_NAV_GOAL_OFFSET_Y=0.020 \
GO2W_PHASE3A_NAV_TIMEOUT_SECONDS=90 \
GO2W_PHASE3A_HZ_WINDOW_SECONDS=15 \
./tools/verify_phase3a_nav2_same_floor.sh
```

## Observed Result

Observed on 2026-04-30.

Scoped build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_navigation go2w_perception go2w_description go2w_sim
```

Observed result:

```text
Summary: 4 packages finished [0.47s]
```

Static checks:

```bash
bash -n tools/verify_phase3a_nav2_same_floor.sh
shellcheck tools/verify_phase3a_nav2_same_floor.sh
python3 -m py_compile go2w_sim/launch/sim.launch.py go2w_navigation/launch/phase3a_nav2_same_floor.launch.py
xmllint --noout go2w_sim/worlds/phase3a_feature_world.sdf go2w_navigation/behavior_trees/phase3a_navigate_to_pose.xml go2w_navigation/behavior_trees/phase3a_navigate_through_poses.xml
git diff --check
```

Observed result:

```text
no output
```

Runtime verifier:

```bash
./tools/verify_phase3a_nav2_same_floor.sh
```

Observed summary:

```text
phase3a_world_present: PASS
required_topic__clock: PASS
required_topic__imu: PASS
required_topic__lidar_points: PASS
diff_drive_enable_odom_tf: False
pre_activation_odom_base_link: ABSENT
pre_activation_map_odom: ABSENT
perception_process_alive: PASS
adapted_pointcloud_time_field: PASS
fastlio_process_alive: PASS
contract_topic__odom: PASS
contract_topic__cloud_body: PASS
contract_topic__cloud_registered: PASS
contract_cloud_body_frame: base_link
fastlio_tf_camera_init_body: ABSENT
pre_nav2_map_odom: ABSENT
odom_base_link_authority: PRESENT
nav2_launch_process_alive: PASS
controller_server_lifecycle: active
planner_server_lifecycle: active
bt_navigator_lifecycle: active
navigate_to_pose_action: AVAILABLE
controller_odom_topic: /go2w/perception/odom
local_costmap_global_frame: odom
local_costmap_robot_base_frame: base_link
local_costmap_observation_topic: /go2w/perception/cloud_body
global_costmap_global_frame: odom
global_costmap_robot_base_frame: base_link
global_costmap_observation_topic: /go2w/perception/cloud_body
local_costmap_cloud_subscription: PASS
global_costmap_cloud_subscription: PASS
local_costmap_topic_once: PASS
global_costmap_topic_once: PASS
local_costmap_frame: odom
global_costmap_frame: odom
forbidden_phase3a_extra_nodes: ABSENT
phase3a_goal_status: SUCCEEDED
phase3a_odom_delta_xy: 0.047916
phase3a_cmd_vel_nonzero_count: 126
phase3a_diff_drive_delta_xy: 0.162024
phase3a_nav_goal_result: PASS
navigate_to_pose_goal: PASS
local_costmap_average_rate: 1.585
global_costmap_average_rate: 0.667
cloud_body_average_rate: 9.074
odom_average_rate: 9.176
sim_process_alive_after_goal: PASS
perception_process_alive_after_goal: PASS
fastlio_process_alive_after_goal: PASS
nav2_process_alive_after_goal: PASS
forbidden_phase3a_extra_nodes: ABSENT
fastlio_missing_time_warning_count: 0
perception_contract_error_count: 0
fastlio_runtime_exception_count: 0
nav2_runtime_exception_count: 0
post_nav2_fastlio_tf_camera_init_body: ABSENT
post_nav2_map_odom: ABSENT
post_nav2_odom_base_link_authority: PRESENT
phase3a_result: PASS
```

Evidence directory:

```text
/tmp/go2w_phase3a_nav2_same_floor_12208
```

## Current Decision

Phase 3A is accepted as the first full Nav2 same-floor navigation closed loop:

- Nav2 planner, controller, and BT Navigator reach lifecycle `active`;
- `/navigate_to_pose` accepts and succeeds on a short `odom`-frame goal;
- Nav2 publishes non-zero `/cmd_vel`;
- perception odometry changes during the goal;
- local and global costmaps consume `/go2w/perception/cloud_body`;
- `odom -> base_link` remains perception-owned;
- no temporary `map -> odom` edge is published;
- `nav2_route`, route graph, mission, stair, elevation, and traversability nodes
  remain absent.
