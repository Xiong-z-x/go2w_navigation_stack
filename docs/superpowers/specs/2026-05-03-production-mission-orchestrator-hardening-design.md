# Production Mission Orchestrator Skeleton Hardening Design

## Goal
Harden the current `go2w_mission` skeleton without expanding it into a full production
Mission Orchestrator.

This pass focuses on two narrow but high-value fixes:

1. Keep flat-goal pose conversion canonical across mission code paths.
2. Preserve the existing single-flight admission gate as the minimal production-style
   concurrency boundary.

## Scope
### In scope
- Shared flat-goal pose conversion helper for mission code paths.
- `RunMission` single-flight admission gate behavior and diagnostics.
- Focused unit tests covering the shared helper and the two mission call sites.
- Documentation sync for the mission runtime and handoff state.

### Out of scope
- Multi-mission queueing.
- Priority scheduling.
- Operator pause/resume UX.
- Perception TF authority changes.
- `map_server` / AMCL / `map -> odom`.
- Stair dynamics or gait tuning.
- Terrain-aware connector generation.

## Design
### Flat-goal pose conversion
The mission runtime already builds flat goals from route-graph nodes.
The new design centralizes the final `PoseStamped` conversion in
`go2w_mission.mission_pose`.

This keeps:
- `phase4b_mission_runtime.py`
- `mission_api.py`

on the same yaw-to-quaternion path, which avoids regressions where one mission
path preserves route-graph orientation and the other silently degrades to a unit
quaternion.

### Admission gate
`MissionApiRuntime` continues to use a non-blocking mission slot backed by
`_mission_lock`.

The intended behavior is:
- first mission goal acquires the slot and executes normally;
- concurrent goals are rejected with `MISSION_BUSY` / `mission_state_in_use`;
- the slot is always released in `finally`.

This is a production-style hardening boundary, not a full queue.

## Validation
- `python3 -m py_compile` on the touched mission files.
- Focused `pytest` for the shared helper and mission API skeleton.
- `colcon build --symlink-install --packages-select go2w_mission`.
- `colcon test --packages-select go2w_mission`.
- `colcon test-result --verbose`.
- `git diff --check`.
- `tools/verify_go2w_mission_real_flat_execution.sh`.

## Done Definition
The pass is complete when:
- mission flat pose conversion is canonical and shared;
- mission API and Phase 4B runtime preserve the same yaw semantics;
- the single-flight admission gate remains stable;
- runtime evidence for mission real-flat execution still passes;
- docs stay aligned with the code.
