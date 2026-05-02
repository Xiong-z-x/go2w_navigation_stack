# Phase 4E Follow-up Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a phase-aware stair execution skeleton, mission recovery with persistent checkpoints, and an opt-in real-model regression wrapper without changing the default accepted real-model baseline.

**Architecture:** `go2w_control` owns the stair execution strategy and diagnostics. `go2w_mission` owns mission goal persistence, recovery, and scheduling of long mission runs. `tools/verify_*` and `docs/verification/*` capture the evidence, while `README.md` and handoff docs state clearly that the real-model path remains opt-in and is now part of a broader regression wrapper rather than the default baseline.

**Tech Stack:** ROS 2 Humble, `rclpy`, `ament_cmake`, `pytest`, Bash verifiers, Python standard library JSON / pathlib / threading utilities.

---

## File Structure

- `go2w_control/go2w_control_runtime/stair_executor.py`: phase-aware stair execution policy and diagnostic state reporting.
- `go2w_control/test/test_stair_executor_policy.py`: pure policy coverage for phase schedule and state formatting.
- `go2w_control/test/test_stair_executor_phases.py`: pure tests for the phase schedule helpers.
- `go2w_mission/go2w_mission/mission_recovery.py`: mission journal, checkpoint model, resume helpers, and state-file utilities.
- `go2w_mission/go2w_mission/mission_api.py`: integrate the recovery helpers into the long-lived action server.
- `go2w_mission/test/test_mission_recovery.py`: pure tests for checkpoint save/load and resume eligibility.
- `go2w_mission/launch/mission_api.launch.py`: expose recovery-related launch arguments.
- `tools/verify_phase4e_stair_fixture.sh`: runtime stair fixture verifier.
- `tools/verify_phase4e_mission_recovery.sh`: runtime mission recovery verifier.
- `tools/verify_go2w_real_model_regression.sh`: opt-in wrapper that composes the real-model baseline, route-following, and stair fixture checks.
- `docs/verification/phase4e_stair_fixture.md`, `docs/verification/phase4e_mission_recovery.md`, `docs/verification/go2w_real_model_regression.md`: evidence records.
- `docs/architecture/architecture_state.md`, `docs/handoff/current_project_state.md`, `docs/handoff/next_agent_notes.md`, `docs/handoff/risk_cleanup_log.md`, `README.md`: state synchronization.

## Task 1: Phase-Aware Stair Executor

**Files:**
- Modify: `go2w_control/go2w_control_runtime/stair_executor.py`
- Modify: `go2w_control/test/test_stair_executor_policy.py`
- Create: `go2w_control/test/test_stair_executor_phases.py`

- [x] Add a phase schedule helper that emits `prepare`, `wheel_lock`, `body_height_transition_down`, `execute_stairs`, `body_height_transition_up`, and `release`.
- [x] Keep `stair_cmd_vel` conservative and profile-limited during the active stair phase.
- [x] Emit stable diagnostic text for each phase so verifiers can observe the control sequence.
- [x] Add pure tests that assert the phase order, state text, and velocity clamp behavior.
- [x] Run `PYTHONPATH=go2w_control python3 -m pytest go2w_control/test -q`.

## Task 2: Mission Recovery and Persistent Scheduling

**Files:**
- Create: `go2w_mission/go2w_mission/mission_recovery.py`
- Modify: `go2w_mission/go2w_mission/mission_api.py`
- Modify: `go2w_mission/launch/mission_api.launch.py`
- Create: `go2w_mission/test/test_mission_recovery.py`

- [x] Add a mission checkpoint model and a JSON-backed state store with atomic writes.
- [x] Add resume eligibility helpers keyed by mission request identity and last checkpoint.
- [x] Update the action server so a matching incomplete mission can resume from the stored checkpoint.
- [x] Add finite retry handling for transient route / flat / stair unavailability.
- [x] Expose recovery configuration in the mission launch file.
- [x] Run `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test -q`.

## Task 3: Real-Model Regression Wrapper

**Files:**
- Create: `tools/verify_phase4e_stair_fixture.sh`
- Create: `tools/verify_phase4e_mission_recovery.sh`
- Create: `tools/verify_go2w_real_model_regression.sh`
- Create: `docs/verification/phase4e_stair_fixture.md`
- Create: `docs/verification/phase4e_mission_recovery.md`
- Create: `docs/verification/go2w_real_model_regression.md`

- [x] Implement a stair fixture verifier that checks the phase-aware `/stair_exec` sequence.
- [x] Implement a mission recovery verifier that proves the persisted checkpoint is written and can be resumed.
- [x] Implement a regression wrapper that runs the existing real-model baseline and route-following verifiers plus the new stair fixture check.
- [x] Keep the wrapper opt-in and do not modify the default `sim.launch.py` baseline.
- [x] Run `bash -n` on all three scripts.

## Task 4: Documentation And State Sync

**Files:**
- Modify: `docs/architecture/architecture_state.md`
- Modify: `docs/handoff/current_project_state.md`
- Modify: `docs/handoff/next_agent_notes.md`
- Modify: `docs/handoff/risk_cleanup_log.md`
- Modify: `README.md`

- [x] Record the new stair control strategy as a skeleton, not as real stair dynamics.
- [x] Record the mission recovery checkpoint model and its bounded recovery semantics.
- [x] Record that real-model remains opt-in and is now wrapped by an explicit regression script instead of a default-baseline flip.
- [x] Run `git diff --check`.

## Plan Self-Review

- The plan stays within the frozen control / mission boundaries.
- The plan gives the user a concrete answer on regression policy: opt-in wrapper, not default flip.
- Every runtime claim has a companion verifier or pure test.
