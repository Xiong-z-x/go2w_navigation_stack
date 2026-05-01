# Phase 5A Live Route Tracking Observation Gate Acceptance

## Scope
Phase 5A adds a live route-tracking observation gate. It drives the installed
`nav2_route` `route_server` through the standard
`nav2_msgs/action/ComputeAndTrackRoute` action, uses a controlled TF trajectory
fixture to advance through the Phase 3C hospital route graph, and verifies that
the live route server emits feedback for staircase edge `500`.

This is not production Mission Orchestrator, real robot-motion route tracking,
real stair locomotion dynamics/tuning, `map_server`, AMCL, `map -> odom`
localization, elevation mapping, traversability analysis, automatic stair
detection, or automatic connector generation.

## Implemented Runtime Surface
- `go2w_mission.phase5a_live_route_tracking` provides the live probe runtime and
  the `build_route_pose_samples` helper used by the pure test.
- `go2w_mission/launch/phase5a_live_route_tracking.launch.py` starts the real
  `nav2_route` `route_server`, its lifecycle manager, and the live probe.
- `tools/verify_phase5a_live_route_tracking.sh` builds the required packages,
  launches the live gate, waits for the route server and action server, and
  checks the live feedback result keys.

## Verified Facts
- The installed `route_server` node is present during the live gate run.
- The installed `/compute_and_track_route` action is present.
- The action type reported by `ros2 action list -t` is
  `nav2_msgs/action/ComputeAndTrackRoute`.
- The live probe observes route feedback edges `0, 300, 301, 500, 400, 401`.
- The live probe detects staircase edge `500`.
- The live probe observes `AdjustSpeedLimit` in `operations_triggered`.
- The live probe reports `phase5a_route_feedback_seen: PASS`.
- The live probe reports `phase5a_stair_edge_detected: PASS`.
- The top-level verifier reports `phase5a_live_route_tracking_result: PASS`.

## Verification Evidence
Timestamp: `2026-05-01T14:29+08:00`

Static syntax check:

```bash
bash -n tools/verify_phase5a_live_route_tracking.sh
```

Result: passed with exit code `0`.

Focused pure test:

```bash
PYTHONPATH=go2w_mission python3 -m pytest \
  go2w_mission/test/test_phase5a_live_route_tracking.py \
  -q
```

Result:

```text
1 passed in 0.01s
```

Package build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_mission go2w_navigation
```

Result:

```text
Summary: 2 packages finished [2.15s]
```

Package tests:

```bash
source /opt/ros/humble/setup.bash
colcon test --packages-select go2w_mission go2w_navigation
colcon test-result --verbose
```

Result:

```text
Summary: 59 tests, 0 errors, 0 failures, 0 skipped
```

Runtime acceptance:

```bash
./tools/verify_phase5a_live_route_tracking.sh
```

Key output:

```text
phase5a_live_route_tracking_result: PASS
node_/route_server: PRESENT
action_/compute_and_track_route: PRESENT
action_type_/compute_and_track_route: nav2_msgs/action/ComputeAndTrackRoute
phase5a_feedback_edges: 0,300,301,500,400,401
phase5a_feedback_operations: AdjustSpeedLimit
phase5a_stair_edge_detected: PASS
phase5a_route_feedback_seen: PASS
```

The runtime evidence directory for that run was:

```text
/tmp/go2w_phase5a_live_route_tracking_26446
```

## Reproduction Command
From the repository root:

```bash
./tools/verify_phase5a_live_route_tracking.sh
```

The script builds `go2w_mission` and `go2w_navigation`, launches the real
`nav2_route` route server, waits for the live `ComputeAndTrackRoute` action,
runs the live probe, and verifies the route-feedback and staircase-edge
diagnostics.

## Open Validation Items
- This is a live route-server observation gate, not physical robot-motion
  validation.
- The observed route operation is `AdjustSpeedLimit`, not a physical stair
  locomotion controller.
- No production Mission Orchestrator API is introduced.
- No `map_server`, AMCL, or `map -> odom` localization chain is introduced.
- No elevation mapping, traversability, automatic stair detection, or
  automatic connector generation is implemented.
