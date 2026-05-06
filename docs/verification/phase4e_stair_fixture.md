# Phase 4E Real-Model Stair Fixture Verification

## Scope
This document records the post-Phase-4 real-model stair fixture gate for the
dedicated `/stair_exec` Action.

It verifies a phase-aware stair execution skeleton on the opt-in real Go2W
model launch path. It does not verify physical stair traversal, tuned legged
gait control, hardware SDK2 control, terrain contact stability, or true
cross-floor autonomy.

## Source Basis
- The verifier uses the opt-in real-model launch:
  `go2w_sim/launch/sim_go2w_real.launch.py`.
- `go2w_control` remains the owner of command arbitration, active motion mode,
  and stair execution.
- `/stair_exec` remains a dedicated Action. It is not a service and is not
  tunneled through `/cmd_vel`.
- The stair executor phase plan is:
  `prepare,wheel_lock,body_height_transition_down,execute_stairs,body_height_transition_up,release`.
- The current repository has no dedicated body-height hardware interface, so
  body-height transition is represented as diagnostic phase state and motion
  profile metadata. The leg command outlets in this gate are the current
  12-joint position command on `/leg_position_controller/commands` and the
  standard `JointTrajectory` diagnostic/future-integration surface on
  `/go2w/control/stair_leg_trajectory`.
- The phase plan now also reports `wheel_lock_required=...` and supports an
  opt-in execution body-height target for `body_height_transition_down` and
  `execute_stairs`.

## Verification Run
- Date: `2026-05-02T03:39+08:00`
- Command: `./tools/verify_phase4e_stair_fixture.sh`
- Evidence directory: `/tmp/go2w_phase4e_stair_fixture_14184`
- Result: `phase4e_stair_fixture_result: PASS`

## Verified Facts
- The real-model launch started headless with `use_gpu:=false`.
- `joint_state_broadcaster`, `leg_position_controller`, and
  `diff_drive_controller` reached `active`.
- `go2w_command_gate` and `go2w_stair_executor` nodes were present.
- `/stair_exec` was present and accepted a goal.
- The `/stair_exec` goal returned `SUCCEEDED`.
- The command gate observed owner/mode sequence:
  `flat/wheeled -> stair/legged -> flat/wheeled`.
- The stair executor logged the expected phase plan.
- Every phase in the phase plan was observed in executor state logs.
- Wheel-lock and body-height phase targets are now checked by the updated
  verifier; focused policy evidence is recorded in
  `docs/verification/phase4e_stair_phase_targets.md`.
- Trajectory outlet diagnostics are now checked by the updated verifier;
  focused policy evidence is recorded in
  `docs/verification/phase4e_stair_trajectory_outlet.md`.
- The active stair phase published a profile-limited command velocity
  `cmd_vel_mps=0.025`.
- Leg hold remained enabled through the active stair phases and was disabled in
  the final `release` phase.

## Result Keys
```text
controller_states_ready: PASS
node_/go2w_command_gate: PRESENT
node_/go2w_stair_executor: PRESENT
action_/stair_exec: PRESENT
stair_fixture_action_status: 4
stair_fixture_result_code: SUCCEEDED
stair_fixture_success: True
phase4e_stair_fixture_result: PASS
```

## Evidence Snippets
```text
go2w_command_gate_state: owner=flat mode=wheeled
go2w_command_gate_state: owner=stair mode=legged
go2w_command_gate_state: owner=flat mode=wheeled

go2w_stair_executor_plan: phases=prepare,wheel_lock,body_height_transition_down,execute_stairs,body_height_transition_up,release total_duration_sec=0.80
go2w_stair_executor_trajectory: phase=execute_stairs trajectory_joint_count=12 trajectory_checksum=...
go2w_stair_executor_state: phase=execute_stairs owner=stair mode=legged body_height_m=0.32 foot_raise_height_m=0.09 cmd_vel_mps=0.025 wheel_lock_required=true publish_leg_hold=true trajectory_joint_count=12 trajectory_checksum=...
go2w_stair_executor_state: phase=release owner=stair mode=legged body_height_m=0.32 foot_raise_height_m=0.09 cmd_vel_mps=0.000 wheel_lock_required=false publish_leg_hold=false trajectory_joint_count=12 trajectory_checksum=... progress=1.000 complete
```

## Open Validation Items
- This is still a stair execution skeleton, not real stair locomotion.
- The current leg command is a conservative phase target outlet, not a tuned
  stair gait.
- Wheel lock and body-height transition are observable control phases, not yet
  dedicated low-level hardware-control interfaces.
- No Unitree SDK2 hardware controller is included in this repository path.
- The real model path remains opt-in and does not replace `sim.launch.py`.
