# Phase 3A Nav2 Same-Floor Minimal Bringup Plan

## Scope

Execute the Phase 3A task card in
`docs/superpowers/specs/2026-04-30-phase3a-nav2-same-floor-design.md`.

Status: completed on 2026-04-30.

## Steps

1. Completed: add `go2w_navigation` runtime dependencies for planner, controller, BT
   navigator, lifecycle manager, NavFn, DWB, and Nav2 action messages.
2. Completed: add minimal Phase 3A behavior trees with `ComputePathToPose`,
   `ComputePathThroughPoses`, and `FollowPath`.
3. Completed: add a Phase 3A Nav2 YAML that runs planner/controller/BT in `odom`, consumes
   `/go2w/perception/odom`, and configures both costmaps to consume
   `/go2w/perception/cloud_body`.
4. Completed: add a launch file that starts only the Phase 3A Nav2 nodes and their
   lifecycle manager.
5. Completed: add an end-to-end verifier that reuses the accepted Phase 2 runtime chain,
   launches Nav2, sends a short `NavigateToPose` goal, and captures lifecycle,
   action, `/cmd_vel`, odometry, costmap, TF, and forbidden-node evidence.
6. Completed: add a Phase 3A feature-rich verification world and a backward-compatible
   `world` launch argument so FAST-LIO has observable same-floor geometry.
7. Completed: run build, static checks, and runtime verification.
8. Completed: update verification docs, README, and architecture state with accepted
   evidence.

## Checkpoints

- Nav2 lifecycle nodes are active.
- `/navigate_to_pose` is available.
- Local and global costmaps subscribe to `/go2w/perception/cloud_body`.
- A short `odom` goal succeeds.
- `/cmd_vel` is published by Nav2.
- `/go2w/perception/odom` changes during the goal.
- Perception remains the only `odom -> base_link` TF authority.
- Later-phase route, mission, stair, elevation, and traversability nodes remain
  absent.
