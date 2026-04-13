# Architecture State

## Purpose
This document is the single source of truth for the current implementation state of the Go2W cross-floor navigation stack.
It records the active phase, the frozen contracts, the open decisions, and the only approved next task boundary.

## Current Phase
- Active Phase: `Phase 1`
- Phase Status: The current change set has completed Phase 1 runtime acceptance verification for simulation controllability, TF handoff preparation, and sensor observability. Once this verified baseline is accepted on `main`, Phase 2 may begin.

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
- TF authority handoff is now fixed in policy but not yet activated by perception: `diff_drive_controller` must not publish `odom -> base_link`, and FAST-LIO will take that edge when Phase 2 perception integration starts.
- The placeholder URDF still couples robot geometry, `gz_ros2_control`, and sensor declarations in one file. This is accepted as a Phase 1 technical debt for fast closed-loop progress and must be refactored in Phase 3.

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
- Phase 1 uses a software-rendering Gazebo baseline and now reserves `odom -> base_link` for later FAST-LIO ownership by disabling `diff_drive_controller` TF publication.
- Phase 1 simulation is expected to publish `robot_description`, `/clock`, `/imu`, and `/lidar_points`, while RViz visualizes the robot model, TF sensor frames, and point cloud data without consuming perception outputs.
- FAST_LIO integration, Nav2 configuration, mission logic, and staircase behavior implementation do not exist yet.

## Only Allowed Next Task
- The current change set has completed Phase 1 runtime acceptance verification; once it is accepted as the `main` baseline, the first Phase 2 task may integrate FAST-LIO2 input/output plumbing without pulling in Nav2 or mission logic.
- Runtime acceptance evidence is recorded in `docs/verification/phase1_runtime_acceptance.md` and can be replayed with `tools/verify_phase1_runtime.sh`.
- Forbidden in that next task unless explicitly approved: Nav2, `nav2_route`, route graph authoring, mission orchestration, and staircase execution logic.
