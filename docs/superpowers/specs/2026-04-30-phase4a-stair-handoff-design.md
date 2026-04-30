# Phase 4A Stair Handoff Design

## Status
Approved by the operator on 2026-04-30 as "方案 A".

## Goal
Start Phase 4A with the smallest staircase state-machine and control-ownership
handoff skeleton that advances the final cross-floor autonomy goal without
pretending that full cross-floor autonomy already exists.

The Phase 4A acceptance target is:

- use the Phase 3C manual route graph stair connector metadata;
- detect that a computed route crosses a `stair_exec_required` edge;
- prove flat navigation command ownership and stair execution command ownership
  are mutually exclusive;
- expose a dedicated `/stair_exec` Action skeleton with success, failure,
  cancel, and timeout outcomes;
- return command ownership to flat navigation after the stair segment completes.

## Architecture
The design keeps package boundaries aligned with the frozen contracts:

- `go2w_navigation` continues to own Nav2 and `nav2_route` assets. It may only
  receive a route graph consistency fix and Phase 4A verification support.
- `go2w_mission` owns the Phase 4A demo state machine because it decides when a
  route segment is flat or stair.
- `go2w_control` owns the final command arbitration and the dedicated
  staircase execution Action endpoint because it decides how locomotion mode is
  executed.

`stair_exec` remains a dedicated Action. It must not be implemented as a
service and must not be tunneled through raw `cmd_vel`.

## Selected Approach
Use a mission-owned route handoff demo plus a control-owned Action skeleton and
command gate.

1. Route acquisition:
   - call `/compute_route` from node `100` to node `202`;
   - read the installed Phase 3C route graph metadata;
   - identify stair edges by `mode: stair`, `connector_id`, and
     `stair_exec_required: true`.

2. Control ownership:
   - introduce a minimal command gate with two inputs:
     `/go2w/control/flat_cmd_vel` and `/go2w/control/stair_cmd_vel`;
   - publish the selected command to `/cmd_vel`;
   - support explicit owner state `flat` or `stair`;
   - reject simultaneous ownership by construction.

3. Stair execution:
   - expose `/stair_exec` as a ROS 2 Action;
   - simulate deterministic execution for the skeleton path;
   - emit feedback with current phase and progress;
   - support success, configured failure, cancel, and timeout behavior.

4. State machine:
   - start in `FLAT_ACTIVE`;
   - on stair edge entry, request `STAIR_ACTIVE` ownership;
   - call `/stair_exec`;
   - return to `FLAT_ACTIVE` on success;
   - enter diagnostic terminal states on failure, cancel, or timeout.

## Data Flow
The Phase 4A data path is intentionally minimal:

```text
Phase 3C route graph metadata
  -> go2w_mission Phase 4A handoff demo
  -> /stair_exec Action goal
  -> go2w_control stair executor skeleton
  -> command ownership gate
  -> /cmd_vel
```

Perception remains outside this task except as an existing accepted authority
for `odom -> base_link`. The task must not change TF publishers, FAST-LIO
adapters, map server behavior, or AMCL behavior.

## Error Handling
The skeleton must make failures diagnosable rather than silent:

- missing route graph file;
- route does not contain a stair edge;
- stair Action server unavailable;
- stair Action failure;
- cancel request;
- timeout while waiting for the stair Action result;
- invalid command owner transition;
- route graph geometry inconsistent with node IDs.

Each case should produce a stable verifier key so future agents can distinguish
contract failure from runtime instability.

## Testing
Verification must be scriptable and replayable:

- static JSON parse for the Phase 3C route graph;
- static check that each edge geometry starts at `startid` node coordinates and
  ends at `endid` node coordinates;
- build `go2w_control`, `go2w_mission`, and `go2w_navigation`;
- run package tests for the affected packages;
- run a Phase 4A verifier that demonstrates:
  - `/stair_exec` Action is available;
  - route `100 -> 202` crosses stair edge `500`;
  - success path switches `flat -> stair -> flat`;
  - while in stair owner mode, flat commands do not reach `/cmd_vel`;
  - while in flat owner mode, stair commands do not reach `/cmd_vel`;
  - failure, cancel, and timeout paths are reported with stable keys.

## Non-Goals
This task must not implement:

- production Mission Orchestrator;
- real multi-floor autonomous navigation;
- real stair traversal controller tuning;
- Unitree Go2W real model import;
- elevation mapping;
- traversability;
- automatic stair detection;
- automatic stair connector generation;
- `map_server`, AMCL, or `map -> odom` localization fusion;
- any change to perception-owned `odom -> base_link` authority;
- any Gazebo GPU re-baseline.

## Phase 4 Continuation
After Phase 4A passes, the next natural increments are:

- Phase 4B: connect the same ownership skeleton to `ComputeAndTrackRoute`
  feedback and/or a `nav2_route` Route Operation trigger.
- Phase 4C: run the handoff skeleton against the Phase 3C hospital world
  runtime scene.
- Phase 4D: replace skeleton stair motion with real stair executor control
  tuning under a separate task card.

Those future increments are not part of this design.

## Task Card

### Task Goal
Implement Phase 4A minimal staircase state-machine and control ownership handoff
skeleton.

### Current Phase
Accepted Phase 3 baseline entering Phase 4A only for the minimal handoff
skeleton.

### Allowed Files
- `go2w_control/package.xml`
- `go2w_control/CMakeLists.txt`
- `go2w_control/action/**`
- `go2w_control/scripts/**`
- `go2w_control/go2w_control/**`
- `go2w_control/test/**`
- `go2w_mission/package.xml`
- `go2w_mission/CMakeLists.txt`
- `go2w_mission/scripts/**`
- `go2w_mission/go2w_mission/**`
- `go2w_mission/launch/**`
- `go2w_mission/test/**`
- `go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson`
- `tools/verify_phase4a_stair_handoff.sh`
- `docs/verification/phase4a_stair_handoff_acceptance.md`
- `docs/architecture/architecture_state.md`
- `README.md`
- `docs/handoff/current_project_state.md`
- `docs/handoff/next_agent_notes.md`
- `docs/handoff/risk_cleanup_log.md`

### Forbidden Files
- `go2w_perception/**`
- `go2w_sim/**`
- `go2w_description/**`
- `.go2w_external/**`
- Gazebo world/model import files except documentation references
- Nav2 Phase 3A runtime behavior rewrites
- map server, AMCL, elevation, traversability, or automatic stair detection files

### Required Commands
```bash
./tools/verify_phase4_pre_handoff.sh
python3 -m json.tool go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson >/dev/null
bash -n tools/verify_phase4a_stair_handoff.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
colcon test --packages-select go2w_control go2w_mission go2w_navigation
colcon test-result --verbose
./tools/verify_phase4a_stair_handoff.sh
```

### Definition of Done
- `/stair_exec` is a ROS 2 Action endpoint.
- Route `100 -> 202` crosses manual stair edge `500`.
- Success path proves command ownership transitions `flat -> stair -> flat`.
- Failure, cancel, and timeout paths are diagnosable.
- Flat and stair command streams are mutually exclusive at `/cmd_vel`.
- No forbidden later-phase nodes or files are introduced.
- `docs/verification/phase4a_stair_handoff_acceptance.md` records fresh evidence.
- `architecture_state.md` and handoff notes state exactly what Phase 4A does
  and does not prove.

## Self-Review
- No placeholder sections remain.
- The design is scoped to one Phase 4A task.
- The Action-vs-service boundary is explicit.
- The design does not claim real cross-floor autonomy or real stair dynamics.
- Known route graph geometry risk is included in verification.
