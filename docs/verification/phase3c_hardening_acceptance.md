# Phase 3C Hardening Acceptance

Status: accepted.

Phase 3C closes three hardening gaps after Phase 3A/3B acceptance:

- FAST-LIO external dependency preparation no longer defaults to `/tmp`.
- A persistent, floor-aware hospital route graph baseline is available in `map`.
- A non-default multi-floor hospital Gazebo world asset is available for future Phase 4 handoff tests.

This does not introduce Mission Orchestrator, staircase executor runtime,
multi-floor autonomous behavior, elevation mapping, traversability, automatic
stair detection, `map_server`, AMCL, Unitree Go2W model import, or changes to
perception-owned `odom -> base_link`.

## Fresh Verification

Run date: 2026-04-30

Static checks:

```bash
bash -n \
  tools/apply_phase2c_fastlio_patch.sh \
  tools/check_phase2_fastlio_external.sh \
  tools/prepare_phase2d_fastlio_external.sh \
  tools/verify_phase2d_fastlio_no_tf_dryrun.sh \
  tools/verify_phase3c_fastlio_dependency_baseline.sh \
  tools/verify_phase3c_multifloor_route_graph.sh \
  tools/verify_phase3c_hospital_world.sh

shellcheck \
  tools/apply_phase2c_fastlio_patch.sh \
  tools/check_phase2_fastlio_external.sh \
  tools/prepare_phase2d_fastlio_external.sh \
  tools/verify_phase2d_fastlio_no_tf_dryrun.sh \
  tools/verify_phase3c_fastlio_dependency_baseline.sh \
  tools/verify_phase3c_multifloor_route_graph.sh \
  tools/verify_phase3c_hospital_world.sh

python3 -m json.tool go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson
python3 - <<'PY'
import xml.etree.ElementTree as ET
ET.parse('go2w_sim/worlds/phase3c_hospital_multifloor_world.sdf')
print('sdf_xml_parse: PASS')
PY

source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception go2w_navigation go2w_description go2w_sim
colcon test --packages-select go2w_perception go2w_navigation go2w_description go2w_sim
colcon test-result --verbose
```

Result:

```text
sdf_xml_parse: PASS
Summary: 4 packages finished
Summary: 17 tests, 0 errors, 0 failures, 0 skipped
```

## FAST-LIO External Dependency Baseline

Command:

```bash
GO2W_FASTLIO_SKIP_BUILD=1 ./tools/verify_phase3c_fastlio_dependency_baseline.sh
```

Key results:

```text
fastlio_ref_pinned_sha: PASS
ikdtree_ref_pinned_sha: PASS
default_fastlio_paths_not_tmp: PASS
fastlio_external_audit: PASS
external_cache_untracked: PASS
phase3c_fastlio_dependency_result: PASS
```

The pinned refs are recorded in:

```text
go2w_perception/external/fast_lio_ros2.lock.env
```

Generated source and build products default to ignored local cache paths:

```text
.go2w_external/src/FAST_LIO_ROS2
.go2w_external/workspaces/fast_lio_ros2
```

The repository still does not vendor FAST-LIO source.

## Multi-Floor Route Graph Baseline

Command:

```bash
./tools/verify_phase3c_multifloor_route_graph.sh
```

Evidence directory:

```text
/tmp/go2w_phase3c_multifloor_route_23577
```

Key results:

```text
static_graph_nodes: 7
static_graph_edges: 12
static_graph_floors: F1,F2
static_graph_stair_edges: 2
route_server_lifecycle: active [3]
route_frame: map
global_frame: map
base_frame: base_link
set_route_graph: PASS
compute_route: PASS
compute_route_path_frame: map
compute_route_route_frame: map
compute_route_node_ids: 100,101,102,200,201,202
compute_route_edge_ids: 300,301,500,400,401
route_graph_marker_frame: map
forbidden_later_phase_nodes: ABSENT
phase3c_multifloor_route_result: PASS
```

Interpretation:

- `route_server` loads the installed floor-aware GeoJSON graph.
- `/compute_route` succeeds from floor `F1` node `100` to floor `F2` node `202`.
- The returned route crosses manual stair connector edge `500`.
- The graph uses `map` frame floor-atlas coordinates to avoid 2D projection ambiguity.
- No mission, stair executor runtime, elevation, traversability, `map_server`, or AMCL nodes are introduced.

## Multi-Floor Hospital World Baseline

Command:

```bash
./tools/verify_phase3c_hospital_world.sh
```

Evidence directory:

```text
/tmp/go2w_phase3c_hospital_world_23422
```

Key results:

```text
world_name: go2w_phase3c_hospital_multifloor_world
world_model_count: 9
world_static_validation: PASS
required_topic__clock: PASS
required_topic__imu: PASS
required_topic__lidar_points: PASS
gazebo_runtime: ign gazebo-6
phase3c_hospital_world_result: PASS
```

Interpretation:

- The installed SDF world is parseable and contains two floor decks plus a manual stair connector.
- The world launches through the existing Fortress-only `go2w_sim` path.
- The default placeholder model and default `empty_world.sdf` remain unchanged.
- `/clock`, `/imu`, and `/lidar_points` remain available in the non-default hospital world.

## Closure

Phase 3C hardening is accepted as an asset and dependency baseline. It prepares
Phase 4 but does not implement Phase 4 control handoff behavior.

Regression checks were also run after Phase 3C changes:

```text
./tools/verify_phase3b_route_graph.sh: phase3b_result: PASS
./tools/verify_go2w_sim_launch.sh: clock/imu/lidar_points/controller checks PASS
```
