# Phase 4B-Min Mission Segment Runtime Design

## Status
Approved by the operator on 2026-05-01 as "方案 A".

## Goal
Advance from the Phase 4A one-shot staircase handoff demo to the smallest
mission-owned route segment runtime. The runtime must compute the existing
manual multi-floor route, split it into ordered flat and stair segments, execute
the stair segment through the existing dedicated `/stair_exec` Action, and emit
stable diagnostic state keys.

This task moves the project closer to the final cross-floor goal by adding
mission-layer segmentation and orchestration evidence. It must not claim full
cross-floor autonomy.

## Current Baseline
Phase 4A is accepted. The current baseline already verifies:

- `route_server` computes a route from node `100` to node `202`.
- The route includes manual staircase connector edge `500`.
- `/stair_exec` is a dedicated Action endpoint.
- `go2w_control` command gate proves flat/stair command ownership is mutually
  exclusive.
- success, failure, cancel, and timeout outcomes are diagnosable.

The new work should reuse these contracts instead of replacing them.

## Architecture
The package boundary remains unchanged:

- `go2w_navigation` owns the route graph asset and `nav2_route` configuration.
- `go2w_mission` owns route interpretation, segment decomposition, mission
  state progression, and high-level recovery classification.
- `go2w_control` owns command arbitration and the `/stair_exec` Action server.

Phase 4B-min adds mission runtime structure only. It does not move navigation or
control implementation into `go2w_mission`.

## Selected Approach
Use a mission-owned one-shot runtime that turns a computed route into explicit
segments:

1. Request `/compute_route` from start node `100` to goal node `202`.
2. Read the installed Phase 3C graph metadata through the existing
   `Phase4ARouteGraph` helper.
3. Convert the returned route edge IDs into ordered mission segments:
   - contiguous non-stair edges become `flat` segments;
   - each `stair_exec_required` edge becomes one `stair` segment.
4. Execute flat segments as diagnostic stubs only:
   - publish stable status keys;
   - do not publish continuous motor commands;
   - do not claim Nav2 physical traversal.
5. Execute stair segments by sending `/stair_exec` goals using the existing
   Phase 4A Action contract.
6. Return a final mission result key:
   - `MISSION_SUCCEEDED`;
   - `MISSION_FAILED`;
   - `MISSION_CANCELED`;
   - `MISSION_TIMEOUT`;
   - `ROUTE_UNAVAILABLE`;
   - `CONNECTOR_UNAVAILABLE`.

This is intentionally one-shot and script-driven. A long-lived production
Mission Orchestrator is a later task.

## Data Flow

```text
Phase 3C graph metadata
  + /compute_route result
  -> go2w_mission segment builder
  -> go2w_mission one-shot mission runtime
  -> flat segment diagnostic states
  -> /stair_exec Action goal for stair segment
  -> final mission diagnostic result
```

## State Model
The minimal runtime uses observable string states:

- `ROUTE_REQUESTED`
- `ROUTE_COMPUTED`
- `SEGMENTS_READY`
- `FLAT_SEGMENT_ACTIVE`
- `FLAT_SEGMENT_SUCCEEDED`
- `STAIR_SEGMENT_ACTIVE`
- `STAIR_SEGMENT_SUCCEEDED`
- `MISSION_SUCCEEDED`
- `MISSION_FAILED`
- `MISSION_CANCELED`
- `MISSION_TIMEOUT`
- `ROUTE_UNAVAILABLE`
- `CONNECTOR_UNAVAILABLE`

The states are diagnostic output and verifier keys. They are not a frozen public
Action interface yet.

## Error Handling
The runtime must classify failures without silently absorbing them:

- missing or invalid graph geometry -> `CONNECTOR_UNAVAILABLE`;
- route action server unavailable -> `ROUTE_UNAVAILABLE`;
- route result unavailable or missing stair edge -> `CONNECTOR_UNAVAILABLE`;
- stair Action server unavailable -> `MISSION_FAILED`;
- stair Action result `FAILED` -> `MISSION_FAILED`;
- stair Action result `CANCELED` -> `MISSION_CANCELED`;
- stair result wait timeout -> `MISSION_TIMEOUT`.

