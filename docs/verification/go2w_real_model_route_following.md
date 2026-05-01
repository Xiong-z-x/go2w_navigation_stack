# Go2W Real Model Same-Floor Route Following Verification

## Scope
This document records the opt-in real-model same-floor route-following verifier.
It proves that the imported Go2W model can execute a short `odom`-frame
`NavigateToPose` goal through Nav2 while keeping perception ownership of
`odom -> base_link`.

This is not production route tracking. It does not prove `nav2_route`
multi-edge route tracking against robot motion, real staircase locomotion,
hardware gait control, `map_server`, AMCL, or `map -> odom` localization.

## Source Basis
- The verifier uses the opt-in real-model launch:
  `go2w_sim/launch/sim_go2w_real.launch.py`.
- The real-model Nav2 parameters live in
  `go2w_navigation/config/phase5_real_model_nav2_same_floor.yaml`.
- The verifier keeps the Phase 3A same-floor Nav2 launch surface, but passes
  the real-model params file through `params_file:=...`.
- The costmap tuning is real-model-specific:
  - `robot_radius: 0.28`
  - `footprint_padding: 0.01`
  - `origin_z: -0.40`
  - `z_voxels: 16`
- `z_voxels` intentionally remains `16`; the Humble voxel grid implementation
  reported that it supports at most 16 z values during debugging.

## Verification Run
- Date: `2026-05-01T19:11+08:00`
- Command: `GO2W_REAL_ROUTE_REBUILD_REPO=0 ./tools/verify_go2w_real_model_route_following.sh`
- Evidence directory: `/tmp/go2w_real_model_route_following_13161`
- Result: `go2w_real_model_route_following_result: PASS`

## Verified Facts
- `joint_state_broadcaster`, `leg_position_controller`, and
  `diff_drive_controller` reached `active`.
- `/clock`, `/imu`, `/lidar_points`, and `/joint_states` produced messages.
- `/joint_states` included both leg joints and foot wheel joints.
- `diff_drive_controller.enable_odom_tf` remained `False`.
- Before perception activation, `odom -> base_link` and `map -> odom` were absent.
- FAST-LIO input pointclouds carried the `time` field.
- `/go2w/perception/odom`, `/go2w/perception/cloud_body`, and
  `/go2w/perception/cloud_registered` produced messages.
- `go2w_perception` owned the `odom -> base_link` TF edge before and after Nav2.
- `map -> odom` remained absent.
- Nav2 `controller_server`, `planner_server`, and `bt_navigator` reached
  lifecycle `active`.
- `/navigate_to_pose` was available.
- `controller_server.odom_topic` was `/go2w/perception/odom`.
- Local and global costmaps published in `odom`.
- No forbidden mission, route, stair, elevation, traversability, AMCL, or
  map-server nodes were present.
- A short `NavigateToPose` goal succeeded on the real model.
- `/cmd_vel` was nonzero during execution.
- Perception odometry and diff-drive odometry both changed.
- Sim, perception, FAST-LIO, and Nav2 logs had zero runtime exception matches.

## Result Keys
```text
joint_state_broadcaster_active: PASS
leg_position_controller_active: PASS
diff_drive_controller_active: PASS
diff_drive_enable_odom_tf: False
pre_perception_odom_base_link: ABSENT
pre_perception_map_odom: ABSENT
adapted_pointcloud_time_field: PASS
contract_topic__odom: PASS
contract_topic__cloud_body: PASS
contract_topic__cloud_registered: PASS
fastlio_tf_camera_init_body: ABSENT
pre_nav2_map_odom: ABSENT
odom_base_link_authority: PRESENT
controller_server_lifecycle: active
planner_server_lifecycle: active
bt_navigator_lifecycle: active
navigate_to_pose_action: AVAILABLE
controller_odom_topic: /go2w/perception/odom
bt_navigator_global_frame: odom
bt_navigator_robot_base_frame: base_link
local_costmap_topic_once: PASS
global_costmap_topic_once: PASS
local_costmap_frame: odom
forbidden_extra_nodes: ABSENT
real_route_goal_status: SUCCEEDED
real_route_perception_odom_delta_xy: 0.183221
real_route_diff_drive_odom_delta_xy: 0.146164
real_route_cmd_vel_nonzero_count: 560
real_route_goal_result: PASS
sim_runtime_exception_count: 0
perception_runtime_exception_count: 0
fastlio_runtime_exception_count: 0
nav2_runtime_exception_count: 0
post_nav2_fastlio_tf_camera_init_body: ABSENT
post_nav2_map_odom: ABSENT
post_nav2_odom_base_link_authority: PRESENT
go2w_real_model_route_following_result: PASS
```

## Implementation Notes
- The real-model route-following verifier is replayable through
  `tools/verify_go2w_real_model_route_following.sh`.
- The verifier launches the real model, perception TF authority, FAST-LIO, and
  the Phase 3A Nav2 bringup with the real-model params file.
- An earlier verifier iteration failed when the local/global voxel layers could
  not raytrace from the real-model sensor origin because `origin_z: -0.20` was
  too high. The accepted fix lowers the real-model costmap origin to `-0.40`.
- A later debugging attempt set `z_voxels: 22`, but the runtime reported that
  the voxel grid supports at most 16 z values. The accepted config keeps
  `z_voxels: 16`.

## Open Validation Items
- The real model path remains opt-in and does not replace `sim.launch.py`.
- This verifies a short same-floor `NavigateToPose` goal, not production
  `nav2_route` route tracking.
- The `nav2_route` live feedback gate still runs under a controlled TF fixture,
  not the real-model motion chain.
- Stair traversal, stair dynamics, and legged controller tuning remain open.
- `map_server`, AMCL, and `map -> odom` localization remain open.
