# Architecture State

## Purpose
This document is the single source of truth for the current implementation state of the Go2W cross-floor navigation stack.
It records the active phase, the frozen contracts, the open decisions, and the only approved next task boundary.

## Current Phase
- Active Phase: `Phase 3`
- Phase Status: Phase 3 is accepted on the current `main` baseline. FAST-LIO2 input/output plumbing, perception-side `odom -> base_link` TF authority, longer-window perception stability, the first Nav2 costmap consumer gate, the first minimal same-floor Nav2 navigation closed loop, the first minimal `nav2_route` / manual route graph baseline, and Phase 3C hardening assets are accepted. Do not enter Phase 4 runtime behavior without a separate complete task card.

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
- Phase 2 is accepted as complete: `/fastlio/input/lidar_points` carries `time`, patched FAST-LIO runs no-TF, contract topics publish project frame semantics, `go2w_perception` owns `odom -> base_link`, longer-window perception stability passed, and standalone Nav2 costmap consumes `/go2w/perception/cloud_body`.
- FAST_LIO_ROS2 remains an external dependency and is not vendored into this repository. Phase 3C replaces the previous `/tmp` default with a pinned dependency lock and ignored repo-local cache under `.go2w_external/`; operators may still override paths through environment variables.
- The Phase 2H costmap consumer uses the Humble standalone `nav2_costmap_2d` lifecycle node `/costmap/costmap`. Phase 3A separately introduced the conventional full-stack local/global costmap paths; these remain distinct evidence gates and must not be conflated.
- Phase 3A full Nav2 bringup intentionally runs in `odom` without publishing a temporary `map -> odom` edge. This preserves the long-term localization/map authority boundary while proving the immediate same-floor closed loop.
- Phase 3B route graph baseline also runs in `odom`, using a hand-authored GeoJSON graph loaded by `nav2_route` `route_server`; it does not publish TF and does not add mission, stair, multi-floor, elevation, or traversability behavior.
- Phase 3C adds a persistent `map` frame, floor-aware hospital route graph and map metadata baseline. It uses floor-atlas coordinates plus `floor_id` / `connector_id` metadata to avoid 2D projection ambiguity. This is an asset and contract baseline only; it does not add mission orchestration, stair executor runtime, elevation mapping, traversability, automatic connector generation, `map_server`, or AMCL.
- Phase 3C adds a non-default multi-floor hospital Gazebo world asset for later Phase 4 staircase handoff tests. The default `empty_world.sdf` and placeholder model launch path remain unchanged.
- The default Phase 1 empty world remains the default `go2w_sim` world. Phase 3A adds a dedicated feature-rich verification world because the empty world is too degenerate for FAST-LIO-backed motion feedback.
- The placeholder URDF still couples robot geometry, `gz_ros2_control`, and sensor declarations in one file. This remains accepted technical debt and must be handled by a future dedicated refactor task; it is not part of Phase 3A/3B acceptance.

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
- `go2w_sim` now provides a minimal empty-world Gazebo Sim launch path, a backward-compatible optional `world` / `world_name` launch override, a Phase 3A feature-rich verification world, a Phase 3C multi-floor hospital verification world, a `ros_gz_sim`-based spawn path, `/clock` bridge startup, and `gz_ros2_control` controller orchestration.
- `go2w_perception` now contains Phase 2E local FAST-LIO contract adapters, Phase 2F TF authority activation, config, launch, and tests.
- `go2w_navigation` now contains a Phase 2H standalone Nav2 costmap consumer config and launch, a Phase 3A minimal same-floor Nav2 planner/controller/BT bringup, a Phase 3B minimal `nav2_route` route server plus manual same-floor GeoJSON route graph, and Phase 3C persistent multi-floor route graph / map metadata assets. Mission logic and staircase behavior are not implemented yet.
- `go2w_control` and `go2w_mission` remain scaffold-only.
- Phase 1 uses a software-rendering Gazebo baseline and now reserves `odom -> base_link` for later FAST-LIO ownership by disabling `diff_drive_controller` TF publication.
- Phase 1 simulation is expected to publish `robot_description`, `/clock`, `/imu`, and `/lidar_points`, while RViz visualizes the robot model, TF sensor frames, and point cloud data without consuming perception outputs.
- Repository-local FAST-LIO integration is accepted through Phase 3C. Current work covers pinned external-source patching, build validation, no-TF dry-run automation, local input/output contract adapters, perception-side `odom -> base_link` TF activation, longer-window perception output stability, a standalone Nav2 costmap consumer gate, a minimal same-floor Nav2 closed loop, a minimal same-floor `nav2_route` graph baseline, and Phase 3C multi-floor map/route/world hardening assets. Mission logic and staircase behavior implementation do not exist yet.