Each case must have stable key-value output for replayable verification.

## Testing
Verification must be replayable from the repository root:

- unit tests for segment decomposition:
  - route `[300, 301, 500, 400, 401]` becomes `flat [300,301]`,
    `stair [500]`, `flat [400,401]`;
  - a route with no stair edge remains one flat segment;
  - missing edge IDs are rejected.
- unit tests for mission result classification.
- runtime verifier:
  - bounded Phase 4A verifier replay;
  - build affected packages;
  - launch route server, command gate, and stair executor;
  - run mission runtime modes: success, failure, cancel, timeout;
  - assert stable final result keys.

The verifier must use bounded timeouts. The 2026-05-01 lifecycle wait hang shows
that lifecycle/action probes must not wait indefinitely.

## Non-Goals
This task must not implement:

- production Mission Orchestrator;
- a new mission Action API;
- real Nav2 flat segment execution;
- real multi-floor autonomous navigation;
- real stair traversal controller tuning;
- Unitree Go2W real model import;
- elevation mapping;
- traversability;
- automatic stair detection;
- automatic stair connector generation;
- `map_server`, AMCL, or `map -> odom` localization fusion;
- changes to perception-owned `odom -> base_link`;
- changes to the `StairExec.action` contract.

## Task Card

### Task Goal
Implement Phase 4B-min mission segment runtime around the existing manual
staircase connector and Phase 4A `/stair_exec` skeleton.

### Current Phase
Accepted Phase 4A baseline entering Phase 4B-min only for minimal mission
segment runtime.

### Allowed Files
- `go2w_mission/go2w_mission/**`
- `go2w_mission/launch/**`
- `go2w_mission/scripts/**`
- `go2w_mission/test/**`
- `go2w_mission/CMakeLists.txt`
- `go2w_mission/package.xml`
- `tools/verify_phase4b_mission_segments.sh`
- `tools/verify_phase4a_stair_handoff.sh` only for bounded verifier hardening
- `docs/superpowers/specs/**`
- `docs/superpowers/plans/**`
- `docs/verification/**`
- `docs/architecture/architecture_state.md`
- `docs/handoff/**`
- `README.md`

### Forbidden Files
- `go2w_perception/**`
- `go2w_sim/**`
- `go2w_description/**`
- `.go2w_external/**`
- `go2w_control/action/StairExec.action`
- Nav2 Phase 3A planner/controller/BT rewrites
- `map_server`, AMCL, or `map -> odom` files
- elevation, traversability, automatic stair detection, or connector generation
- Unitree Go2W model import files

### Required Commands
```bash
./tools/verify_phase4_pre_handoff.sh
timeout 120s ./tools/verify_phase4a_stair_handoff.sh
bash -n tools/verify_phase4b_mission_segments.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
colcon test --packages-select go2w_control go2w_mission go2w_navigation
colcon test-result --verbose
./tools/verify_phase4b_mission_segments.sh
```

### Definition of Done
- route `100 -> 202` is split into ordered `flat`, `stair`, `flat` mission
  segments.
- the stair segment uses the existing `/stair_exec` Action.
- flat segments are diagnostic stubs and do not claim real Nav2 traversal.
- success, failure, cancel, timeout, route-unavailable, and
  connector-unavailable outcomes are diagnosable.
- no forbidden later-phase nodes or files are introduced.
- `docs/verification/phase4b_mission_segment_runtime.md` records fresh evidence.
- `architecture_state.md`, README, and handoff notes distinguish verified facts
  from open validation items.

## Self-Review
- No placeholder sections remain.
- The design is scoped to one Phase 4B-min task.
- Package ownership remains aligned with the frozen contracts.
- The design does not claim production orchestration, real flat navigation, real
  stair dynamics, or real cross-floor autonomy.
- The lifecycle verifier hang discovered on 2026-05-01 is accounted for through
  bounded runtime verification.
