# Architecture State

## Purpose
This document is the single source of truth for the current implementation state of the Go2W cross-floor navigation stack.
It records the active phase, the frozen contracts, the open decisions, and the only approved next task boundary.

## Current Phase
- Active Phase: `Phase 2`
- Phase Status: Phase 1 simulation controllability has completed runtime acceptance and has been accepted on the current `main` baseline. The project now enters Phase 2 for FAST-LIO2 input/output plumbing and perception TF authority activation.

## Current Document Status

### Frozen Documents
- `docs/architecture/system_blueprint.md`
- `docs/architecture/interface_contracts.md`

### Active Coordination Documents
- `AGENTS.md`
- `docs/agent_collaboration_policy.md`
- `docs/architecture/architecture_state.md`

### Non-Canonical Documentation
- `README.md` is an operator-facing summary and is not a source of truth for architecture or execution status.

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
- Phase 2A input audit found that `/lidar_points` provides `x,y,z,intensity,ring` but no per-point timing field. The next perception task must choose either a minimal adapter or a validated FAST-LIO2 configuration that can tolerate this simulation data shape.
- Phase 2B external FAST-LIO2 dry-run gate found that the current candidate ROS 2 wrapper requires `livox_ros_driver2` at build time and contains hard-coded TF publication (`camera_init -> body`). A no-TF runtime dry-run is therefore blocked until the external dependency chain and TF-disable strategy are explicitly handled.
- The placeholder URDF still couples robot geometry, `gz_ros2_control`, and sensor declarations in one file. This is accepted as a Phase 1 technical debt for fast closed-loop progress and must be refactored in Phase 3.

## Current Repository State
- The repository is treated as a standalone colcon monorepo root inside an outer workspace `src/`.
- ROS 2 packages are placed directly under the repository root.
- Environment Constraint: The repository runtime baseline is now frozen as **Fortress-only** on ROS 2 Humble. The accepted simulator path is `ros_gz_sim` with `gz_version=6`, which launches `ign gazebo-6`, together with `gz_ros2_control`.
- Environment Constraint: Gazebo Harmonic mixed runtime packages (`gz-sim8`, `libgz-*`, `python3-gz-*`) and the `packages.osrfoundation.org` Gazebo runtime path are not part of the accepted project environment and must remain removed unless the human operator explicitly re-baselines the project.
- Environment Constraint: GPU acceleration for Gazebo Fortress rendering under WSLg remains unsupported for the accepted project baseline. The 2026-04-27 GPU re-baseline confirmed that the WSLg/NVIDIA GLX path is visible and RViz can initialize OpenGL 4.2, but `go2w_sim use_gpu:=true` still aborts in Gazebo/Ogre2 sensors/rendering with `GL3PlusTextureGpu::copyTo`. `use_gpu:=true` is not part of the current Gazebo runtime contract, and the stable Gazebo path remains software rendering (`use_gpu:=false`). RViz may use a process-local WSLg/NVIDIA OpenGL environment without changing the Gazebo rendering baseline. See `docs/verification/gazebo_gpu_rebaseline.md`.
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
- The current project state is now formally in `Phase 2`.
- Phase 2A has audited the existing `/lidar_points` and `/imu` simulation outputs against FAST-LIO2 input expectations.
- Phase 2B has audited the external FAST_LIO_ROS2 build and no-TF dry-run gate.
- The only allowed Phase 2 direction remains the first perception baseline task: FAST-LIO2 input/output plumbing plus later `odom -> base_link` TF authority activation.
- The next implementation boundary is Phase 2C: choose one narrow path before runtime launch: close the external `livox_ros_driver2` / Livox SDK dependency chain and add a no-TF FAST-LIO2 wrapper/patch strategy, or implement a minimal `go2w_perception` adapter plus validated FAST-LIO2 config/fork strategy for `/lidar_points` fields `x,y,z,intensity,ring` without per-point timing.
- `odom -> base_link` remains unclaimed until FAST-LIO2 runtime odometry is verified stable and duplicate TF authority is ruled out.
- Runtime acceptance evidence is recorded in `docs/verification/phase1_runtime_acceptance.md` and can be replayed with `tools/verify_phase1_runtime.sh`.
- Phase 2A input-audit evidence is recorded in `docs/verification/phase2_fastlio_input_audit.md`.
- Phase 2B external FAST-LIO2 dry-run-gate evidence is recorded in `docs/verification/phase2_fastlio_dryrun.md`.
- Forbidden in that next task unless explicitly approved: Nav2, `nav2_route`, route graph authoring, mission orchestration, and staircase execution logic.
