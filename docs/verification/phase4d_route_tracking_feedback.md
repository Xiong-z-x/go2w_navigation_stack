# Phase 4D-Min Route Tracking Feedback Gate Acceptance

## Scope
Phase 4D-min adds a route tracking feedback observation gate. It validates that
mission-side logic can consume the standard `nav2_msgs/action/ComputeAndTrackRoute`
feedback shape, observe staircase edge `500`, and detect a `stair_exec` route
operation trigger.

This is not real `nav2_route` tracking against robot motion, production Mission
Orchestrator, `map_server`, AMCL, `map -> odom` localization, real stair
locomotion tuning, elevation mapping, traversability analysis, automatic stair
detection, or automatic connector generation.

## Implemented Runtime Surface
- `go2w_navigation_runtime.route_tracking_feedback_executor` provides a
  navigation-owned verifier Action server for `ComputeAndTrackRoute`.
- `go2w_mission.phase4d_route_tracking_observer` provides a mission-owned
  one-shot Action client that records route feedback.
- `go2w_mission/launch/phase4d_route_tracking_feedback.launch.py` starts the
  feedback executor.
- `tools/verify_phase4d_route_tracking_feedback.sh` verifies success, missing
  operation trigger, and unavailable action paths.

## Verified Facts
- The observer receives `ComputeAndTrackRoute` feedback.
- The observer sees route edges `300, 301, 500, 400, 401`.
- The observer detects staircase edge `500`.
- The observer detects `stair_exec` in `operations_triggered`.
- Missing operation trigger is diagnosable as `ROUTE_OPERATION_NOT_OBSERVED`.
- Missing action server is diagnosable as `ROUTE_TRACKING_UNAVAILABLE`.

## Verification Evidence
Timestamp: `2026-05-01T02:17+08:00`

Static syntax check:

```bash
bash -n tools/verify_phase4d_route_tracking_feedback.sh
```

Result: passed with exit code `0`.

Focused navigation tests:

```bash
PYTHONPATH=go2w_navigation python3 -m pytest \
  go2w_navigation/test/test_phase4d_route_tracking_feedback_executor.py \
  -q
```

Result:

```text
2 passed in 0.01s
```

Focused mission tests:

```bash
PYTHONPATH=go2w_mission python3 -m pytest \
  go2w_mission/test/test_phase4d_route_tracking_observer.py \
  -q
```

Result:

```text
3 passed in 0.01s
```

Package build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_navigation go2w_mission
```

Result:

```text
Summary: 2 packages finished [0.41s]
```

Runtime acceptance:

```bash
./tools/verify_phase4d_route_tracking_feedback.sh
```

Key output:

```text
phase4d_route_tracking_feedback_result: RUNNING
node_/go2w_route_tracking_feedback_executor: PRESENT
action_/compute_and_track_route: PRESENT
observer_success: PASS
phase4d_success_keys: PASS
observer_missing_operation: PASS
observer_unavailable: PASS
phase4d_route_tracking_feedback_result: PASS
```

The runtime evidence directory for that run was:

```text
/tmp/go2w_phase4d_route_tracking_feedback_11273
```

## Reproduction Command
From the repository root:

```bash
./tools/verify_phase4d_route_tracking_feedback.sh
```

The script builds `go2w_navigation` and `go2w_mission`, starts the
`ComputeAndTrackRoute` feedback executor, runs the mission observer, and verifies
both positive and negative feedback/operation paths.

## Open Validation Items
- This is a verifier feedback source, not real route tracking against robot
  motion.
- Route Operation behavior is represented through the standard
  `operations_triggered` feedback field; no real `nav2_route` operation plugin
  is executed.
- No production Mission Orchestrator API is introduced.
- No localization or map server chain is introduced.
