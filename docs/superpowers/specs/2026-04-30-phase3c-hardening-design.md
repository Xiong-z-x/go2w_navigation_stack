# Phase 3C Hardening Design

## Status
Approved by the operator's autonomous execution instruction on 2026-04-30.

## Goal
Close three Phase 3 hardening gaps before Phase 4A:

- Make FAST-LIO external-source preparation reproducible without defaulting to `/tmp`.
- Add a persistent, floor-aware route graph contract that can represent a manual stair connector without adding mission autonomy.
- Add a minimal multi-floor hospital-style Gazebo world and matching map metadata for later Phase 4 staircase handoff tests.

Unitree Go2W model import is intentionally deferred because it changes model/control assumptions.

## Architecture
The work remains additive and keeps the current closed loop intact:

- `go2w_perception` owns FAST-LIO dependency policy and external patch gates.
- `go2w_navigation` owns route graph and map metadata assets.
- `go2w_sim` owns Gazebo world assets.
- No package may add mission orchestration, staircase executor runtime, elevation mapping, traversability, AMCL, `map_server`, or duplicate TF authority in this task.

## Data Flow
FAST-LIO remains external source plus repository-owned patch and wrapper scripts. The default external workspace moves from `/tmp` to an ignored repo-local cache:

```text
.go2w_external/src/FAST_LIO_ROS2
.go2w_external/workspaces/fast_lio_ros2
```

The route graph adds floor metadata and connector semantics as GeoJSON properties. `nav2_route` still receives a two-dimensional graph; floor identity is metadata for later mission decomposition, not 3D planning.

The hospital world is a deterministic SDF asset with two floor decks, corridors, obstacles, and a manual stair/ramp connector. It is not the default `go2w_sim` world.

## Testing
Verification must prove:

- FAST-LIO source acquisition uses the pinned dependency lock and does not default to `/tmp`.
- The multi-floor route graph is valid, installed, loadable by `route_server`, and can compute a route across a manual stair connector in `map`.
- The hospital world is valid SDF, installed, and can launch headless while preserving `/clock`, `/imu`, and `/lidar_points`.
- Phase 3B remains isolated from Phase 4 runtime behavior.

## Non-Goals
- Do not vendor FAST-LIO source into the repository.
- Do not import the Unitree Go2W model.
- Do not add real cross-floor autonomous mission behavior.
- Do not add elevation mapping, traversability, automatic stair detection, `map_server`, or AMCL.
- Do not change `odom -> base_link` perception authority.
