# Phase 3B Route Graph Baseline Verification

Status: accepted.

This document records the accepted evidence for the first minimal
`nav2_route` / manual route graph baseline. The authoritative command is:

```bash
./tools/verify_phase3b_route_graph.sh
```

Acceptance requires:

- `route_server` reaches `active [3]`.
- `/route_server/set_route_graph` accepts the installed GeoJSON graph.
- `/compute_route` returns action status `SUCCEEDED` from node `0` to node `3`.
- Returned `Route` and `Path` frames are `odom`.
- `/route_graph` publishes a `visualization_msgs/msg/MarkerArray` in `odom`.
- No mission, stair, multi-floor, elevation, traversability, `map_server`, or
  `amcl` nodes are introduced.

## Accepted Evidence

Run date: 2026-04-30

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
compute_route_goal_accepted: True
compute_route_action_status: 4
compute_route_path_frame: odom
compute_route_route_frame: odom
compute_route_path_poses: 19
compute_route_route_nodes: 4
compute_route_route_edges: 3
compute_route_node_ids: 0,1,2,3
compute_route_edge_ids: 10,11,12
compute_route_route_cost: 0.9000000357627869
route_graph_marker_frame: odom
forbidden_later_phase_nodes: ABSENT
```

Route server log evidence:

```text
Loading graph file from .../phase3b_same_floor_route.geojson, by parser nav2_route::GeoJsonGraphFileLoader
Setting new route graph: .../phase3b_same_floor_route.geojson.
Route found with 4 nodes and 3 edges
```

Phase 3B intentionally does not launch simulation, planner/controller/BT,
mission, stair, multi-floor, elevation, or traversability nodes. Phase 3A is
the accepted evidence for the same-floor Nav2 motion loop; Phase 3B is the
isolated topology baseline.
