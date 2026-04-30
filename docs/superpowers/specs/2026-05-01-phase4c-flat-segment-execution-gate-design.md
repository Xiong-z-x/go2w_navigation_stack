# Phase 4C-Min Flat Segment Execution Gate Design

## Context
The current accepted baseline is `Phase 4B-min`. It computes the Phase 3C manual
hospital route, decomposes it into `flat:300|301;stair:500;flat:400|401`, and
dispatches the stair segment through the dedicated `/stair_exec` Action. Its
main remaining Phase 4 gap is explicit: flat segments are only diagnostic
placeholders.

The Phase 4 blueprint target is a staircase state-machine closed loop:

```text
flat navigation -> stair execution -> restored flat navigation
```

This task does not attempt to finish real cross-floor autonomy, production
mission orchestration, AMCL, `map_server`, `map -> odom`, real stair locomotion,
Unitree model import, elevation mapping, traversability, or automatic connector
generation.

## Self-Approved Task Card

1. **Task Goal**: Add a Phase 4C-min flat segment execution gate so the mission
   runtime calls a navigation-owned flat execution Action for each flat segment
   instead of treating flat segments as print-only placeholders.
2. **Current Phase**: `Phase 4B-min` accepted; this task advances to
   `Phase 4C-min`.
3. **Allowed Files**:
   - `go2w_navigation/CMakeLists.txt`
   - `go2w_navigation/package.xml`
   - `go2w_navigation/go2w_navigation_runtime/*`
   - `go2w_navigation/scripts/*`
   - `go2w_navigation/launch/*`
   - `go2w_navigation/test/*`
   - `go2w_mission/go2w_mission/phase4b_mission_runtime.py`
   - `go2w_mission/test/*`
   - `go2w_mission/launch/phase4b_mission_runtime.launch.py`
   - `tools/verify_phase4c_flat_segment_gate.sh`
   - Phase 4C docs and handoff/state files
4. **Forbidden Files**:
   - `go2w_perception/*`
   - `go2w_sim/*`
   - `go2w_description/*`
   - `go2w_control/action/StairExec.action`
   - Existing Phase 1/2/3 verification evidence except cross-links
   - Any file that introduces AMCL, `map_server`, elevation, traversability, or
     automatic connector generation into this task