## Only Allowed Next Task
- The current project state remains formally in `Phase 3` until a separate Phase 4A task card starts.
- Phase 2A has audited the existing `/lidar_points` and `/imu` simulation outputs against FAST-LIO2 input expectations.
- Phase 2B has audited the external FAST_LIO_ROS2 build and no-TF dry-run gate.
- Phase 2C has added and verified a repository-local external patch gate for FAST_LIO_ROS2: `FAST_LIO_ENABLE_LIVOX=OFF` builds successfully in a scratch workspace, and FAST-LIO TF publication is parameter-gated off by default.
- Phase 2D has added and verified automated external preparation plus no-TF runtime dry-run scripts for patched FAST_LIO_ROS2.
- Phase 2E has added and verified local `go2w_perception` contract adapters: FAST-LIO input pointclouds carry `time`, contract outputs use project frame IDs, and no TF is published.
- Phase 2F has added and verified a local `go2w_perception` TF authority node: `odom -> base_link` is published from `/go2w/perception/odom`, pre-activation duplicate authority checks pass, and FAST-LIO upstream `camera_init -> body` TF remains absent.
- Phase 2G has added and verified a perception runtime stability acceptance script for the activated odometry, TF, point cloud, path, and map outputs.
- Phase 2H has added and verified the first Nav2 costmap consumer gate: standalone `/costmap/costmap` consumes `/go2w/perception/cloud_body`, publishes `/costmap/costmap` in `odom`, and does not start planner, controller, BT, route, mission, stair, elevation, or traversability nodes.
- Phase 3A has added and verified the first minimal same-floor Nav2 navigation closed loop: planner, controller, and BT Navigator reach lifecycle `active`; local and global costmaps consume `/go2w/perception/cloud_body`; `/navigate_to_pose` succeeds on a short `odom`-frame goal; Nav2 publishes `/cmd_vel`; perception odometry changes; `odom -> base_link` remains perception-owned; no temporary `map -> odom`, `nav2_route`, route graph, mission, stair, elevation, or traversability nodes are introduced.
- Phase 3B has added and verified the first minimal `nav2_route` / manual route graph baseline: `route_server` reaches lifecycle `active`; `/route_server/set_route_graph` reloads the installed GeoJSON graph; `/compute_route` succeeds from node `0` to node `3`; returned `Route` and `Path` frames are `odom`; `/route_graph` publishes `visualization_msgs/msg/MarkerArray` in `odom`; no mission, stair, multi-floor, elevation, traversability, `map_server`, or `amcl` nodes are introduced.
- Phase 3C has added and verified hardening assets: FAST-LIO external dependency preparation uses a pinned lock and ignored repo-local cache instead of `/tmp` defaults; `route_server` loads a persistent floor-aware hospital graph in `map` and computes a route from node `100` to node `202` across manual connector edge `500`; a non-default multi-floor hospital Gazebo world launches headless through the existing Fortress-only path and publishes `/clock`, `/imu`, and `/lidar_points`.
- `odom -> base_link` is now claimed only by the perception TF authority path, and navigation may consume it from Phase 3 onward.
- Runtime acceptance evidence is recorded in `docs/verification/phase1_runtime_acceptance.md` and can be replayed with `tools/verify_phase1_runtime.sh`.
- Phase 2A input-audit evidence is recorded in `docs/verification/phase2_fastlio_input_audit.md`.
- Phase 2B external FAST-LIO2 dry-run-gate evidence is recorded in `docs/verification/phase2_fastlio_dryrun.md`.
- Phase 2C external FAST-LIO2 patch-gate evidence is recorded in `docs/verification/phase2_fastlio_patch_gate.md`.
- Phase 2D external FAST-LIO2 no-TF runtime dry-run evidence is recorded in `docs/verification/phase2_fastlio_no_tf_dryrun.md`.
- Phase 2E FAST-LIO input/output contract stabilization evidence is recorded in `docs/verification/phase2_fastlio_contract_stabilization.md`.
- Phase 2F perception TF authority activation evidence is recorded in `docs/verification/phase2_tf_authority_activation.md`.
- Phase 2G perception runtime stability acceptance evidence is recorded in `docs/verification/phase2_perception_stability_acceptance.md`.
- Phase 2H Nav2 costmap consumer evidence is recorded in `docs/verification/phase2_costmap_consumer_gate.md`.
- Phase 2 total acceptance evidence is recorded in `docs/verification/phase2_runtime_acceptance.md`.
- Phase 3A Nav2 same-floor evidence is recorded in `docs/verification/phase3a_nav2_same_floor.md`.
- Phase 3B route graph baseline evidence is recorded in `docs/verification/phase3b_route_graph_baseline.md`.
- Phase 3 total acceptance evidence is recorded in `docs/verification/phase3_runtime_acceptance.md`.
- Phase 3C hardening evidence is recorded in `docs/verification/phase3c_hardening_acceptance.md`.
- The next implementation boundary is Phase 4A only after an explicit complete task card: introduce the smallest staircase state-machine handoff skeleton needed to prove control ownership transitions, without real multi-floor autonomy, elevation mapping, traversability, automatic stair detection, or changes to the perception-owned `odom -> base_link` authority.
- Forbidden in the next task unless explicitly approved by its task card: production mission orchestration, real staircase traversal controller tuning, multi-floor autonomous behavior, elevation mapping, traversability, automatic stair connector generation, and any change to the perception-owned `odom -> base_link` authority.
