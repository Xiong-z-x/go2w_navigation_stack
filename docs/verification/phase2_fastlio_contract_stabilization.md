# Phase 2E FAST-LIO Contract Stabilization

## Purpose

This document records the Phase 2E contract stabilization gate for FAST-LIO
input/output plumbing.

Phase 2E adds repository-local `go2w_perception` adapters that provide a
per-point `time` field to FAST-LIO and republish FAST-LIO outputs on project
contract topics with project frame IDs.

Phase 2E does not activate or claim `odom -> base_link`.

## Phase Boundary

Allowed in this task:

- add local `go2w_perception` Python adapter nodes
- add local unit tests for timing and frame rewrite helpers
- add local config and launch files for the adapters
- verify patched external FAST-LIO through the existing `/tmp` scratch workflow
- verify adapted input topic and contract output topics
- verify no FAST-LIO TF or `odom -> base_link` TF is published

Forbidden in this task:

- changing Gazebo world, URDF, controller YAML, or sensor declarations
- modifying Nav2, `nav2_route`, mission orchestration, or staircase behavior
- vendoring FAST_LIO_ROS2 source into this repository
- expanding the external FAST-LIO patch
- publishing or claiming `odom -> base_link`

## Automation

Runtime verifier:

```bash
./tools/verify_phase2e_fastlio_contract.sh
```

The verifier runs the accepted headless simulation path, starts the local
Phase 2E adapters, launches patched FAST-LIO with
`common.lid_topic=/fastlio/input/lidar_points`, and treats missing timing
warnings, bad contract frames, forbidden TF, and runtime process residue as
hard failures.

## Observed Result

Observed on 2026-04-29.

Unit tests:

```bash
python3 -m pytest go2w_perception/test -q
```

Observed result:

```text
9 passed in 0.48s
```

Scoped build:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim
```

Observed result:

```text
Summary: 3 packages finished [0.80s]
```

Static checks:

```bash
bash -n tools/verify_phase2e_fastlio_contract.sh
shellcheck tools/verify_phase2e_fastlio_contract.sh
```

Observed result:

```text
no output
```

Runtime verifier:

```bash
./tools/verify_phase2e_fastlio_contract.sh
```

Observed summary:

```text
required_topic__clock: PASS
required_topic__imu: PASS
required_topic__lidar_points: PASS
adapter_process_alive: PASS
adapted_pointcloud_time_field: PASS
fastlio_process_alive: PASS
raw_fastlio_topic_odometry: PASS
raw_fastlio_topic_cloud_registered: PASS
raw_fastlio_topic_cloud_registered_body: PASS
raw_fastlio_topic_laser_map: PASS
raw_fastlio_topic_path: PASS
contract_odometry_frame: odom
contract_odometry_child_frame: base_link
contract_cloud_registered_frame: odom
contract_cloud_body_frame: base_link
contract_laser_map_frame: odom
contract_path_frame: odom
fastlio_missing_time_warning_count: 0
fastlio_tf_camera_init_body: ABSENT
odom_base_link_authority: ABSENT
phase2e_result: PASS
```

Evidence directory:

```text
/tmp/go2w_phase2e_fastlio_contract_1911
```

FAST-LIO log no longer contains the Phase 2D missing timing warning:

```text
fastlio_missing_time_warning_count: 0
```

No target runtime process remained after cleanup:

```text
pgrep fastlio_mapping/go2w_sim/go2w_perception/Gazebo target patterns: no target runtime process
```

## Current Decision

Phase 2E is complete as a FAST-LIO input/output contract stabilization gate:

- `/fastlio/input/lidar_points` carries a `time` field for FAST-LIO;
- FAST-LIO raw outputs are republished on project contract topics under
  `/go2w/perception/*`;
- project contract odometry uses `odom -> base_link` message frame semantics;
- no TF is published by the Phase 2E adapters;
- `odom -> base_link` remains unclaimed as a TF edge.

The next task must be a dedicated TF authority activation dry-run. It must be
limited to publishing and verifying `odom -> base_link` from the stabilized
perception contract, with duplicate TF authority checks. It must not introduce
Nav2, mission orchestration, staircase behavior, elevation mapping, or simulator
model changes.
