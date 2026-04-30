# Phase 3B Route Graph Baseline Plan

## Scope

Execute the Phase 3B task card in
`docs/superpowers/specs/2026-04-30-phase3b-route-graph-baseline-design.md`.

Status: completed on 2026-04-30.

## Steps

1. Completed: add the `nav2_route` runtime dependency and install `graphs/`.
2. Completed: add a minimal `odom`-frame same-floor GeoJSON route graph.
3. Completed: add a Phase 3B route server parameter file.
4. Completed: add a Phase 3B launch file for `route_server` and lifecycle manager only.
5. Completed: add a verifier for build, lifecycle, graph reload, `ComputeRoute`, marker
   visualization, and forbidden-node checks.
6. Completed: run static checks and runtime verification.
7. Completed: update verification docs, README, and architecture state with accepted
   evidence.

## Checkpoints

- `route_server` is active.
- `/route_server/set_route_graph` accepts the installed graph.
- `/compute_route` succeeds from node `0` to node `3`.
- Returned path and route frames are `odom`.
- `/route_graph` publishes marker data in `odom`.
- Later-phase mission, stair, multi-floor, elevation, and traversability nodes
  remain absent.