5. **Required Commands**:
   - `bash -n tools/verify_phase4c_flat_segment_gate.sh`
   - `PYTHONPATH=go2w_navigation python3 -m pytest go2w_navigation/test/test_phase4c_flat_nav_executor.py -q`
   - `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase4b_mission_runtime.py -q`
   - `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_navigation go2w_control go2w_mission`
   - `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_navigation go2w_control go2w_mission`
   - `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
   - `./tools/verify_phase4c_flat_segment_gate.sh`
   - Existing Phase 4A/4B verifier regressions before final state update
6. **Definition of Done**:
   - A navigation-owned flat execution skeleton exists and exposes a standard
     `nav2_msgs/action/NavigateToPose` server for verification.
   - The mission runtime sends every flat segment to the configured flat
     navigation Action before proceeding.
   - The runtime executes and observes the sequence:
     `flat segment -> stair segment -> flat segment`.
   - Flat execution success, failure, cancellation, timeout, and unavailable
     action paths are mission-diagnosable.
   - Stair execution remains a dedicated `/stair_exec` Action.
   - The command gate still proves flat/stair command ownership mutual exclusion.
   - Documentation and handoff files clearly state Phase 4C-min is still not
     production Mission Orchestrator or real cross-floor autonomous navigation.

## Approach Options

### Option A: Full Nav2/Gazebo Flat Execution Now
Run the existing Phase 3A Nav2 stack and Gazebo/perception chain for each flat
segment in the Phase 3C `map` graph.

Rejected for this task. It would collide with the current lack of `map -> odom`
localization and risks turning Phase 4C into an AMCL/map_server or TF authority
task.

### Option B: Keep Flat Segments As Diagnostic Prints
Keep Phase 4B behavior and only add more status keys.

Rejected. It does not close the known Phase 4B gap and would not prove restored
flat navigation ownership after the stair segment.

### Option C: Navigation-Owned Flat Execution Gate
Add a minimal `go2w_navigation` runtime skeleton that exposes a standard
`nav2_msgs/action/NavigateToPose` Action server and publishes flat-owner
diagnostic commands through the existing command gate path. Update the mission
runtime to call this action for every flat segment.

Selected. It advances the Phase 4 state machine without changing frozen
interfaces. It keeps navigation-owned behavior in `go2w_navigation`, mission
sequencing in `go2w_mission`, and command arbitration in `go2w_control`.

## Architecture

### Navigation Layer
`go2w_navigation_runtime.flat_nav_executor` provides a replaceable verifier
implementation of the standard `NavigateToPose` Action surface. It is not a new
mission API and not a production controller. Its responsibility is to:

- accept a `NavigateToPose` goal,
- publish owner `flat` on `/go2w/control/command_owner`,
- publish a small diagnostic flat command on `/go2w/control/flat_cmd_vel`,
- support success, failure, cancel, and timeout modes for verifier coverage,
- return through standard action status/result semantics.

### Mission Layer
`Phase4BMissionRuntime` becomes a Phase 4C-compatible sequencer:

- route computation remains `/compute_route`,
- segmentation remains `build_mission_segments`,
- flat segments call a configurable `NavigateToPose` action,
- stair segments continue to call `/stair_exec`,
- mission-level result keys remain stable and add flat-specific diagnostics:
  `FLAT_NAV_UNAVAILABLE`, `FLAT_NAV_FAILED`, `MISSION_TIMEOUT`,
  `MISSION_CANCELED`.

The class name may remain `Phase4BMissionRuntime` for backward compatibility,
but diagnostics and docs will describe the Phase 4C behavior.

### Control Layer
No interface changes. The existing command gate continues to arbitrate:

- `flat` owner forwards `/go2w/control/flat_cmd_vel`,
- `stair` owner forwards `/go2w/control/stair_cmd_vel`,
- non-owned commands are muted.

## Data Flow

```text
route_server /compute_route
  -> go2w_mission route segmentation
  -> flat segment NavigateToPose action
  -> command gate owner=flat
  -> stair segment /stair_exec action
  -> command gate owner=stair then flat
  -> next flat segment NavigateToPose action
```

## Error Handling

- Missing `/compute_route`: `ROUTE_UNAVAILABLE`.
- No staircase connector in returned route: `CONNECTOR_UNAVAILABLE`.
- Missing flat navigation action server: `FLAT_NAV_UNAVAILABLE`.
- Flat action abort: `FLAT_NAV_FAILED`.
- Flat action cancel: `MISSION_CANCELED`.
- Flat action timeout: cancel the goal and report `MISSION_TIMEOUT`.
- Stair action failure, cancel, and timeout preserve Phase 4B result semantics.

## Verification

The new verifier must run in an isolated ROS domain, start route server, command
gate, stair executor, and the flat navigation executor. It must prove:

- all required nodes/actions are present,
- the mission sequence includes flat segment, stair segment, flat segment,
- success path reaches `MISSION_SUCCEEDED`,
- flat failure reaches `FLAT_NAV_FAILED`,
- flat cancel reaches `MISSION_CANCELED`,
- flat timeout reaches `MISSION_TIMEOUT`,
- missing flat action reaches `FLAT_NAV_UNAVAILABLE`,
- existing Phase 4A and Phase 4B verifiers still pass.

## Scope Guard

This design intentionally does not introduce:

- real `map -> odom` localization,
- AMCL or `map_server`,
- real route tracking against robot motion,
- physical stair locomotion,
- production Mission Orchestrator API,
- automatic stair detection or connector generation.

Those remain later tasks after Phase 4C-min is accepted.

## Self-Review
- Placeholder scan: no `TBD` or open placeholder remains.
- Consistency check: selected approach matches package ownership contracts.
- Scope check: single task, focused on flat segment execution gate only.
- Ambiguity check: verifier modes and result keys are explicit.
