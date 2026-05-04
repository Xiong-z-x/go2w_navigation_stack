# Production Mission Priority Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit non-preemptive priority scheduling to `RunMission` while preserving bounded queue, replay, history, and operator-control semantics.

**Architecture:** `RunMission.action` carries the operator-specified priority. `MissionScheduleGate` owns in-memory activation order. Mission replay, task history, and operator snapshots persist the same priority metadata so runtime diagnostics explain why a mission was admitted or activated.

**Tech Stack:** ROS 2 Humble actions/services, `rclpy`, Python dataclasses/threading/JSON, pytest, Bash verifier scripts, colcon.

---

## File Structure

- `go2w_mission/action/RunMission.action`: add `int32 priority` to the request.
- `go2w_mission/go2w_mission/mission_scheduler.py`: store queue entries with ticket and priority, expose priority-aware snapshot.
- `go2w_mission/go2w_mission/mission_api.py`: read request priority, pass it to scheduler, queue replay, task history, and diagnostics.
- `go2w_mission/go2w_mission/mission_queue_replay.py`: persist priority in outstanding queue records and restore activation order by priority.
- `go2w_mission/go2w_mission/mission_task_history.py`: persist priority in terminal records.
- `go2w_mission/go2w_mission/mission_orchestrator.py`: record queued priority diagnostics in operator-state summaries.
- `go2w_mission/test/test_mission_scheduling_policy.py`: RED/GREEN coverage for priority ordering and regressions.
- `tools/verify_mission_api_priority_scheduling.sh`: focused py_compile + pytest verifier.
- `docs/verification/mission_api_priority_scheduling.md`: evidence document.
- `docs/architecture/architecture_state.md`, `docs/handoff/current_project_state.md`, `docs/handoff/pre_migration_final_freeze_report.md`, `docs/handoff/risk_cleanup_log.md`, `docs/handoff/next_agent_notes.md`, `docs/handoff/reading_order_and_file_map.md`, `docs/handoff/README.md`, `README.md`: state and handoff synchronization.
- `tools/verify_phase4_pre_handoff.sh`: include the new priority verification evidence and script in the handoff consistency gate.

## Task 1: RED Tests For Priority Semantics

**Files:**
- Modify: `go2w_mission/test/test_mission_scheduling_policy.py`

- [ ] Add a pure scheduler test named `test_mission_schedule_gate_prioritizes_waiting_goals_without_preemption`.
- [ ] Add a pure scheduler test named `test_mission_schedule_gate_keeps_fifo_for_equal_priority`.
- [ ] Add a mission API integration test named `test_mission_api_prioritizes_high_priority_queued_goal_after_active_releases`.
- [ ] Add replay/history assertions that priority is stored and reported.
- [ ] Run:

```bash
PYTHONPATH="$PWD/go2w_mission" python3 -m pytest go2w_mission/test/test_mission_scheduling_policy.py -q
```

Expected before implementation: tests fail because `MissionScheduleGate.reserve()` does not accept priority and fake `RunMission` requests do not propagate priority.

## Task 2: Scheduler And Mission API GREEN Implementation

**Files:**
- Modify: `go2w_mission/action/RunMission.action`
- Modify: `go2w_mission/go2w_mission/mission_scheduler.py`
- Modify: `go2w_mission/go2w_mission/mission_api.py`

- [ ] Add `int32 priority` to the action request after existing timeout fields.
- [ ] Add `priority: int = 0` to `MissionGoalSpec`.
- [ ] Normalize priority with `int(request.priority)` and default to `0` when old tests use a fake request without the field.
- [ ] Change `MissionScheduleGate.reserve(priority=0)` to store `ticket` and `priority`.
- [ ] Change `wait_for_turn()` to activate the queue entry sorted by `(-priority, ticket)`.
- [ ] Preserve active mission non-preemption by never comparing new priority against `_active_ticket`.
- [ ] Run the focused pytest command from Task 1 until it passes.

## Task 3: Persistence And Diagnostics

**Files:**
- Modify: `go2w_mission/go2w_mission/mission_queue_replay.py`
- Modify: `go2w_mission/go2w_mission/mission_task_history.py`
- Modify: `go2w_mission/go2w_mission/mission_orchestrator.py`
- Modify: `go2w_mission/go2w_mission/mission_api.py`

- [ ] Add priority fields to queue replay and task-history dataclasses.
- [ ] Default missing JSON priority fields to `0` for backward compatibility.
- [ ] Add queued priority pairs to `MissionOrchestratorState`.
- [ ] Update summaries to include priority diagnostics.
- [ ] Restore replay scheduler with ticket priorities.
- [ ] Run:

```bash
PYTHONPATH="$PWD/go2w_mission" python3 -m pytest go2w_mission/test/test_mission_scheduling_policy.py -q
```

Expected after implementation: all scheduling / replay / history tests pass.

## Task 4: Verifier And Documentation

**Files:**
- Create: `tools/verify_mission_api_priority_scheduling.sh`
- Create: `docs/verification/mission_api_priority_scheduling.md`
- Modify: `tools/verify_phase4_pre_handoff.sh`
- Modify: state and handoff docs listed in File Structure.

- [ ] Add a verifier that py-compiles touched mission modules and runs the scheduling policy pytest file.
- [ ] Add a verification document with command, result keys, verified facts, and open validation items.
- [ ] Update handoff / architecture / README files to state priority scheduling is complete only as a non-preemptive queued scheduling slice.
- [ ] Update `verify_phase4_pre_handoff.sh` to require the new verifier script and evidence doc.
- [ ] Run:

```bash
bash -n tools/verify_mission_api_priority_scheduling.sh tools/verify_phase4_pre_handoff.sh
./tools/verify_mission_api_priority_scheduling.sh
./tools/verify_phase4_pre_handoff.sh
git diff --check
```

## Task 5: Package Verification

**Files:**
- No new files unless verification reveals a focused fix.

- [ ] Run:

```bash
source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_mission
source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_mission
source /opt/ros/humble/setup.bash && colcon test-result --verbose
```

- [ ] If the action interface rebuild exposes stale install-space behavior, cleanly rerun the same command after confirming generated artifacts were rebuilt by colcon.

## Plan Self-Review

- The plan implements only explicit non-preemptive priority scheduling.
- The plan preserves active mission behavior and existing `cancel_active` semantics.
- The plan covers replay/history/status diagnostics so priority cannot become hidden scheduler state.
- The plan does not touch perception, stair dynamics, default launch baseline, localization, or terrain-aware connector generation.
