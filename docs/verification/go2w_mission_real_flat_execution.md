# Go2W Mission Real-Model Flat Execution Verification

## Scope
This document records the post-Phase-4 hardening gate that connects the
`go2w_mission` `RunMission` flat segment execution path to the real-model Nav2
`/navigate_to_pose` action surface.

This replaces the verifier-only flat executor for this opt-in flat-only mission
fixture by launching the mission API with `launch_flat_nav_executor:=false`.
It does not remove the Phase 4C verifier skeleton, and it is not production
Mission Orchestrator, multi-floor autonomy, real `nav2_route` tracking against
robot motion, stair dynamics, AMCL, `map_server`, or `map -> odom`
localization.

## Implemented Runtime Surface
- `go2w_mission.mission_api` now accepts `--flat-behavior-tree`.
- The default remains `success`, preserving the Phase 4C verifier action
  server behavior.
- The sentinel value `__empty__` is converted to an empty
  `NavigateToPose.Goal.behavior_tree`, allowing real Nav2 BT Navigator to use
  its configured default behavior tree.
- `tools/verify_go2w_mission_real_flat_execution.sh` starts:
  - opt-in real Go2W simulation,
  - perception TF authority,
  - FAST-LIO,
  - Phase 3A Nav2 with `phase5_real_model_nav2_same_floor.yaml`,
  - mission API with route server and `launch_flat_nav_executor:=false`.
- The verifier generates a short odom-frame flat-only route graph from the
  current perception odometry, keeps the target yaw in the generated node
  properties, reloads `/route_server/set_route_graph`, and then sends a
  `RunMission` goal from node `100` to node `101`.

## Verification Run
- Date: `2026-05-02`
- Command:

```bash
./tools/verify_go2w_mission_real_flat_execution.sh
```

- Evidence directory:

```text
/tmp/go2w_mission_real_flat_execution_8114
```

- Result:

```text
go2w_mission_real_flat_execution_result: PASS
```

- Key result lines:

```text
mission_real_flat_goal_status: SUCCEEDED
mission_real_flat_goal_result_code: MISSION_SUCCEEDED
mission_real_flat_goal_message: mission_succeeded
mission_real_flat_segment_summary: flat:10
mission_real_flat_execution_result: PASS
go2w_mission_real_flat_execution_result: PASS
```

## Hardened Rerun
- Date: `2026-05-02T22:05+08:00`
- Command:

```bash
./tools/verify_go2w_mission_real_flat_execution.sh
```

- Evidence directory:

```text
/tmp/go2w_mission_real_flat_execution_12698
```

- Result:

```text
go2w_mission_real_flat_execution_result: PASS
```

## Production Skeleton Hardening Rerun
- Date: `2026-05-04T00:07+08:00`
- Command:

```bash
./tools/verify_go2w_mission_real_flat_execution.sh
```

- Evidence directory:

```text
/tmp/go2w_mission_real_flat_execution_9341
```

- Result:

```text
go2w_mission_real_flat_execution_result: PASS
```

- Key result lines:

```text
controller_server_lifecycle: active
planner_server_lifecycle: active
bt_navigator_lifecycle: active
mission_real_flat_graph_target_yaw: -0.265109
mission_real_flat_goal_status: SUCCEEDED
mission_real_flat_goal_result_code: MISSION_SUCCEEDED
mission_real_flat_segment_summary: flat:10
mission_real_flat_cmd_vel_nonzero_count: 15
mission_real_flat_execution_result: PASS
post_mission_map_odom: ABSENT
post_mission_odom_base_link_authority: PRESENT
```

### Non-Passing Attempt During This Rerun
- Evidence directory:

```text
/tmp/go2w_mission_real_flat_execution_7053
```

- Observed failure:

```text
controller_server_lifecycle: FAIL
inactive [2]
```

- Log evidence showed Nav2 lifecycle manager configured `controller_server` and
  `planner_server`, then timed out while sending the `bt_navigator/change_state`
  response. After manually clearing the failed run's orphaned sim / perception /
  FAST-LIO / Nav2 processes, the same verifier passed in a new ROS domain.
- Current judgment: this is a ROS lifecycle / runtime-cleanup flake, not evidence
  of a mission API code regression. Future failures of this shape should first
  inspect `nav2.log`, clear residual processes, and rerun in a clean domain before
  changing mission or route graph code.

## Serial Rerun After Concurrent Heavy Verifier
- Date: `2026-05-04T03:05+08:00`
- Command:

```bash
./tools/verify_go2w_mission_real_flat_execution.sh
```

- Evidence directory:

```text
/tmp/go2w_mission_real_flat_execution_33491
```

- Result:

```text
go2w_mission_real_flat_execution_result: PASS
```

- Key result lines:

