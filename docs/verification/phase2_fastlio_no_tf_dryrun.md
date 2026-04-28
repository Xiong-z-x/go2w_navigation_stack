# Phase 2D FAST-LIO2 No-TF Runtime Dry-Run

## Purpose

This document records the Phase 2D runtime dry-run for patched external
FAST_LIO_ROS2.

Phase 2D launches the patched external wrapper against the accepted simulation
input topics while keeping FAST-LIO TF publication disabled.

Phase 2D does not activate or claim `odom -> base_link`.

## Phase Boundary

Allowed in this task:

- reuse or acquire external FAST_LIO_ROS2 source in `/tmp`
- apply the repository-local Phase 2C patch
- build external `fast_lio` with `FAST_LIO_ENABLE_LIVOX=OFF`
- launch `go2w_sim` headless on the accepted Fortress-only software-rendering path
- launch patched FAST-LIO with `publish.tf_publish_en=false`
- observe FAST-LIO output topics and TF absence/presence
- record whether a pointcloud adapter is required

Forbidden in this task:

- vendoring FAST_LIO_ROS2 source into this repository
- changing Gazebo world, URDF, controller YAML, or sensor declarations
- enabling FAST-LIO TF publication
- publishing or claiming `odom -> base_link`
- adding Nav2, `nav2_route`, mission orchestration, or staircase behavior

## Automation

Preparation command:

```bash
GO2W_FASTLIO_REBUILD=1 ./tools/prepare_phase2d_fastlio_external.sh
```

Runtime dry-run command:

```bash
./tools/verify_phase2d_fastlio_no_tf_dryrun.sh
```

## Observed Result

Observed on 2026-04-29.

External preparation was first forced through a fresh build:

```bash
GO2W_FASTLIO_REBUILD=1 ./tools/prepare_phase2d_fastlio_external.sh
```

Observed preparation summary:

```text
fastlio_remote_head: 2fffc570a25d0df172720bac034fbdb6a13d2162
ikdtree_remote_head: e2e3f4e9d3b95a9e66b1ba83dc98d4a05ed8a3c4
source_acquisition_status: downloaded
patch_status: applied
fastlio_no_tf_dryrun_gate: candidate_gated_default_off
Finished <<< fast_lio [1min 0s]
fastlio_build_status: PASS
fastlio_mapping_executable: present
prepare_status: complete
```

Runtime dry-run command:

```bash
./tools/verify_phase2d_fastlio_no_tf_dryrun.sh
```

Observed runtime summary:

```text
source_acquisition: reused_existing
patch_status: already_applied
fastlio_build_status: reused_existing
required_topic__clock: PASS
required_topic__imu: PASS
required_topic__lidar_points: PASS
fastlio_process_alive: PASS
fastlio_topic_odometry: PASS
fastlio_topic_cloud_registered: PASS
fastlio_topic_cloud_registered_body: PASS
fastlio_topic_laser_map: PASS
fastlio_topic_path: PASS
fastlio_tf_camera_init_body: ABSENT
odom_base_link_authority: ABSENT
fastlio_output_topics_with_messages: 5
phase2d_result: PASS
cleanup_fastlio: forced_terminate
cleanup_sim: forced_terminate
```

Evidence directory from the successful dry-run:

```text
/tmp/go2w_phase2d_fastlio_no_tf_dryrun_5190
```

No runtime process remained after cleanup:

```text
pgrep fastlio_mapping/go2w_sim/Gazebo target patterns: no target runtime process
```

## Runtime Findings

The no-TF runtime gate is cleared:

- patched FAST-LIO launched and stayed alive during the dry-run;
- all expected FAST-LIO output topics produced at least one message;
- FAST-LIO did not publish `camera_init -> body` TF;
- `odom -> base_link` remained absent and unclaimed.

Two integration blockers remain before TF authority activation:

- FAST-LIO output messages still use upstream frame IDs:
  `/Odometry.header.frame_id=camera_init` and
  `/Odometry.child_frame_id=body`.
- FAST-LIO logged repeated missing per-point timing warnings:
  `Failed to find match for field 'time'` was observed 464 times in the
  successful dry-run log.

## Current Decision

Phase 2D is complete as a no-TF runtime dry-run gate.

The next task must not claim `odom -> base_link` yet. The next minimal
perception task should stabilize the FAST-LIO input/output contract by handling
the missing pointcloud timing field and the upstream `camera_init/body` frame
IDs before any TF authority activation.
