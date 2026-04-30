# Phase 2H Costmap Consumer Gate Plan

## Scope

Execute the Phase 2H task card in
`docs/superpowers/specs/2026-04-30-phase2h-costmap-consumer-design.md`.

Status: completed on 2026-04-30.

## Steps

1. Completed: add `go2w_navigation` install rules and runtime dependencies for standalone
   Nav2 costmap lifecycle bringup.
2. Completed: add a local rolling costmap YAML that consumes
   `/go2w/perception/cloud_body`.
3. Completed: add a launch file that starts only `nav2_costmap_2d` and
   `nav2_lifecycle_manager`.
4. Completed: add a verifier that reuses the accepted Phase 2F/G perception runtime chain,
   launches the costmap consumer, and captures lifecycle, subscription, output,
   TF, and forbidden-node evidence.
5. Completed: run build, static checks, and runtime verification.
6. Completed: update verification docs, README, and architecture state.

## Checkpoints

- Standalone `/costmap/costmap` launches and reaches lifecycle `active`.
- Costmap subscribes to the perception cloud contract.
- `/costmap/costmap` publishes in `odom`.
- Forbidden Phase 3+ nodes remain absent.
- Phase 2 can be closed only after verification evidence is recorded.
