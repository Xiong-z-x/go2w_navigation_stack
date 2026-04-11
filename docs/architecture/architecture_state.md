# Architecture State

## Purpose
This document is the single source of truth for the current implementation state of the Go2W cross-floor navigation stack.
It records the active phase, the repository layout, the frozen interface boundaries, and the next approved engineering step.

## Canonical References
- Blueprint: `docs/architecture/system_blueprint.md`
- Interface Contracts: `docs/architecture/interface_contracts.md`
- Collaboration Policy: `docs/agent_collaboration_policy.md`
- Agent Rules: `AGENTS.md`

## Current Phase
- Active Phase: `Phase 0`
- Phase Meaning: system boundaries and interface contracts are frozen first; no simulation, perception, navigation, or mission closed loop is implemented yet.

## Repository Layout Status
- Repository Role: this repository is treated as a standalone colcon monorepo root.
- Outer Workspace Note: the repository itself is located under an outer workspace `src/`, but no inner repository-level `src/` directory is used.
- Package Placement Policy: ROS 2 packages are placed directly under the repository root.

## Current Package Status
- `go2w_description`: scaffold only, no robot model assets yet
- `go2w_sim`: scaffold only, no Gazebo Sim world or bridge configuration yet
- `go2w_control`: scaffold only, no locomotion controller implementation yet
- `go2w_perception`: scaffold only, no FAST_LIO_ROS2 integration yet
- `go2w_navigation`: scaffold only, no Nav2 or `nav2_route` configuration yet
- `go2w_mission`: scaffold only, no mission orchestrator or staircase state machine yet

## Frozen Contracts Summary

### TF Contract
- Canonical minimum TF chain: `map -> odom -> base_link`
- Additional sensor frames must hang below `base_link`
- Duplicate authority over the same TF edge is not allowed without explicit approval

### Motion Entry Contract
- Flat-ground navigation enters through a normalized velocity-style command channel equivalent in role to `cmd_vel`
- Stair traversal must use a dedicated staircase execution Action or Service
- Stair traversal must not be tunneled through generic `cmd_vel`

### Layer Ownership Contract
- Mission decides when to switch behavior
- Navigation decides how to move within a floor
- Control executes the final locomotion mode switch
- Perception provides state and environment representation, but must not directly actuate locomotion

### Route Contract
- `nav2_route` is a graph routing and route tracking component
- `nav2_route` is not a 3D terrain traversal planner
- Staircase executor API must remain stable from Phase 4 to Phase 5

## Current Implementation Facts
- The repository currently contains architecture and collaboration documents plus Phase 0 package scaffolds
- No URDF, Xacro, Gazebo world, bridge configuration, controller code, FAST_LIO integration, Nav2 configuration, mission logic, or staircase behavior implementation exists yet
- The current repository state must be interpreted as boundary setup only, not as a runnable robot stack

## Explicit Path Decisions
- The only canonical blueprint file is `docs/architecture/system_blueprint.md`
- `docs/architecture/master_technical_blueprint.md` is not used as an active source of truth

## Phase 0 Exit Criteria Snapshot
Phase 0 is considered complete only when all of the following are true:
- package boundaries are frozen and reflected in repository structure
- `architecture_state.md` is initialized and usable as shared context
- the repository builds successfully as a minimal ROS 2 scaffold with `colcon build --symlink-install`
- no implementation code has crossed package ownership boundaries

## Next Recommended Single Task
- Phase 1 starter task should focus on simulation controllability only
- Recommended target: establish the minimum `go2w_description` and `go2w_sim` assets required to spawn the robot in Gazebo Sim and verify a future `cmd_vel` control path
- Do not pull FAST_LIO, Nav2, route graph, or staircase logic into that task
