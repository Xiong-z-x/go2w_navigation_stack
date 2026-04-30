# Phase 3C Hardening Plan

## Task 1: FAST-LIO External Dependency Productionization

### Task Goal
Replace `/tmp` as the default FAST-LIO external-source location with a reproducible, pinned, repo-local ignored cache and document the dependency lock.

### Current Phase
Phase 3C hardening after Phase 3 acceptance; no Phase 4 runtime behavior.

### Allowed Files
- `.gitignore`
- `go2w_perception/external/**`
- `tools/prepare_phase2d_fastlio_external.sh`
- `tools/verify_phase2d_fastlio_no_tf_dryrun.sh`
- `tools/verify_phase3c_fastlio_dependency_baseline.sh`
- `docs/verification/**`
- `README.md`
- `docs/architecture/architecture_state.md`

### Forbidden Files
- FAST-LIO vendor source under the repository
- `go2w_navigation/**`
- `go2w_sim/**`
- `go2w_control/**`
- `go2w_mission/**`

### Required Commands
- `bash -n tools/prepare_phase2d_fastlio_external.sh tools/verify_phase2d_fastlio_no_tf_dryrun.sh tools/verify_phase3c_fastlio_dependency_baseline.sh`
- `shellcheck tools/prepare_phase2d_fastlio_external.sh tools/verify_phase2d_fastlio_no_tf_dryrun.sh tools/verify_phase3c_fastlio_dependency_baseline.sh`
- `GO2W_FASTLIO_SKIP_BUILD=1 ./tools/verify_phase3c_fastlio_dependency_baseline.sh`

### Definition of Done
The default FAST-LIO source/workspace paths are not `/tmp`, the dependency lock records pinned upstream refs, and verification proves the source can be acquired, patched, audited, and kept outside tracked repository files.

## Task 2: Persistent Multi-Floor Route Graph Hardening

### Task Goal
Add a floor-aware persistent route graph and map metadata contract for a manual multi-floor hospital baseline.

### Current Phase
Phase 3C hardening after Phase 3 acceptance; no Phase 4 mission/stair runtime.

### Allowed Files
- `go2w_navigation/graphs/**`
- `go2w_navigation/config/**`
- `go2w_navigation/maps/**`
- `go2w_navigation/CMakeLists.txt`
- `tools/verify_phase3c_multifloor_route_graph.sh`
- `docs/verification/**`
- `README.md`
- `docs/architecture/architecture_state.md`

### Forbidden Files
- `go2w_control/**`
- `go2w_mission/**`
- `go2w_perception/**`
- `go2w_sim/**`
- Phase 3A/3B accepted graph/config behavior changes

### Required Commands
- `bash -n tools/verify_phase3c_multifloor_route_graph.sh`
- `shellcheck tools/verify_phase3c_multifloor_route_graph.sh`
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_navigation`
- `./tools/verify_phase3c_multifloor_route_graph.sh`

### Definition of Done
The graph contains at least two floors, flat edges, a manual stair connector, and map-frame metadata; it is installed and `route_server` can compute a route across the connector without launching mission, stair, elevation, traversability, `map_server`, or AMCL nodes.

## Task 3: Multi-Floor Hospital World Asset

### Task Goal
Add a non-default multi-floor hospital-style Gazebo Fortress world for future Phase 4 handoff tests.

### Current Phase
Phase 3C hardening after Phase 3 acceptance; no Unitree model import and no Phase 4 runtime behavior.

### Allowed Files
- `go2w_sim/worlds/**`
- `tools/verify_phase3c_hospital_world.sh`
- `docs/verification/**`
- `README.md`
- `docs/architecture/architecture_state.md`

### Forbidden Files
- `go2w_description/urdf/go2w_placeholder.urdf`
- `go2w_sim/launch/sim.launch.py` unless required for backward-compatible launch arguments
- `go2w_control/**`
- `go2w_mission/**`
- `go2w_perception/**`
- `go2w_navigation/**` except documentation references

### Required Commands
- `bash -n tools/verify_phase3c_hospital_world.sh`
- `shellcheck tools/verify_phase3c_hospital_world.sh`
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_description go2w_sim`
- `./tools/verify_phase3c_hospital_world.sh`

### Definition of Done
The world is installed, SDF is parseable, default `go2w_sim` world remains unchanged, and headless launch produces `/clock`, `/imu`, and `/lidar_points`.