```text
mission_real_flat_goal_status: SUCCEEDED
mission_real_flat_goal_result_code: MISSION_SUCCEEDED
mission_real_flat_segment_summary: flat:10
mission_real_flat_cmd_vel_nonzero_count: 15
mission_real_flat_execution_result: PASS
post_mission_map_odom: ABSENT
post_mission_odom_base_link_authority: PRESENT
go2w_mission_real_flat_execution_result: PASS
```

- This rerun passed after the control-chain wrapper had been run separately,
  confirming the earlier `FAIL_NO_PARAM` symptom was a heavy-verifier
  concurrency flake. Keep this verifier serialized with the other heavyweight
  Gazebo jobs.

## Verified Facts
- Real-model controllers reached `active`.
- `/clock`, `/imu`, `/lidar_points`, and `/joint_states` produced messages.
- `diff_drive_controller.enable_odom_tf` remained `False`.
- Before perception activation, `odom -> base_link` and `map -> odom` were
  absent.
- FAST-LIO input pointclouds carried the `time` field.
- `/go2w/perception/odom`, `/go2w/perception/cloud_body`, and
  `/go2w/perception/cloud_registered` produced messages.
- `go2w_perception` owned `odom -> base_link` before and after the mission.
- `map -> odom` remained absent.
- Nav2 `controller_server`, `planner_server`, and `bt_navigator` reached
  lifecycle `active`.
- The real `/navigate_to_pose` action was present.
- `controller_server.odom_topic` was `/go2w/perception/odom`.
- Local and global costmaps published in `odom`.
- Mission API started without `go2w_flat_nav_executor`.
- `/route_server/set_route_graph` successfully reloaded the generated flat-only
  route graph immediately before the mission goal.
- `RunMission` returned `MISSION_SUCCEEDED` with segment summary `flat:10`.
- `/cmd_vel` was nonzero during execution.
- Perception odometry and diff-drive odometry both changed.
- Sim, perception, FAST-LIO, Nav2, and mission logs had zero runtime exception
  matches.

## Key Result Lines
```text
node_/go2w_flat_nav_executor: ABSENT
set_route_graph: PASS
mission_real_flat_goal_status: SUCCEEDED
mission_real_flat_goal_success: True
mission_real_flat_goal_result_code: MISSION_SUCCEEDED
mission_real_flat_segment_count: 1
mission_real_flat_segment_summary: flat:10
mission_real_flat_perception_odom_delta_xy: 0.092673
mission_real_flat_diff_drive_odom_delta_xy: 0.118375
mission_real_flat_cmd_vel_nonzero_count: 21
mission_real_flat_execution_result: PASS
post_mission_map_odom: ABSENT
post_mission_odom_base_link_authority: PRESENT
go2w_mission_real_flat_execution_result: PASS
```

## Debugging Notes
- A first iteration tried to pass an empty launch override as
  `flat_behavior_tree:=`. ROS 2 launch rejects empty CLI overrides, so the
  accepted implementation uses `flat_behavior_tree:=__empty__` and converts the
  sentinel inside `mission_api.py`.
- A fixture iteration used node id `0`; mission API correctly rejected it as
  `MISSION_INVALID_GOAL`. The accepted generated graph uses positive node ids
  `100 -> 101`.
- A stale install-space run still sent `behavior_tree=success` to real Nav2 and
  Nav2 aborted with `BT file not found: success`. Runtime verification after
  editing ROS package source must rebuild the affected packages at least once.
- A graph generated too early could become stale as perception odometry settled.
  The accepted verifier regenerates the graph and reloads route_server after
  mission API is ready and immediately before sending the mission goal.
- A later rerun showed `MISSION_FLAT_FAILED` because the flat goal had been
  reduced to x/y only, and `_to_pose_stamped()` was still emitting a unit
  quaternion. The accepted fix preserves target yaw in the generated route
  graph and converts that yaw to a quaternion before sending
  `NavigateToPose`.
- That pose conversion is now shared between `mission_api.py` and
  `phase4b_mission_runtime.py` through `go2w_mission.mission_pose`, so the two
  mission flat execution paths no longer drift on orientation handling.

## Open Validation Items
- This verifies a flat-only mission fixture, not a complete flat/stair/flat
  cross-floor real-motion mission.
- It uses `NavigateToPose`, not production `nav2_route` robot-motion route
  tracking.
- The real Go2W path remains opt-in and does not replace the default
  `sim.launch.py` placeholder baseline.
- Stair traversal and real stair dynamics remain open.
- Production Mission Orchestrator priority scheduling remains open; durable queue
  replay and bounded task history are covered separately in
  `docs/verification/mission_api_queue_replay.md` and
  `docs/verification/mission_api_task_history.md`.
- Do not run this verifier in parallel with
  `verify_go2w_control_chain_regression.sh`; the shared ROS/Gazebo runtime can
  produce false timeout / parameter-discovery flakes under combined load.
