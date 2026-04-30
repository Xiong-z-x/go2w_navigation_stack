# Phase 4B-Min Mission Segment Runtime Acceptance

## Scope
Phase 4B-min adds the smallest mission-side runtime above the accepted Phase 4A
handoff skeleton. It computes a manual `nav2_route` route, decomposes the route
into flat/stair/flat mission segments, dispatches stair segments through the
dedicated `/stair_exec` Action, and reports stable mission result keys.

This is not production Mission Orchestrator, real flat-ground Nav2 execution,
real stair locomotion tuning, real cross-floor autonomous navigation, elevation
mapping, traversability analysis, automatic stair detection, automatic connector
generation, `map_server`, AMCL, or `map -> odom` localization.

## Implemented Runtime Surface
- `go2w_mission.phase4b_mission_segments` provides pure route-edge segmentation
  helpers and stair result classification.
- `go2w_mission.phase4b_mission_runtime` provides a one-shot CLI runtime that:
  - calls `/compute_route`
  - validates the route against the Phase 3C hospital graph
  - groups contiguous flat route edges into flat segments
  - maps each staircase connector edge to one stair segment
  - sends stair segments to `/stair_exec`
  - prints stable `phase4b_final_result` diagnostics
- `go2w_mission/launch/phase4b_mission_runtime.launch.py` starts the minimal
  verifier stack: `route_server`, lifecycle manager, command gate, and stair
  executor.
- `tools/verify_phase4b_mission_segments.sh` rebuilds the required packages,
  launches the verifier stack in an isolated ROS domain, checks nodes/actions,
  and verifies success, failure, cancel, timeout, route-unavailable, and
  connector-unavailable paths.

## Verified Facts
- The Phase 3C hospital route graph can be used to compute a route from node
  `100` to node `202` over staircase connector edge `500`.
- The route edge sequence is decomposed into flat/stair/flat mission segments:
  `flat:300|301;stair:500;flat:400|401`.
- Stair segment goals are sent through the dedicated `/stair_exec` Action.
- The runtime reports stable final result keys:
  - `MISSION_SUCCEEDED`
  - `MISSION_FAILED`
  - `MISSION_CANCELED`
  - `MISSION_TIMEOUT`
  - `ROUTE_UNAVAILABLE`
  - `CONNECTOR_UNAVAILABLE`
- Route action unavailability and connector/segment unavailability are
  represented as explicit mission-level diagnostics.
- The verifier leaves no matched `phase4b_mission`, `go2w_command_gate`,
  `go2w_stair_executor`, `route_server`, or `ros2 launch go2w_mission`
  process after cleanup.

## Verification Evidence
Timestamp: `2026-05-01T01:12+08:00`

Static syntax check:

```bash
bash -n tools/verify_phase4b_mission_segments.sh
```

Result: passed with exit code `0`.

Focused Phase 4B unit tests:

```bash
PYTHONPATH=go2w_mission python3 -m pytest \
  go2w_mission/test/test_phase4b_mission_segments.py \
  go2w_mission/test/test_phase4b_mission_runtime.py \
  -q
```

Result:

```text
7 passed in 0.01s
```

Package build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
```

Result:

```text
Summary: 3 packages finished [1.01s]
```

Package tests:

```bash
source /opt/ros/humble/setup.bash
colcon test --packages-select go2w_control go2w_mission go2w_navigation
colcon test-result --verbose
```

Result:

```text
Summary: 44 tests, 0 errors, 0 failures, 0 skipped
```

Runtime acceptance:

```bash
./tools/verify_phase4b_mission_segments.sh
```

Key output:

```text
phase4b_mission_segments_result: RUNNING
node_/route_server: PRESENT
node_/go2w_command_gate: PRESENT
node_/go2w_stair_executor: PRESENT
action_/compute_route: PRESENT
action_/stair_exec: PRESENT
mission_success: PASS
mission_failure: PASS
mission_cancel: PASS
mission_timeout: PASS
mission_route_unavailable: PASS
mission_connector_unavailable: PASS
phase4b_mission_segments_result: PASS
```

The runtime evidence directory for that run was:

```text
/tmp/go2w_phase4b_mission_segments_21884
```

## Reproduction Command
From the repository root:

```bash
./tools/verify_phase4b_mission_segments.sh
```

The script builds `go2w_control`, `go2w_mission`, and `go2w_navigation`, sources
the local install space, starts the minimal Phase 4B-min launch path, checks
nodes and actions, then exercises all six expected mission result categories.

## Open Validation Items
- Flat segments are diagnostic placeholders; they do not run a real Nav2
  `NavigateToPose` or route-tracking controller.
- The runtime is a one-shot verifier CLI, not a long-running production Mission
  Orchestrator API.
- No Gazebo physics or real stair kinematics are exercised.
- No real Unitree Go2W model is loaded.
- No `map_server`, AMCL, or `map -> odom` localization chain is introduced.
- No automatic stair detection, traversability, or automatic connector
  generation is implemented.
