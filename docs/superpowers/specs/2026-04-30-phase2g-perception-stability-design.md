# Phase 2G Perception Runtime Stability Design

## Scope

Phase 2G is the runtime stability acceptance gate for the already activated
Phase 2F perception baseline.

This task verifies that the current FAST-LIO perception chain can keep
publishing odometry, TF, point cloud, path, and map outputs during a longer
motion window. It does not add Nav2, mission orchestration, staircase behavior,
route graphs, elevation mapping, or simulator model changes.

## 6-Item Task Card

- Task Goal: verify activated Phase 2 perception outputs remain alive and
  internally consistent during a longer headless simulation motion window.
- Current Phase: `Phase 2`.
- Allowed Files: `tools/verify_phase2g_perception_stability.sh`,
  `docs/verification/phase2_perception_stability_acceptance.md`,
  `docs/superpowers/specs/2026-04-30-phase2g-perception-stability-design.md`,
  `docs/superpowers/plans/2026-04-30-phase2g-perception-stability.md`,
  `docs/architecture/architecture_state.md`, and `README.md`.
- Forbidden Files: `go2w_sim/*`, `go2w_description/*`, `go2w_control/*`,
  `go2w_perception/*`, `go2w_navigation/*`, `go2w_mission/*`, external
  FAST_LIO_ROS2 source, Nav2 files, mission files, and staircase files.
- Required Commands: `python3 -m pytest go2w_perception/test -q`,
  `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim`,
  `bash -n tools/verify_phase2g_perception_stability.sh`,
  `shellcheck tools/verify_phase2g_perception_stability.sh`,
  `./tools/verify_phase2g_perception_stability.sh`,
  `./tools/verify_go2w_sim_launch.sh`, and `git diff --check`.
- Definition of Done: the verifier runs headless Fortress simulation plus
  Phase 2F perception plus patched no-TF FAST-LIO; applies a motion command for
  a configurable stability window; verifies `diff_drive_controller` still does
  not publish odom TF; verifies `odom -> base_link` remains present from
  perception; verifies `camera_init -> body` remains absent; verifies
  `/go2w/perception/odom`, `/go2w/perception/path`,
  `/go2w/perception/cloud_registered`, `/go2w/perception/cloud_body`, and
  `/go2w/perception/laser_map` produce messages; verifies odometry, TF, adapted
  lidar, and registered cloud have non-zero rates; verifies FAST-LIO missing
  `time` warnings remain zero; records evidence; updates docs; and pushes
  `main`.

## Options Considered

1. Move directly to Nav2 bringup.
   - Faster superficially, but violates the current architecture state because
     perception stability is still open.
   - Rejected.

2. Add new production watchdog nodes.
   - Could be useful later, but adds runtime behavior before the baseline is
     accepted.
   - Rejected for Phase 2G.

3. Add an acceptance verifier that reuses the Phase 2F runtime chain and checks
   longer-window output stability.
   - Minimal code movement and strongest audit value for the current gate.
   - Selected.

## Selected Design

Add `tools/verify_phase2g_perception_stability.sh`.

The verifier reuses the accepted Phase 2F path:

- prepare patched external FAST-LIO in `/tmp`;
- build `go2w_perception`, `go2w_description`, and `go2w_sim`;
- launch headless `go2w_sim`;
- launch `go2w_perception phase2f_tf_authority.launch.py`;
- launch patched FAST-LIO with `publish.tf_publish_en=false`;
- publish a bounded `/cmd_vel` command for a default 30 second stability
  window;
- collect topic rate and once-message evidence;
- sample TF before and after the window;
- fail on missing outputs, forbidden TF, missing timing field warnings, or
  process exits.

The default 30 second window is intentionally longer than the Phase 2F dry-run
but short enough to keep iteration speed acceptable. It can be changed with
`GO2W_PHASE2G_STABILITY_SECONDS`.

## Acceptance Signals

- `diff_drive_controller.enable_odom_tf=False`
- pre-activation `odom -> base_link` absent
- post-activation `odom -> base_link` present
- `camera_init -> body` absent
- FAST-LIO missing-time warning count is `0`
- `/go2w/perception/odom`, `/tf`, `/fastlio/input/lidar_points`, and
  `/go2w/perception/cloud_registered` have non-zero measured rates
- contract path and map topics produce at least one message
- `/cmd_vel` publishes throughout the stability window
- odometry x position is sampled before and after the window for audit context

## Error Handling

The verifier fails closed and writes evidence under
`/tmp/go2w_phase2g_perception_stability_<pid>` by default. Cleanup terminates
FAST-LIO, perception launch, and simulation launch processes and then invokes
the repository cleanup script.
