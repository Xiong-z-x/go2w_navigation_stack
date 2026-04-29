# Phase 2F TF Authority Activation Design

## Scope

Phase 2F activates the perception-side `odom -> base_link` TF authority from
the already stabilized Phase 2E FAST-LIO contract odometry.

This task is still inside Phase 2 perception baseline. It must not introduce
Nav2, mission orchestration, staircase behavior, route graphs, elevation maps,
or simulator model changes.

## 6-Item Task Card

- Task Goal: publish and verify `odom -> base_link` from
  `/go2w/perception/odom` while proving that competing TF authorities remain
  absent.
- Current Phase: `Phase 2`.
- Allowed Files: `go2w_perception/CMakeLists.txt`,
  `go2w_perception/package.xml`,
  `go2w_perception/go2w_perception/fastlio_tf_authority.py`,
  `go2w_perception/scripts/go2w_fastlio_tf_authority`,
  `go2w_perception/config/phase2f_tf_authority.yaml`,
  `go2w_perception/launch/phase2f_tf_authority.launch.py`,
  `go2w_perception/test/test_fastlio_tf_authority.py`,
  `tools/verify_phase2f_tf_authority.sh`,
  `docs/verification/phase2_tf_authority_activation.md`,
  `docs/architecture/architecture_state.md`, and `README.md`.
- Forbidden Files: `go2w_sim/*`, `go2w_description/*`, `go2w_control/*`,
  `go2w_navigation/*`, `go2w_mission/*`,
  `go2w_perception/patches/fast_lio_ros2/*`, vendored FAST_LIO_ROS2 source,
  Nav2 files, mission orchestration files, and staircase executor files.
- Required Commands: `python3 -m pytest go2w_perception/test -q`,
  `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim`,
  `bash -n tools/verify_phase2f_tf_authority.sh`,
  `shellcheck tools/verify_phase2f_tf_authority.sh`,
  `./tools/verify_phase2f_tf_authority.sh`,
  `./tools/verify_go2w_sim_launch.sh`, and `git diff --check`.
- Definition of Done: the Phase 2F launch starts Phase 2E adapters plus a
  dedicated perception TF authority node; `/tf` contains `odom -> base_link`;
  `/tf` does not contain `camera_init -> body`; pre-activation simulation TF
  sampling shows no existing `odom -> base_link`; the runtime controller
  parameter `enable_odom_tf` is `False`; FAST-LIO missing-time warnings remain
  zero; Phase 1 launch-chain verification still passes; documentation records
  evidence; and `main` is pushed.

## Options Considered

1. Extend the Phase 2E output adapter to publish TF directly.
   - Simpler launch surface, but weakens the no-TF Phase 2E contract.
   - Rejected because Phase 2E must remain a stable no-TF gate.

2. Add a dedicated TF authority node that subscribes to
   `/go2w/perception/odom`.
   - Keeps message contract adaptation and TF authority as separate units.
   - Allows explicit validation and fail-closed behavior on frame mismatch.
   - Selected.

3. Re-enable FAST-LIO's upstream TF publisher and remap frames.
   - Faster superficially, but reopens the `camera_init -> body` authority
     problem and couples the project contract to external source behavior.
   - Rejected.

## Selected Design

Add `go2w_fastlio_tf_authority` under `go2w_perception`.

The node subscribes to `/go2w/perception/odom`, validates that the incoming
message already has `header.frame_id=odom` and `child_frame_id=base_link`, then
publishes a `geometry_msgs/TransformStamped` on `/tf` through `tf2_ros`.
It copies timestamp, position, and orientation from the odometry message. If
the frame contract is violated, it logs an error and does not publish.

Add `phase2f_tf_authority.launch.py` as an additive launch path. It starts the
existing Phase 2E adapters and the new TF authority node. The existing
`phase2e_fastlio_contract.launch.py` remains no-TF.

Add `verify_phase2f_tf_authority.sh`. The verifier starts the accepted
headless Fortress simulation, proves no `odom -> base_link` exists before
activation, starts Phase 2F perception, launches patched FAST-LIO with
`publish.tf_publish_en=false`, samples contract odometry and `/tf`, and fails
on forbidden or missing TF edges.

## Error Handling

- Incoming odometry with unexpected frames is rejected.
- Missing contract odometry fails the verifier.
- Any `camera_init -> body` TF fails the verifier.
- Existing `odom -> base_link` before Phase 2F activation fails the verifier.
- Runtime `diff_drive_controller.enable_odom_tf` not equal to `False` fails
  the verifier.

## Test Strategy

- Unit tests cover odometry-to-transform conversion, timestamp preservation,
  position/orientation copying, and frame mismatch rejection.
- Runtime verifier proves the end-to-end authority handoff against Gazebo,
  Phase 2E adapters, patched FAST-LIO, and `/tf`.
- Phase 1 launch verifier remains a regression gate.
