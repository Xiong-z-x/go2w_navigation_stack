# Architecture State

## Purpose
This document is the single source of truth for the current implementation state of the Go2W cross-floor navigation stack.
It records the active phase, the frozen contracts, the open decisions, and the only approved next task boundary.

## Current Phase
- Active Phase: `Phase 0`
- Phase Status: architecture boundaries are being frozen first; Phase 0 audit closure is pending explicit acceptance after document review.

## Current Document Status

### Frozen Documents
- `docs/architecture/system_blueprint.md`
- `docs/architecture/interface_contracts.md`

### Active Coordination Documents
- `AGENTS.md`
- `docs/agent_collaboration_policy.md`
- `docs/architecture/architecture_state.md`

### Pending Or Incomplete Documentation
- `README.md` is still minimal and is not a source of truth for architecture or execution status.

## Current Unique Blueprint File
- The only canonical blueprint file is `docs/architecture/system_blueprint.md`.

## Current Frozen Interfaces

### TF Baseline
- Canonical minimum TF chain: `map -> odom -> base_link`

### Flat-Ground Motion Entry
- Flat-ground navigation command entry: `cmd_vel`

### Stair Traversal Entry
- Stair traversal command entry name: `stair_exec`
- Stair traversal must remain a dedicated behavior-level interface and must not be tunneled through `cmd_vel`.

## Current Unresolved Items
- `stair_exec` final transport form is not fixed yet: `Action` or `Service` remains undecided.
- TF authority publisher allocation is not fixed yet and must be assigned explicitly before perception and navigation integration.

## Current Repository State
- The repository is treated as a standalone colcon monorepo root inside an outer workspace `src/`.
- ROS 2 packages are placed directly under the repository root.
- The following root-level scaffold packages now exist:
  - `go2w_description`
  - `go2w_sim`
  - `go2w_control`
  - `go2w_perception`
  - `go2w_navigation`
  - `go2w_mission`
- Current package state is scaffold-only; no URDF, Xacro, Gazebo world, bridge configuration, controller code, FAST_LIO integration, Nav2 configuration, mission logic, or staircase behavior implementation exists yet.

## Only Allowed Next Task
- The only allowed next task is the first `Phase 1` task.
- Scope must remain limited to `go2w_description` and `go2w_sim`.
- Goal: establish the minimum simulation bootstrap needed for a spawnable robot description path in Gazebo Sim and an observable description or TF chain, without pulling in later-phase subsystems.
- Forbidden in that task: `gz_ros2_control`, full `cmd_vel` control closure, FAST_LIO, Nav2, `nav2_route`, mission orchestration, and staircase execution logic.
