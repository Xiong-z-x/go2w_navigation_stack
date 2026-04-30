# Phase 3 Runtime Acceptance

Status: accepted.

Phase 3 is accepted as the combination of:

- Phase 3A: minimal same-floor Nav2 planner/controller/BT navigation loop.
- Phase 3B: minimal `nav2_route` / manual route graph baseline.
- Phase 3C: hardening assets for FAST-LIO external dependency, persistent
  multi-floor route graph metadata, and a non-default multi-floor hospital world.

The accepted Phase 3 boundary is same-floor navigation plus topology skeleton.
It does not include Mission Orchestrator, staircase execution, multi-floor
behavior, elevation mapping, traversability, automatic stair connectors, or any
change to perception-owned `odom -> base_link`.

Phase 3C prepares multi-floor assets but still does not implement multi-floor
autonomous behavior or Phase 4 staircase control handoff.

## Fresh Verification

Run date: 2026-04-30

Static and build checks:

```bash
bash -n tools/verify_phase3a_nav2_same_floor.sh tools/verify_phase3b_route_graph.sh
shellcheck tools/verify_phase3a_nav2_same_floor.sh tools/verify_phase3b_route_graph.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_navigation go2w_perception go2w_description go2w_sim
```

Result:

```text
Summary: 4 packages finished
```

## Phase 3A Same-Floor Nav2 Evidence

Command:

```bash
./tools/verify_phase3a_nav2_same_floor.sh
```

Evidence directory:

```text
/tmp/go2w_phase3a_nav2_same_floor_17523
```

Key results:

```text
phase3a_goal_status: SUCCEEDED
phase3a_odom_delta_xy: 0.063236
phase3a_cmd_vel_nonzero_count: 465
local_costmap_average_rate: 1.667
global_costmap_average_rate: 0.667
cloud_body_average_rate: 9.680
odom_average_rate: 9.686
post_nav2_fastlio_tf_camera_init_body: ABSENT
post_nav2_map_odom: ABSENT
post_nav2_odom_base_link_authority: PRESENT
phase3a_result: PASS
```

Interpretation:

- Planner, controller, and BT Navigator were active.
- Nav2 consumed `/go2w/perception/odom` and `/go2w/perception/cloud_body`.
- A short `odom`-frame same-floor goal succeeded.
- Nav2 published nonzero `/cmd_vel`.
- Perception odometry changed during the goal.
- No temporary `map -> odom` authority was introduced.
- `odom -> base_link` remained perception-owned.

## Phase 3B Route Graph Evidence

Command:

```bash
./tools/verify_phase3b_route_graph.sh
```

Evidence directory:

```text
/tmp/go2w_phase3b_route_graph_17247
```

Key results:

```text
phase3b_result: PASS
route_server_lifecycle: active [3]
route_frame: odom
global_frame: odom
base_frame: base_link
set_route_graph: PASS
compute_route: PASS
compute_route_action_status: 4
compute_route_path_frame: odom
compute_route_route_frame: odom
compute_route_path_poses: 19
compute_route_route_nodes: 4
compute_route_route_edges: 3
compute_route_node_ids: 0,1,2,3
compute_route_edge_ids: 10,11,12
route_graph_marker_frame: odom
forbidden_later_phase_nodes: ABSENT
```

Interpretation:

- `route_server` loaded the installed hand-authored GeoJSON route graph.
- `/route_server/set_route_graph` reloaded the graph successfully.
- `/compute_route` succeeded from node `0` to node `3`.
- Returned `Route`, `Path`, and `/route_graph` visualization are in `odom`.
- No mission, stair, multi-floor, elevation, traversability, `map_server`, or
  `amcl` nodes were introduced.

## Closure

Phase 3 acceptance criteria from the canonical blueprint are covered:

- RViz-equivalent same-floor goal execution is covered by Phase 3A
  `NavigateToPose` runtime acceptance.
- Route graph visualization is covered by Phase 3B `/route_graph`
  `MarkerArray` evidence.
- `nav2_route` is enabled through a minimal route server and manual GeoJSON
  graph baseline.
- Phase 3C hardening evidence is recorded separately in
  `docs/verification/phase3c_hardening_acceptance.md`.

The next phase boundary is Phase 4A only after a separate complete task card.
