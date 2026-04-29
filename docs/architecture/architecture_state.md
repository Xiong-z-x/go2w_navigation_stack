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
- TF authority handoff is now activated in a Phase 2F perception runtime dry-run: `diff_drive_controller` does not publish `odom -> base_link`, and `go2w_perception` publishes that edge from the stabilized Phase 2E contract odometry. Longer runtime stability acceptance is still open before Nav2 work starts.
- Phase 2A input audit found that `/lidar_points` provides `x,y,z,intensity,ring` but no per-point timing field. The next perception task must choose either a minimal adapter or a validated FAST-LIO2 configuration that can tolerate this simulation data shape.
- Phase 2B external FAST-LIO2 dry-run gate found that the current candidate ROS 2 wrapper requires `livox_ros_driver2` at build time and contains hard-coded TF publication (`camera_init -> body`). A no-TF runtime dry-run is therefore blocked until the external dependency chain and TF-disable strategy are explicitly handled.
- Phase 2C external patch gate cleared that immediate build/no-TF blocker: the repository now carries an external FAST_LIO_ROS2 patch that makes Livox support optional and gates FAST-LIO TF publication behind `publish.tf_publish_en`, defaulting to `false`.
- Phase 2D external no-TF runtime dry-run cleared the next runtime gate: patched FAST-LIO launched against `/lidar_points` and `/imu`, produced `/Odometry`, `/cloud_registered`, `/cloud_registered_body`, `/Laser_map`, and `/path`, and did not publish `camera_init -> body` TF. However, the FAST-LIO log still reports missing pointcloud `time` fields, and output message frames remain upstream `camera_init/body`; this is not yet stable enough to claim `odom -> base_link`.
- Phase 2E contract stabilization cleared the Phase 2D input/output blockers: `/fastlio/input/lidar_points` now carries a `time` field, FAST-LIO missing-time warnings are zero in the verifier, and raw FAST-LIO `camera_init/body` messages are republished on project contract topics with `odom/base_link` message frame semantics. Phase 2E still does not publish or claim `odom -> base_link` TF.
- Phase 2F TF authority activation dry-run cleared the first authority gate: pre-activation simulation TF has no `odom -> base_link`, runtime `diff_drive_controller.enable_odom_tf` is `False`, patched FAST-LIO does not publish `camera_init -> body`, and `go2w_perception` publishes `odom -> base_link` from `/go2w/perception/odom`.
- Phase 2G perception runtime stability acceptance cleared the longer-window baseline gate: during a 30 second command window, contract odometry, TF, adapted lidar, registered cloud, path, body cloud, and laser map outputs remained available; FAST-LIO missing-time warnings stayed zero; `camera_init -> body` stayed absent; and `odom -> base_link` stayed present from perception.
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
- `go2w_perception` now contains Phase 2E local FAST-LIO contract adapters, config, launch, and tests.
- `go2w_control`, `go2w_navigation`, and `go2w_mission` remain scaffold-only.
- Phase 1 uses a software-rendering Gazebo baseline and now reserves `odom -> base_link` for later FAST-LIO ownership by disabling `diff_drive_controller` TF publication.
- Phase 1 simulation is expected to publish `robot_description`, `/clock`, `/imu`, and `/lidar_points`, while RViz visualizes the robot model, TF sensor frames, and point cloud data without consuming perception outputs.
- Repository-local FAST-LIO TF authority activation now exists as a Phase 2F dry-run node and verifier, and Phase 2G has accepted the current perception runtime stability baseline. Current FAST-LIO work covers external-source patching, build validation, no-TF dry-run automation, local input/output contract adapters, perception-side `odom -> base_link` TF activation, and longer-window perception output stability. Nav2 configuration, mission logic, and staircase behavior implementation do not exist yet.

## Only Allowed Next Task
- The current project state is now formally in `Phase 2`.
- Phase 2A has audited the existing `/lidar_points` and `/imu` simulation outputs against FAST-LIO2 input expectations.
- Phase 2B has audited the external FAST_LIO_ROS2 build and no-TF dry-run gate.
- Phase 2C has added and verified a repository-local external patch gate for FAST_LIO_ROS2: `FAST_LIO_ENABLE_LIVOX=OFF` builds successfully in a scratch workspace, and FAST-LIO TF publication is parameter-gated off by default.
- Phase 2D has added and verified automated external preparation plus no-TF runtime dry-run scripts for patched FAST_LIO_ROS2.
- Phase 2E has added and verified local `go2w_perception` contract adapters: FAST-LIO input pointclouds carry `time`, contract outputs use project frame IDs, and no TF is published.
- Phase 2F has added and verified a local `go2w_perception` TF authority node: `odom -> base_link` is published from `/go2w/perception/odom`, pre-activation duplicate authority checks pass, and FAST-LIO upstream `camera_init -> body` TF remains absent.
- Phase 2G has added and verified a perception runtime stability acceptance script for the activated odometry, TF, point cloud, path, and map outputs.
- The only allowed Phase 2 direction remains the first perception baseline task: FAST-LIO2 input/output plumbing plus later `odom -> base_link` TF authority activation.
- The next implementation boundary is the first Nav2/costmap consumer gate: only consume the verified Phase 2 perception outputs in a minimal costmap-facing integration/audit task.
- `odom -> base_link` is now claimed only by the Phase 2F perception TF authority path, and Phase 2G has provided longer-window runtime stability evidence. Navigation may consume it only after a separate, explicit Nav2/costmap task card.
- Runtime acceptance evidence is recorded in `docs/verification/phase1_runtime_acceptance.md` and can be replayed with `tools/verify_phase1_runtime.sh`.
- Phase 2A input-audit evidence is recorded in `docs/verification/phase2_fastlio_input_audit.md`.
- Phase 2B external FAST-LIO2 dry-run-gate evidence is recorded in `docs/verification/phase2_fastlio_dryrun.md`.
- Phase 2C external FAST-LIO2 patch-gate evidence is recorded in `docs/verification/phase2_fastlio_patch_gate.md`.
- Phase 2D external FAST-LIO2 no-TF runtime dry-run evidence is recorded in `docs/verification/phase2_fastlio_no_tf_dryrun.md`.
- Phase 2E FAST-LIO input/output contract stabilization evidence is recorded in `docs/verification/phase2_fastlio_contract_stabilization.md`.
- Phase 2F perception TF authority activation evidence is recorded in `docs/verification/phase2_tf_authority_activation.md`.
- Phase 2G perception runtime stability acceptance evidence is recorded in `docs/verification/phase2_perception_stability_acceptance.md`.
- Forbidden in that next task unless explicitly approved: `nav2_route`, route graph authoring, mission orchestration, staircase execution logic, and multi-floor behavior.
