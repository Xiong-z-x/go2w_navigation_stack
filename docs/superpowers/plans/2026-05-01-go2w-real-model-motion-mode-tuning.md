# Go2W Real Model Motion-Mode Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the opt-in Go2W real-model motion baseline into an explicit, conservative motion-mode profile system with startup stand selection, stair speed tuning, and verifier-visible diagnostics.

**Architecture:** `go2w_control` owns the motion-mode profile definitions, stair policy, and startup stand command. `go2w_sim` only wires the real-model launch to those control entrypoints. `docs/verification` records the accepted baseline facts and the verifier output; navigation and mission packages stay untouched.

**Tech Stack:** ROS 2 Humble, `ament_cmake`, `rclpy`, `pytest`, Bash verifiers, official Unitree reference docs as source basis.

---

## File Structure

- `go2w_control/go2w_control_runtime/motion_profiles.py`: explicit motion-mode metadata, profile lookup helpers, and summary formatting.
- `go2w_control/go2w_control_runtime/stand_initializer.py`: motion-mode selection for startup stand publishing and diagnostic output.
- `go2w_control/go2w_control_runtime/stair_executor.py`: stair velocity tuning defaults and motion-mode/profile diagnostics.
- `go2w_control/test/test_motion_profiles.py`: pure profile tests.
- `go2w_control/test/test_stair_executor_policy.py`: policy default and clamp tests.
- `go2w_sim/launch/sim_go2w_real.launch.py`: pass explicit motion mode into the real-model startup stand initializer.
- `tools/verify_go2w_real_model_baseline.sh`: require the new motion-mode diagnostics in the verifier log.
- `docs/verification/go2w_real_model_motion_mode_baseline.md`: update accepted facts and result keys.
- `docs/architecture/architecture_state.md`, `docs/handoff/current_project_state.md`, `docs/handoff/next_agent_notes.md`, `docs/handoff/risk_cleanup_log.md`, `README.md`: synchronize the new baseline facts.

## Task 1: Motion-Mode Profile Schema

**Files:**
- Modify: `go2w_control/go2w_control_runtime/motion_profiles.py`
- Modify: `go2w_control/test/test_motion_profiles.py`

- [x] Add explicit profile metadata fields for the real-model baseline.
- [x] Add helpers to resolve a profile from `wheeled` / `legged` mode and to render a stable one-line summary.
- [x] Keep the command-side defaults conservative and profile-driven instead of hard-coded at call sites.
- [x] Add/adjust unit tests to cover the new metadata and summary output.

Run:
`PYTHONPATH=go2w_control python3 -m pytest go2w_control/test/test_motion_profiles.py -q`

Expected:
pure tests pass and assert the new profile fields.

## Task 2: Stand and Stair Entrypoints

**Files:**
- Modify: `go2w_control/go2w_control_runtime/stand_initializer.py`
- Modify: `go2w_control/go2w_control_runtime/stair_executor.py`
- Modify: `go2w_sim/launch/sim_go2w_real.launch.py`
- Modify: `go2w_control/test/test_stair_executor_policy.py`

- [x] Make the startup stand initializer accept an explicit motion-mode selection and print the selected profile summary.
- [x] Make the stair executor derive its default stair velocity from the legged profile and keep the existing override path.
- [x] Pass the explicit motion-mode choice through the real-model launch path.
- [x] Update policy tests to reflect the new conservative defaults and profile linkage.

Run:
`PYTHONPATH=go2w_control python3 -m pytest go2w_control/test/test_stair_executor_policy.py -q`

Expected:
policy tests pass with the new profile-driven defaults.

## Task 3: Verifier And Docs

**Files:**
- Modify: `tools/verify_go2w_real_model_baseline.sh`
- Modify: `docs/verification/go2w_real_model_motion_mode_baseline.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `docs/handoff/current_project_state.md`
- Modify: `docs/handoff/next_agent_notes.md`
- Modify: `docs/handoff/risk_cleanup_log.md`
- Modify: `README.md`

- [x] Update the baseline verifier so it asserts the new motion-mode diagnostics are present in the launch log.
- [x] Update the verification doc with the new accepted facts and result keys.
- [x] Sync architecture and handoff docs so they say this is a tuned baseline, not a hardware-control claim.
- [x] Run the real-model baseline verifier and record the exact result keys in the docs.

Run:
`bash -n tools/verify_go2w_real_model_baseline.sh`
`source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_control go2w_sim`
`source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_control go2w_sim`
`source /opt/ros/humble/setup.bash && colcon test-result --verbose`
`./tools/verify_go2w_real_model_baseline.sh`

Expected:
build and package tests pass, and the baseline verifier prints the updated motion-mode result keys, including controller-state polling evidence.

## Plan Self-Review

- The plan stays inside `go2w_control` and the opt-in real-model launch path.
- The plan does not touch `go2w_navigation`, `go2w_mission`, `go2w_perception`, or route graph assets.
- The plan has a test-before-verification order and a clear verifier checkpoint.
- The plan keeps the change conservative and reversible if the baseline needs to be re-tuned later.
