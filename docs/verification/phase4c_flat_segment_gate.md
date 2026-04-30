# Phase 4C-Min Flat Segment Execution Gate Acceptance

## Scope
Phase 4C-min replaces the Phase 4B print-only flat segment placeholder with a
navigation-owned flat segment execution gate. The mission runtime now calls a
standard `nav2_msgs/action/NavigateToPose` Action for each flat segment, then
continues to the dedicated `/stair_exec` Action for stair segments.

This is not production Mission Orchestrator, real route tracking against robot
motion, real cross-floor autonomous navigation, real stair locomotion tuning,
`map_server`, AMCL, `map -> odom` localization, elevation mapping,
traversability analysis, automatic stair detection, or automatic connector
generation.

## Implemented Runtime Surface
- `go2w_navigation_runtime.flat_nav_executor` provides a navigation-owned
  verifier implementation of the standard `/navigate_to_pose` Action surface.
- `go2w_flat_nav_executor` publishes flat command ownership through the existing
  command gate path:
  - `/go2w/control/command_owner = flat`
  - `/go2w/control/flat_cmd_vel`
- `go2w_mission.phase4b_mission_runtime` now sends each flat segment to the
  configured `NavigateToPose` Action instead of treating it as a print-only
  placeholder.
- Stair segments still use the dedicated `/stair_exec` Action.
- `tools/verify_phase4c_flat_segment_gate.sh` verifies the sequence and flat
  error modes in an isolated ROS domain.

## Verified Facts
- The mission runtime observes a full `flat -> stair -> flat` sequence on the
  Phase 3C route `100 -> 202`.
- The success path reaches `MISSION_SUCCEEDED`.
- The success path reports two `phase4c_state: FLAT_SEGMENT_SUCCEEDED` events.
- The success path reports one `phase4b_state: STAIR_SEGMENT_SUCCEEDED` event.
- Flat Action abort maps to `FLAT_NAV_FAILED`.
- Flat Action cancellation maps to `MISSION_CANCELED`.
- Flat Action timeout maps to `MISSION_TIMEOUT`.
- Missing flat Action server maps to `FLAT_NAV_UNAVAILABLE`.
- Phase 4A and Phase 4B runtime verifiers still pass after the Phase 4C change.
- Package-level tests for `go2w_navigation`, `go2w_control`, and `go2w_mission`
  pass with no failures.

## Verification Evidence
Timestamp: `2026-05-01T01:51+08:00`

Static syntax check:

```bash
bash -n tools/verify_phase4c_flat_segment_gate.sh
```

Result: passed with exit code `0`.

Focused Phase 4C unit tests:

```bash
PYTHONPATH=go2w_navigation python3 -m pytest \
  go2w_navigation/test/test_phase4c_flat_nav_executor.py \
  -q
```

Result:

```text
3 passed in 0.01s
```

Focused mission runtime tests:

```bash
PYTHONPATH=go2w_mission python3 -m pytest \
  go2w_mission/test/test_phase4b_mission_runtime.py \
  -q
```

Result:

```text
5 passed in 0.01s
```

Package build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_navigation go2w_control go2w_mission
```

Result:

```text
Summary: 3 packages finished [0.71s]
```

Package tests:

```bash
source /opt/ros/humble/setup.bash
colcon test --packages-select go2w_navigation go2w_control go2w_mission
colcon test-result --verbose
```

Result:

```text
Summary: 50 tests, 0 errors, 0 failures, 0 skipped
```

Phase 4A regression:

```bash
timeout 120s ./tools/verify_phase4a_stair_handoff.sh
```

Key result:

```text
phase4a_stair_handoff_result: PASS
```

Phase 4B regression:

```bash
./tools/verify_phase4b_mission_segments.sh
```

Key result:

```text
phase4b_mission_segments_result: PASS
```

Phase 4C runtime acceptance:

```bash
./tools/verify_phase4c_flat_segment_gate.sh
```

Key output:

```text
phase4c_flat_segment_gate_result: RUNNING
node_/route_server: PRESENT
node_/go2w_command_gate: PRESENT
node_/go2w_stair_executor: PRESENT
node_/go2w_flat_nav_executor: PRESENT
action_/compute_route: PRESENT
action_/navigate_to_pose: PRESENT
action_/stair_exec: PRESENT
mission_success: PASS
flat_segment_success_count: 2
stair_segment_success_observed: PASS
mission_flat_failure: PASS
mission_flat_cancel: PASS
mission_flat_timeout: PASS
mission_flat_unavailable: PASS
phase4c_flat_segment_gate_result: PASS
```

The runtime evidence directories for these runs were:

```text
/tmp/go2w_phase4a_stair_handoff_3814
/tmp/go2w_phase4b_mission_segments_4942
/tmp/go2w_phase4c_flat_segment_gate_3231
```

After hardening the verifier-generated `ROS_DOMAIN_ID` range to stay below the
Fast-DDS unsafe upper range, the Phase 4C runtime verifier was replayed at
`2026-05-01T02:17+08:00` with:

```text
ros_domain_id: 196
phase4c_flat_segment_gate_result: PASS
```

The replay evidence directory was:

```text
/tmp/go2w_phase4c_flat_segment_gate_10686
```

## Reproduction Command
From the repository root:

```bash
./tools/verify_phase4c_flat_segment_gate.sh
```

The script builds `go2w_navigation`, `go2w_control`, and `go2w_mission`, sources
the local install space, starts the Phase 4 route server, command gate, stair
executor, and flat navigation executor, then verifies success and flat error
paths.

## Open Validation Items
- Flat execution is still a navigation-owned verifier skeleton, not real Nav2
  route tracking against robot motion.
- The runtime is still a one-shot CLI path, not a production Mission
  Orchestrator API.
- No Gazebo physics or real stair kinematics are exercised.
- No real Unitree Go2W model is loaded.
- No `map_server`, AMCL, or `map -> odom` localization chain is introduced.
- No automatic stair detection, traversability, or automatic connector
  generation is implemented.
