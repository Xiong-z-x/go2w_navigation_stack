# Phase 3B Route Graph Baseline Design

## Task Card

### Task Goal

Introduce the smallest auditable `nav2_route` baseline for Phase 3. The stack
must load a hand-authored same-floor route graph, activate `route_server`,
compute an ID-based route, and publish a route graph visualization topic without
changing Phase 2 perception authority or adding mission/stair behavior.

### Current Phase

`Phase 3B`: minimal `nav2_route` / manual route graph baseline.

### Allowed Files

- `go2w_navigation/package.xml`
- `go2w_navigation/CMakeLists.txt`
- `go2w_navigation/config/**`
- `go2w_navigation/graphs/**`
- `go2w_navigation/launch/**`
- `tools/verify_phase3b_route_graph.sh`
- `docs/superpowers/specs/**`
- `docs/superpowers/plans/**`
- `docs/verification/**`
- `docs/architecture/architecture_state.md`
- `README.md`

### Forbidden Files

- `go2w_perception/**`
- `go2w_sim/**`
- `go2w_description/**`
- `go2w_control/**`
- `go2w_mission/**`
- FAST-LIO external vendoring or patching
- `odom -> base_link` TF authority changes
- mission orchestration
- staircase execution
- multi-floor behavior
- elevation mapping
- traversability

### Required Commands

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_navigation
bash -n tools/verify_phase3b_route_graph.sh
shellcheck tools/verify_phase3b_route_graph.sh
./tools/verify_phase3b_route_graph.sh
git status --short --branch
```

### Definition of Done

- `go2w_navigation` declares the `nav2_route` runtime dependency.
- `go2w_navigation` installs a hand-authored same-floor GeoJSON route graph.
- A Phase 3B launch file starts only `route_server` plus its lifecycle manager.
- `route_server` reaches `active`.
- `/route_server/set_route_graph` reloads the installed graph successfully.
- `/compute_route` returns action status `SUCCEEDED` for an ID-based route.
- The returned `Route` and `Path` are in `odom` and contain at least two nodes,
  one edge, and two path poses.
- `/route_graph` publishes `visualization_msgs/msg/MarkerArray` in `odom`.
- Verification confirms no mission, stair, multi-floor, elevation, or
  traversability nodes are introduced.
- Architecture state, README, and verification docs record the accepted result.

## Design Decision

Keep the Phase 3B route graph in `odom`.

Rationale:

- Phase 3A intentionally runs same-floor Nav2 in `odom` to avoid a temporary
  `map -> odom` authority.
- Phase 2 owns `odom -> base_link` through perception; Phase 3B must not change
  that TF edge.
- A small `odom` graph is sufficient to prove the topology baseline:
  GeoJSON loading, route computation, and route graph visualization.

## Runtime Composition

Phase 3B launches only:

- `nav2_route` `route_server`
- `nav2_lifecycle_manager` for `route_server`

It does not launch Nav2 planner/controller/BT, simulation, FAST-LIO, mission,
stair, elevation, or traversability nodes. Phase 3A already accepted the
same-floor Nav2 motion loop; Phase 3B isolates the new route-graph surface so
failures are attributable to `nav2_route`.

## Route Graph

The baseline graph is a small directed same-floor L-shaped graph:

- nodes `0 -> 1 -> 2 -> 3`
- reverse edges are present for basic bidirectional routing
- all node frames are `odom`
- edge costs are computed by `DistanceScorer`
- no semantic operations are attached
- no staircase or multi-floor metadata is present

The route server configuration does not set an empty `operations: []` list
because the Humble `nav2_route` parameter loader treats that as an invalid
unset parameter value. The graph itself remains free of operation metadata.

## Verification Strategy

The verifier:

1. builds `go2w_navigation`
2. launches the Phase 3B route server in an isolated `ROS_DOMAIN_ID`
3. waits for `/route_server` discovery with bounded retries
4. verifies lifecycle state, parameters, service, action, and marker output
5. calls `/route_server/set_route_graph` with the installed GeoJSON path
6. sends an ID-based `/compute_route` request from node `0` to node `3`
7. fails if the result is not successful, not in `odom`, or too small
8. fails if forbidden later-phase nodes appear

DDS discovery is explicitly bounded because the route server may print its
lifecycle startup log before `ros2 node list` sees `/route_server`.

## Non-Goals

- No route-to-Nav2 execution handoff.
- No Mission Orchestrator.
- No staircase Action execution.
- No multi-floor routing.
- No automatic stair connector generation.
- No `map -> odom` publisher.
- No changes to perception or control.
