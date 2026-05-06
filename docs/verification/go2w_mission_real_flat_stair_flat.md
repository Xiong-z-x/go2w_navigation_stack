# Go2W Mission Real-Model Flat/Stair/Flat Verification

## Scope
This document records the post-Phase-4 integration gate for the opt-in
real-model `RunMission` flat/stair/flat runtime.

The verifier starts the real-model simulation, perception TF authority,
FAST-LIO, real-model Nav2, and the mission API. It launches the mission API with
`launch_flat_nav_executor:=false`, keeps the real `/navigate_to_pose` surface for
flat segments, keeps the existing dedicated `/stair_exec` Action skeleton for
the stair segment, and enables mission-side
`route_tracking_action:=/compute_and_track_route` for the two flat segments.

This is not physical stair locomotion, a tuned gait, a hardware wheel-lock or
body-height actuator backend, a real `nav2_route` stair operation plugin,
production cross-floor route tracking, complete production Mission
Orchestrator, AMCL, `map_server`, `map -> odom`, Phase 5 automatic connector
generation, or a default real-model baseline switch.

## External Interface Boundary Checked
- ROS 2 Humble callback-group documentation states that the default callback
  group is mutually exclusive, and that action-client callbacks inherit the
  callback group assigned to the client. This supports the mission API change
  to keep downstream action clients in an explicit `ReentrantCallbackGroup`:
  <https://docs.ros.org/en/humble/How-To-Guides/Using-callback-groups.html>.
- ROS Humble `nav2_msgs/action/ComputeAndTrackRoute` exposes node-id requests
  and feedback fields including `current_edge_id` and
  `operations_triggered`, matching this verifier's route-tracking assertions:
  <https://docs.ros.org/en/humble/p/nav2_msgs/action/ComputeAndTrackRoute.html>.
- Nav2 Route Server documentation describes route computation through a
  predefined graph, not free-space 3D terrain planning. The verifier therefore
  uses a hand-authored short route graph and leaves terrain-aware connector
  discovery for Phase 5:
  <https://docs.nav2.org/configuration/packages/configuring-route-server.html>.

## Implemented Runtime Surface
- `tools/verify_go2w_mission_real_flat_stair_flat.sh` builds a short odom-frame
  graph from settled perception odometry:
  - edge `10`: first flat segment,
  - edge `500`: short nonzero staircase handoff connector,
  - edge `20`: second flat segment.
- The stair connector is intentionally a short nonzero handoff edge. It is not
  a physical stair geometry model.
- The mission API executes the graph as:

```text
flat:10;stair:500:stair_a:F1->F2;flat:20
```

- Both flat segments use real Nav2 `/navigate_to_pose` and mission-side
  `ComputeAndTrackRoute` observation.
- The stair segment uses the existing `/stair_exec` phase-aware skeleton.
- `go2w_mission.mission_api` now assigns downstream action clients to an
  explicit `ReentrantCallbackGroup` and the internal wait helpers call
  `rclpy.spin_once(node, timeout_sec=0.05)` while waiting. This services nested
  action-client responses during the `RunMission` action execute path.

## Verification Run
- Date: `2026-05-06`
- Command:

```bash
./tools/verify_go2w_mission_real_flat_stair_flat.sh
```

- Evidence directory:

```text
/tmp/go2w_mission_real_flat_stair_flat_48188
```

- Result:

```text
go2w_mission_real_flat_stair_flat_result: PASS
```

## Key Result Lines
```text
mission_real_flat_stair_flat_goal_status: SUCCEEDED
mission_real_flat_stair_flat_goal_success: True
mission_real_flat_stair_flat_goal_result_code: MISSION_SUCCEEDED
mission_real_flat_stair_flat_segment_count: 3
mission_real_flat_stair_flat_segment_summary: flat:10;stair:500:stair_a:F1->F2;flat:20
mission_real_flat_stair_flat_perception_odom_delta_xy: 0.242404
mission_real_flat_stair_flat_diff_drive_odom_delta_xy: 0.268338
mission_real_flat_stair_flat_cmd_vel_nonzero_count: 57
mission_route_tracking_feedback_edge: 10
mission_route_tracking_feedback_edge: 20
mission_route_tracking_result: PASS
post_mission_map_odom: ABSENT
post_mission_odom_base_link_authority: PRESENT
go2w_mission_real_flat_stair_flat_result: PASS
```

The mission API log also records the command-gate transitions
`flat/wheeled -> stair/legged -> flat/wheeled` and the stair phase sequence:

```text
prepare,wheel_lock,body_height_transition_down,execute_stairs,body_height_transition_up,release
```

## Non-Passing Attempts During Hardening
- `/tmp/go2w_mission_real_flat_stair_flat_38925`: route computation timed out
  after route server reported a route with four nodes and three edges. The
  synthetic stair connector edge was zero length. The fixture now uses a short
  nonzero handoff connector.
- `/tmp/go2w_mission_real_flat_stair_flat_40625`: generated Python graph builder
  had an indentation error. The generated helper was corrected and the script is
  covered by `bash -n`, `shellcheck`, and a contract pytest.
- `/tmp/go2w_mission_real_flat_stair_flat_42154` and
  `/tmp/go2w_mission_real_flat_stair_flat_44455`: `/stair_exec` completed its
  phase sequence, but the mission API timed out while waiting for the downstream
  stair action goal response. The root fix was to use a reentrant action-client
  callback group and spin the node while waiting.
- `/tmp/go2w_mission_real_flat_stair_flat_46576`: the mission succeeded, route
  tracking observed edges `10` and `20`, and motion evidence passed, but the
  verifier expected a narrower segment summary. The final script now preserves
  connector metadata in the expected summary.

## Verified Facts
- The verifier does not start `go2w_flat_nav_executor`.
- `/compute_route`, `/compute_and_track_route`, `/navigate_to_pose`,
  `/stair_exec`, and `/go2w/mission/run` were present.
- Route graph reload through `/route_server/set_route_graph` passed immediately
  before the mission goal.
- `RunMission` returned `MISSION_SUCCEEDED` with three segments:
  `flat:10;stair:500:stair_a:F1->F2;flat:20`.
- Mission-side route tracking observed flat feedback edges `10` and `20`.
- `/cmd_vel` was nonzero during the mission.
- Perception odometry and diff-drive odometry both changed.
- `/stair_exec` reached the full phase-aware skeleton sequence.
- Command ownership moved through flat, stair, and flat owners.
- `map -> odom` remained absent.
- `odom -> base_link` remained present from the perception-owned path.
- Sim, perception, FAST-LIO, Nav2, and mission logs had zero runtime exception
  matches in the verifier's checked patterns.

## Remaining Boundaries
- This gate is still synthetic around the stair connector. The stair edge is a
  handoff segment, not a real stair traversal trajectory.
- The verifier proves integrated mission orchestration over current skeletons,
  not production route operation execution inside `nav2_route`.
- Real stair trajectory generation, gait tuning, hardware wheel lock, body
  height control, localization via `map -> odom`, and Phase 5 connector
  discovery remain separate tasks.
