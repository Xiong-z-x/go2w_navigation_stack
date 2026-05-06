# Go2W Real Model nav2_route Robot-Motion Tracking Verification

## Scope
This document records the opt-in real-model `nav2_route` robot-motion route
tracking gate.

The gate starts the real Go2W model, perception TF authority, FAST-LIO, real
Nav2 same-floor bringup, and the real `nav2_route` `route_server`. It then
generates a short odom-frame route graph from settled perception odometry,
reloads `/route_server/set_route_graph`, sends a standard
`ComputeAndTrackRoute` goal, and drives the robot through the same edge with
`NavigateToPose`.

This is a real robot-motion route-tracking observation gate. It is still not
cross-floor autonomy, a real stair route-operation plugin, physical stair
locomotion, `map_server`, AMCL, `map -> odom`, elevation mapping,
traversability, or automatic connector generation.

## Source Basis
- Nav2 `route_server` is used through `nav2_msgs/action/ComputeAndTrackRoute`.
- The route graph uses `odom` because the accepted real-model Nav2 motion path
  still runs in `odom` and keeps `map -> odom` absent.
- Real motion is produced by `NavigateToPose`; route tracking observes the
  robot through TF, it does not replace the Nav2 controller.
- The verifier keeps `diff_drive_controller.enable_odom_tf` disabled and checks
  that perception still owns `odom -> base_link`.
- `route_server` is launched with the existing `phase3b_route_server.yaml`
  pattern and `use_sim_time:=false`. A first attempt with
  `use_sim_time:=true` stalled during route-server lifecycle configure in this
  mixed real-model runtime; the accepted pattern follows the existing Phase 3B
  and Phase 5A route-server gates.

## Verification Run
- Date: `2026-05-06`
- Command:

```bash
./tools/verify_go2w_real_model_route_tracking.sh
```

- Evidence directory:

```text
/tmp/go2w_real_model_route_tracking_27576
```

- Result:

```text
go2w_real_model_route_tracking_result: PASS
```

## Verified Facts
- The opt-in real-model launch reached active controllers:
  `joint_state_broadcaster`, `leg_position_controller`, and
  `diff_drive_controller`.
- `/clock`, `/imu`, `/lidar_points`, and `/joint_states` produced messages.
- `diff_drive_controller.enable_odom_tf` remained `False`.
- Before perception activation, both `odom -> base_link` and `map -> odom`
  were absent.
- FAST-LIO input pointclouds carried the `time` field.
- `/go2w/perception/odom` and `/go2w/perception/cloud_body` produced messages.
- `go2w_perception` owned `odom -> base_link` before Nav2 and after route
  tracking.
- `map -> odom` remained absent after route tracking.
- Nav2 `controller_server`, `planner_server`, and `bt_navigator` reached
  lifecycle `active`.
- `/navigate_to_pose` was present.
- The verifier generated an odom-frame route graph from settled perception
  odometry and parsed it as JSON.
- `route_server` reached lifecycle `active`.
- `/compute_and_track_route` was present with type
  `nav2_msgs/action/ComputeAndTrackRoute`.
- `/route_server/set_route_graph` reloaded the generated graph.
- `ComputeAndTrackRoute` accepted the goal and published feedback for edge
  `10`.
- The real Nav2 goal returned `SUCCEEDED`.
- `/cmd_vel` had nonzero samples during execution.
- Perception odometry and diff-drive odometry both changed.
- Sim, perception, FAST-LIO, Nav2, and route-server logs had zero runtime
  exception matches.

## Key Result Lines
```text
route_server_lifecycle: active
action_type_/compute_and_track_route: nav2_msgs/action/ComputeAndTrackRoute
set_route_graph: PASS
real_route_tracking_route_goal: ACCEPTED
real_route_tracking_feedback_edge: 10
real_route_tracking_nav_goal_status: SUCCEEDED
real_route_tracking_feedback_edges: 0,10
real_route_tracking_perception_odom_delta_xy: 0.090716
real_route_tracking_diff_drive_odom_delta_xy: 0.096892
real_route_tracking_cmd_vel_nonzero_count: 14
real_route_tracking_feedback_result: PASS
real_route_tracking_goal_result: PASS
post_tracking_map_odom: ABSENT
post_tracking_odom_base_link_authority: PRESENT
go2w_real_model_route_tracking_result: PASS
```

## Open Validation Items
- This does not execute a cross-floor route.
- This does not replace Mission Orchestrator flat/stair/flat runtime.
- This does not prove a real stair route operation plugin.
- This does not validate physical stair traversal.
- This does not introduce `map_server`, AMCL, or `map -> odom`.
- The real-model path remains opt-in and does not replace the default
  placeholder launch baseline.
