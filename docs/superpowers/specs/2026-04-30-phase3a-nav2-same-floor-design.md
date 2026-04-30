# Phase 3A Nav2 Same-Floor Minimal Bringup Design

## Task Card

### Task Goal

Bring up the first full Nav2 same-floor navigation closed loop. The stack must
consume the accepted Phase 2 odometry, TF, and point-cloud perception contracts,
accept an `odom`-frame `NavigateToPose` goal, publish `/cmd_vel`, and move the
simulated base in Gazebo.

### Current Phase

`Phase 3A`: minimal same-floor Nav2 navigation bringup.

### Allowed Files

- `go2w_navigation/package.xml`
- `go2w_navigation/CMakeLists.txt`
- `go2w_navigation/config/**`
- `go2w_navigation/launch/**`
- `go2w_navigation/behavior_trees/**`
- `go2w_sim/worlds/phase3a_feature_world.sdf`
- `go2w_sim/launch/sim.launch.py` only to add a backward-compatible `world`
  launch argument
- `tools/verify_phase3a_nav2_same_floor.sh`
- `docs/superpowers/specs/**`
- `docs/superpowers/plans/**`
- `docs/verification/**`
- `docs/architecture/architecture_state.md`
- `README.md`

### Forbidden Files

- other `go2w_sim/**` behavior changes
- `go2w_description/**`
- `go2w_control/**`
- `go2w_mission/**`
- `go2w_perception/**` algorithm or launch/config behavior changes
- external FAST_LIO_ROS2 vendoring
- `nav2_route`, route graph, mission orchestration, staircase execution,
  multi-floor behavior, elevation mapping, or traversability implementation

### Required Commands

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_navigation go2w_perception go2w_description go2w_sim
bash -n tools/verify_phase3a_nav2_same_floor.sh
shellcheck tools/verify_phase3a_nav2_same_floor.sh
./tools/verify_phase3a_nav2_same_floor.sh
git status --short --branch
```

### Definition of Done

- `go2w_navigation` installs a Phase 3A Nav2 config, launch file, and minimal
  behavior tree.
- Nav2 lifecycle nodes `planner_server`, `controller_server`, and
  `bt_navigator` reach `active`.
- The Nav2 costmaps use `odom` and `base_link`, and consume
  `/go2w/perception/cloud_body` as PointCloud2 input.
- Runtime evidence shows `/navigate_to_pose` is available and a short same-floor
  `odom` goal succeeds.
- Runtime evidence shows navigation publishes `/cmd_vel` and
  `/go2w/perception/odom` changes during the goal.
- Runtime evidence confirms perception remains the only `odom -> base_link`
  authority and FAST-LIO upstream `camera_init -> body` TF stays absent.
- Runtime evidence confirms `nav2_route`, route graph, mission, stair,
  elevation, and traversability nodes are absent.
- Architecture state, README, and verification docs record the accepted result.

## Design Decision

Run the first same-floor Nav2 closed loop entirely in `odom`.

Rationale:

- Phase 2 already accepts `/go2w/perception/odom` and perception-owned
  `odom -> base_link`.
- The canonical `map -> odom -> base_link` chain remains the long-term target,
  but Phase 3A does not yet introduce localization or map authority for
  `map -> odom`.
- Adding an identity `map -> odom` publisher would be a temporary TF authority
  that could conflict with the later localization/map stage.
- `odom`-frame navigation is enough to verify the immediate interface closure:
  perception output -> Nav2 costmaps/planner/controller/BT -> `/cmd_vel` ->
  Gazebo motion -> perception odometry.

## Nav2 Composition

Phase 3A launches only the Nav2 components needed for a single same-floor
`NavigateToPose` goal:

- `planner_server` with `nav2_navfn_planner/NavfnPlanner`
- `controller_server` with `dwb_core::DWBLocalPlanner`
- `bt_navigator` with minimal ComputePathToPose / ComputePathThroughPoses +
  FollowPath trees
- `nav2_lifecycle_manager`

The launch intentionally omits `map_server`, `amcl`, `nav2_route`,
`waypoint_follower`, `behavior_server`, `smoother_server`, and
`velocity_smoother`. A local minimal NavigateThroughPoses tree is still
installed because Humble `bt_navigator` loads both default BT XMLs during
activation even when Phase 3A only sends `NavigateToPose` goals.

## Costmap Contract

Both local and global costmaps use:

- `global_frame: odom`
- `robot_base_frame: base_link`
- rolling windows
- PointCloud2 observation source: `/go2w/perception/cloud_body`

This reuses the Phase 2H perception consumer path but moves it from the
standalone `/costmap/costmap` gate into the conventional full-Nav2 costmap
namespaces: `/local_costmap/local_costmap` and
`/global_costmap/global_costmap`.

## Verification Strategy

The verifier replays the full accepted runtime chain:

1. launch headless Fortress `go2w_sim`
2. launch Phase 2 perception adapters and TF authority
3. launch patched no-TF FAST-LIO
4. launch Phase 3A Nav2
5. verify lifecycle, params, subscriptions, TF, and forbidden nodes
6. send a short `odom`-frame `NavigateToPose` goal
7. capture `/cmd_vel`, odometry delta, costmap rates, and logs

The verifier fails closed if the action does not succeed, if `/cmd_vel` is not
published, if odometry does not move, or if any later-phase node appears.

Phase 3A uses a dedicated feature-rich verification world because the Phase 1
empty world contains only a ground plane and is too degenerate for meaningful
FAST-LIO-backed motion feedback. The default `go2w_sim` world remains unchanged.

## Non-Goals

- No `map -> odom` publisher.
- No persistent 2D map.
- No `nav2_route`.
- No route graph authoring or visualization.
- No mission orchestration.
- No staircase behavior or control-mode handoff.
- No multi-floor behavior.
- No elevation mapping or traversability.
