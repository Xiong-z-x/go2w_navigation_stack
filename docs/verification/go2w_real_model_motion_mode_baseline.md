# Go2W Real Model / Motion Mode Baseline Verification

## Scope
This document records the opt-in real Go2W model and motion-mode baseline. It verifies model loading, controller activation, sensor topics, explicit wheeled/legged mode data, and startup standing commands.

This is not a production locomotion acceptance test. It does not prove route tracking against physical robot motion, real stair traversal, gait stability, hardware control, or staircase dynamics.

## Source Basis
- Official Unitree Go2W description assets are imported from `unitreerobotics/unitree_ros` under the upstream BSD 3-Clause license notice recorded in `go2w_description/UNITREE_MODEL_LICENSE.txt`.
- The startup stand pose uses the Unitree reference stand posture pattern `hip=0.0`, `thigh=0.67`, `calf=-1.3` for all four legs. It is a simulation startup baseline, not hardware-validated tuning.
- The wheeled baseline keeps the existing conservative `wheel_radius=0.10` and `wheel_separation=0.38` values, now applied to the four real foot wheel joints through `diff_drive_controller` with `wheels_per_side=2`.

## Verification Run
- Date: `2026-05-01T15:33+08:00`
- Command: `./tools/verify_go2w_real_model_baseline.sh`
- Evidence directory: `/tmp/go2w_real_model_baseline_30527`
- Result: `go2w_real_model_baseline_result: PASS`

## Verified Facts
- `go2w_description/urdf/go2w_real.urdf` loads through the opt-in real-model launch path.
- The real model exposes `base_link`, `lidar_link`, and `imu_link` compatibility frames while retaining the official Go2W leg and foot wheel joints.
- `go2w_sim/launch/sim_go2w_real.launch.py` starts headless under the Fortress-only path.
- `joint_state_broadcaster`, `leg_position_controller`, and `diff_drive_controller` all reach `active`.
- `/joint_states` includes both a leg joint (`FL_hip_joint`) and a foot wheel joint (`FL_foot_joint`).
- `/clock`, `/imu`, and `/lidar_points` produce messages.
- `diff_drive_controller.enable_odom_tf` remains `False`, preserving the perception-owned `odom -> base_link` authority.
- `go2w_stand_initializer` publishes a 12-value stand command to `/leg_position_controller/commands`.

## Result Keys
```text
joint_state_broadcaster_active: PASS
leg_position_controller_active: PASS
diff_drive_controller_active: PASS
joint_states_include_leg_joint: PASS
joint_states_include_wheel_joint: PASS
diff_drive_odom_tf_disabled: PASS
clock_message: PASS
imu_message: PASS
lidar_points_message: PASS
stand_initializer: PASS
go2w_real_model_baseline_result: PASS
```

## Implementation Notes
- The new path is opt-in: `ros2 launch go2w_sim sim_go2w_real.launch.py use_gpu:=false headless:=true launch_rviz:=false`.
- The legacy `go2w_sim sim.launch.py` placeholder path remains the default accepted path for existing Phase 1-5 verifiers.
- The original wheel visual meshes are retained, but foot wheel collision geometry is simplified to cylinders with `radius=0.10` and `length=0.05` to keep headless controller activation stable.
- `command_gate` now publishes `/go2w/control/active_mode`, mapping `flat -> wheeled` and `stair -> legged`.
- The opt-in same-floor route-following verifier is documented separately in
  `docs/verification/go2w_real_model_route_following.md`.
- `go2w_stair_executor` now reuses the same legged motion profile as its conservative stair-command baseline and clamps stair linear velocity to that profile ceiling. This keeps the control skeleton aligned with the motion-mode baseline, but it is still not a real stair controller.
- `go2w_stair_executor` now also publishes a 12-joint leg hold command on `/leg_position_controller/commands` while stair ownership is active. This makes the posture outlet explicit, but it is still not a tuned stair gait controller.

## Open Validation Items
- The real model path has not yet replaced the default placeholder path.
- The current stand initializer only commands a static startup posture; it is not a gait controller.
- The wheeled parameters are conservative baseline values and still need broader odometry-scale and controller-tuning validation against the real model.
- `stair_exec` still does not perform real stair locomotion or leg trajectory control.
- No production hardware Unitree SDK2 integration is included in this repository path yet.
