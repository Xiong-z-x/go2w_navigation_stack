# Phase 4A Stair Handoff Acceptance

## Scope
Phase 4A introduces the smallest staircase handoff runtime needed to prove that a
manual `nav2_route` staircase connector can trigger a dedicated stair execution
Action skeleton and that flat-ground and stair command ownership are mutually
exclusive.

This is not production mission orchestration, real stair locomotion tuning, real
cross-floor autonomy, elevation mapping, traversability analysis, automatic
stair detection, automatic connector generation, `map_server`, AMCL, or
`map -> odom` localization.

## Implemented Runtime Surface
- `go2w_control/action/StairExec.action` is the dedicated staircase behavior
  entry. It is an Action, not a service.
- `go2w_control_runtime.command_gate` arbitrates command ownership:
  - owner `flat` forwards `/go2w/control/flat_cmd_vel` to `/cmd_vel`
  - owner `stair` forwards `/go2w/control/stair_cmd_vel` to `/cmd_vel`
  - non-owned command streams are muted
- `go2w_control_runtime.stair_executor` provides the `/stair_exec` Action server
  skeleton, publishes observable command ownership, and now reuses the Go2W
  legged motion profile as a conservative stair-command baseline.
- `go2w_mission.phase4a_handoff_demo` uses the Phase 3C hospital route graph,
  calls `/compute_route`, detects the staircase connector edge, and calls
  `/stair_exec`.
- `go2w_mission/launch/phase4a_stair_handoff.launch.py` starts the minimal
  verifier stack: `route_server`, lifecycle manager, command gate, and stair
  executor.

## Verified Facts
- The Phase 3C multi-floor route graph geometry for edge `500` is internally
  consistent with its source and target nodes.
- `route_server` reaches lifecycle `active` and exposes `/compute_route`.
- `/compute_route` returns a route from node `100` to node `202` that includes
  staircase connector edge `500`.
- `/stair_exec` is present and returns diagnosable success, failure, cancel, and
  timeout outcomes.
- While owner is `flat`, flat commands can reach `/cmd_vel` and stair commands
  are muted.
- While owner is `stair`, stair commands can reach `/cmd_vel` and flat commands
  are muted.
- The verifier launches in a separate ROS domain and leaves no matched
  `phase4a_stair_handoff`, `go2w_command_gate`, `go2w_stair_executor`,
  `route_server`, or `ros2 launch go2w_mission` process after cleanup.

## Verification Evidence
Timestamp: `2026-05-01T00:27+08:00`

Static syntax check:

```bash
bash -n tools/verify_phase4a_stair_handoff.sh
```

Result: passed with exit code `0`.

Focused control unit tests:

```bash
PYTHONPATH=go2w_control python3 -m pytest \
  go2w_control/test/test_command_gate.py \
  go2w_control/test/test_stair_executor_policy.py \
  -q
```

Result:

```text
9 passed in 0.01s
```

Final package build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
```

Result:

```text
Summary: 3 packages finished [0.95s]
```

Final package tests:

```bash
source /opt/ros/humble/setup.bash
colcon test --packages-select go2w_control go2w_mission go2w_navigation
colcon test-result --verbose
```

Result:

```text
Summary: 35 tests, 0 errors, 0 failures, 0 skipped
```

Runtime acceptance:

```bash
./tools/verify_phase4a_stair_handoff.sh
```

Key output:

```text
phase4a_stair_handoff_result: RUNNING
node_/route_server: PRESENT
node_/go2w_command_gate: PRESENT
node_/go2w_stair_executor: PRESENT
route_server_lifecycle: active [3]
action_/compute_route: PRESENT
action_/stair_exec: PRESENT
command_gate_discovery: PASS
owner_flat_ack: PASS
flat_owner_flat_cmd: PASS
owner_stair_ack: PASS
stair_owner_flat_cmd_muted: PASS
stair_owner_stair_cmd: PASS
owner_flat_ack: PASS
flat_owner_stair_cmd_muted: PASS
command_gate_probe: PASS
handoff_success: PASS
handoff_failure: PASS
handoff_cancel: PASS
handoff_timeout: PASS
phase4a_stair_handoff_result: PASS
```

The runtime evidence directory for that run was:

```text
/tmp/go2w_phase4a_stair_handoff_14089
```

Cross-document handoff consistency check:

```bash
./tools/verify_phase4_pre_handoff.sh
```

Result:

```text
phase4_pre_handoff_result: PASS
```

## Reproduction Command
From the repository root:

```bash
./tools/verify_phase4a_stair_handoff.sh
```

The script builds `go2w_control`, `go2w_mission`, and `go2w_navigation`, sources
the local install space, starts the minimal Phase 4A launch path, checks nodes,
lifecycle, actions, command ownership, and the four expected stair execution
outcomes.

## Open Validation Items
- No Gazebo physics or real stair kinematics are exercised.
- No real Unitree Go2W model is loaded.
- No production Mission Orchestrator is implemented.
- No `map_server`, AMCL, or `map -> odom` localization chain is introduced.
- No automatic stair detection, traversability, or automatic connector
  generation is implemented.
- The staircase Action skeleton publishes only minimal diagnostic command
  behavior; it is not a tuned locomotion controller, even though it now clamps
  its stair baseline to the legged motion profile.
