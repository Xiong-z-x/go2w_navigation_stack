# Architecture State

## Purpose
This document is the single source of truth for the current implementation state of the Go2W cross-floor navigation stack.
It records the active phase, the frozen contracts, the open decisions, and the only approved next task boundary.

## Current Phase
- Active Phase: `Phase 2`
- Phase Status: Phase 1 simulation controllability is closed on a stable software-rendering baseline; the next approved task is FAST-LIO2 odometry and mapping output integration.

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
- Stair traversal command entry type: dedicated staircase execution `Action`
- Stair traversal must remain a dedicated behavior-level interface and must not be tunneled through `cmd_vel`.

## Current Unresolved Items
- TF authority publisher allocation is not fixed yet and must be assigned explicitly before perception and navigation integration.

## Current Repository State
- The repository is treated as a standalone colcon monorepo root inside an outer workspace `src/`.
- ROS 2 packages are placed directly under the repository root.
- Environment Constraint: The system strictly uses the official default Gazebo Fortress (ros-humble-ros-gz-*) and ign_ros2_control to ensure compatibility in ROS 2 Humble. Do not use Garden or Harmonic.
- Environment Constraint: GPU acceleration for Gazebo GUI under WSLg is disabled due to Ogre2 UnimplementedException. System relies on software rendering (`use_gpu:=false`) to guarantee stability.
- The following root-level packages exist:
  - `go2w_description`
  - `go2w_sim`
  - `go2w_control`
  - `go2w_perception`
  - `go2w_navigation`
  - `go2w_mission`
- `go2w_description` now provides a minimal diff-drive placeholder URDF, RViz configuration, and a `robot_state_publisher` launch path.
- `go2w_sim` now provides a minimal empty-world Gazebo Sim launch path, a `ros_gz_sim`-based spawn path, `/clock` bridge startup, and `gz_ros2_control` controller orchestration.
- `go2w_control`, `go2w_perception`, `go2w_navigation`, and `go2w_mission` remain scaffold-only.
- A Phase 1 placeholder closed loop is now verified: `/cmd_vel` drives the simulated base, `joint_state_broadcaster` and `diff_drive_controller` are active, RViz can visualize the robot model, and TF remains consistent.
- FAST_LIO integration, Nav2 configuration, mission logic, and staircase behavior implementation do not exist yet.

## Only Allowed Next Task
- The next allowed task must enter `Phase 2`.
- Goal: integrate FAST-LIO2 input/output plumbing in simulation and obtain stable odometry plus point-cloud/map output without pulling in Nav2 or mission logic.
- Forbidden in that next task unless explicitly approved: Nav2, `nav2_route`, route graph authoring, mission orchestration, and staircase execution logic.
