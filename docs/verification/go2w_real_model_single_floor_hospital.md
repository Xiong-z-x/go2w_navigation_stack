# Go2W Real Model Single-Floor Hospital Verification

## Scope
This document records the opt-in single-floor autonomy gate that combines:

- the official Unitree Go2W-derived real model path,
- the Phase 3C hospital world asset,
- FAST-LIO perception contracts,
- same-floor Nav2 planning and control,
- a heading-relative reachable-goal probe with a minimum planned path-length gate.

This is still a same-floor closed loop only. It does not add `map -> odom`,
`map_server`, AMCL, production `nav2_route` route tracking, cross-floor
autonomy, or real stair dynamics.

## Source Basis
- The real Go2W model path uses the imported Unitree upstream asset basis
  recorded in `go2w_description/UNITREE_MODEL_LICENSE.txt`.
- The scene uses the repository-local Phase 3C hospital world
  `go2w_sim/worlds/phase3c_hospital_multifloor_world.sdf` instead of the small
  Phase 3A obstacle fixture.
- The runtime wrapper delegates to
  `tools/verify_go2w_real_model_route_following.sh` and hardens it with a
  larger same-floor target, a minimum planned path length threshold, and longer
  lifecycle/startup windows suitable for the hospital world.

## Verification Run
- Date: `2026-05-06T16:38:00+08:00`
- Command: `GO2W_VERIFY_DOMAIN_ID=197 bash ./tools/verify_go2w_real_model_single_floor_hospital.sh`
- Evidence directory: `/tmp/go2w_real_model_single_floor_hospital_72042`
- Result: `go2w_real_model_route_following_result: PASS`

## Verified Facts
- `sim_go2w_real.launch.py` starts the real Go2W model headless in the hospital
  world.
- `/clock`, `/imu`, `/lidar_points`, and `/joint_states` produce messages.
- FAST-LIO contracts publish `/go2w/perception/odom`,
  `/go2w/perception/cloud_body`, `/go2w/perception/cloud_registered`, and
  `/go2w/perception/laser_map`.
- `odom -> base_link` remains perception-owned and `map -> odom` remains absent.
- Nav2 planner, controller, and BT Navigator reach lifecycle `active`.
- The hospital-world goal probe rejects candidates whose planned path is too
  short to prove meaningful motion.
- On the recorded run, candidate `2` (`offset_x=0.600`, `offset_y=0.050`)
  became the first acceptable same-floor goal.
- `NavigateToPose` returned `SUCCEEDED`.
- `/cmd_vel` published nonzero commands and both perception and diff-drive
  odometry changed during the run.

## Result Keys
```text
contract_topic__laser_map: PASS
controller_server_lifecycle: active
planner_server_lifecycle: active
bt_navigator_lifecycle: active
real_route_goal_min_planned_path_length_m: 0.250
real_route_goal_candidate_2: offset_x=0.600 offset_y=0.050 status=SUCCEEDED path_poses=6 path_length_m=0.443
real_route_goal_selected_candidate: 2
real_route_goal_status: SUCCEEDED
real_route_perception_odom_delta_xy: 0.367239
real_route_diff_drive_odom_delta_xy: 0.106236
real_route_cmd_vel_nonzero_count: 228
real_route_goal_result: PASS
go2w_real_model_route_following_result: PASS
```

## Open Validation Items
- This gate is headless only; it does not itself guarantee a stable long-lived
  GUI demo session.
- It still runs in `odom`, not a persistent `map` localization chain.
- It uses Nav2 same-floor planning only; it does not prove route-server-backed
  multi-floor autonomy.
