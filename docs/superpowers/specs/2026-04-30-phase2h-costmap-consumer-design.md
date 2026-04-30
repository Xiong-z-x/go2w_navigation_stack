# Phase 2H Costmap Consumer Gate Design

## Task Card

### Task Goal

Add the first Nav2 costmap consumer gate for Phase 2: a standalone
`nav2_costmap_2d` local costmap consumes verified Phase 2 perception outputs
without enabling full navigation, route graphs, mission orchestration,
staircase behavior, or multi-floor logic.

### Current Phase

`Phase 2` final perception-baseline consumer gate.

### Allowed Files

- `go2w_navigation/package.xml`
- `go2w_navigation/CMakeLists.txt`
- `go2w_navigation/config/**`
- `go2w_navigation/launch/**`
- `tools/verify_phase2h_costmap_consumer.sh`
- `docs/superpowers/specs/**`
- `docs/superpowers/plans/**`
- `docs/verification/**`
- `docs/architecture/architecture_state.md`
- `README.md`

### Forbidden Files

- `go2w_sim/**`
- `go2w_description/**`
- `go2w_control/**`
- `go2w_perception/**`
- `go2w_mission/**`
- external FAST_LIO_ROS2 source vendoring
- route graph, `nav2_route`, planner, controller, BT Navigator, mission, stair,
  elevation, or traversability implementation files

### Required Commands

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_navigation go2w_perception go2w_description go2w_sim
bash -n tools/verify_phase2h_costmap_consumer.sh
shellcheck tools/verify_phase2h_costmap_consumer.sh
./tools/verify_phase2h_costmap_consumer.sh
git status --short --branch
```

### Definition of Done

- `go2w_navigation` installs a minimal standalone costmap config and launch.
- The costmap uses `global_frame=odom`, `robot_base_frame=base_link`, and a
  PointCloud2 observation source from the Phase 2 perception contract.
- Runtime evidence shows standalone `/costmap/costmap` reaches `active`.
- Runtime evidence shows `/costmap/costmap` subscribes to the perception cloud
  and publishes `/costmap/costmap` in `odom`.
- Runtime evidence confirms no planner, controller, BT, route, mission, stair,
  elevation, or traversability nodes are launched.
- Architecture state and README are updated with the accepted evidence.

## Design Decision

Use `/go2w/perception/cloud_body` as the first costmap observation source.

Rationale:

- The local costmap is a rolling robot-local consumer; a body-frame current
  cloud is a safer obstacle input than an accumulated registered cloud.
- The TF chain already provides `odom -> base_link`, so Nav2 can transform the
  body-frame cloud into the `odom` costmap frame.
- This keeps the gate minimal and avoids map persistence, global planning, or
  route semantics.
- The Humble `nav2_costmap_2d` standalone executable internally creates the
  lifecycle node `/costmap/costmap`; this gate verifies that actual node rather
  than pretending it is the later full-Nav2 `/local_costmap/local_costmap`.

## Non-Goals

- No same-floor navigation goal execution.
- No planner/controller server.
- No `nav2_route`.
- No route graph.
- No mission orchestration.
- No staircase execution.
- No multi-floor behavior.
