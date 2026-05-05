# Production Mission Orchestrator Workflow Policy Implementation Plan

> For agentic workers: implement this plan task-by-task. Keep the scope limited
> to the operator workflow policy snapshot.

**Goal:** Add a read-only MissionControl workflow-policy snapshot and expose it
through deterministic summaries without changing mission execution semantics.

**Architecture:** A new pure helper module derives workflow state from existing
orchestrator, queue replay, and task-history snapshots. `MissionApiRuntime`
uses that helper to answer `MissionControl(command="workflow")` and to prefix
combined state summaries.

**Tech Stack:** ROS 2 Humble services, `rclpy`, Python dataclasses, pytest,
Bash verifier scripts, colcon.

---

## File Structure

- `go2w_mission/go2w_mission/mission_workflow_policy.py`: new pure workflow
  snapshot helper.
- `go2w_mission/go2w_mission/mission_api.py`: import helper, add workflow
  summary, and handle the read-only `workflow` command.
- `go2w_mission/test/test_mission_workflow_policy.py`: focused RED/GREEN
  tests.
- `go2w_mission/CMakeLists.txt`: register the new pytest file.
- `tools/verify_mission_api_workflow_policy.sh`: focused verifier.
- `docs/verification/mission_api_workflow_policy.md`: evidence document.
- `docs/architecture/architecture_state.md`, `docs/handoff/*.md`,
  `README.md`: state and handoff synchronization.
- `tools/verify_phase4_pre_handoff.sh`: include new workflow evidence.

## Task 1: RED Tests

- [ ] Add pure workflow-policy tests for:
  - open / idle / empty state;
  - paused / active / replay-pending / history-ready state;
  - deterministic available-command diagnostics.
- [ ] Add a Mission API integration test for
  `handle_orchestrator_command("workflow")`.
- [ ] Run:

```bash
PYTHONPATH="$PWD/go2w_mission" python3 -m pytest go2w_mission/test/test_mission_workflow_policy.py -q
```

Expected before implementation: import or command support fails.

## Task 2: Workflow Policy Helper

- [ ] Add `MissionWorkflowSnapshot`.
- [ ] Add `build_mission_workflow_snapshot(...)`.
- [ ] Implement deterministic `mission_state`, `queue_state`,
  `history_state`, `available_commands`, and `summary()`.
- [ ] Run the focused pytest until pure policy tests pass.

## Task 3: MissionControl Integration

- [ ] Add `_workflow_summary()` and prefix `_combined_state_summary()`.
- [ ] Add read-only `workflow` command to `handle_orchestrator_command()`.
- [ ] Preserve existing command behavior and response schema.
- [ ] Run the focused pytest until all workflow tests pass.

## Task 4: Verifier And Documentation

- [ ] Add `tools/verify_mission_api_workflow_policy.sh`.
- [ ] Add `docs/verification/mission_api_workflow_policy.md`.
- [ ] Update `tools/verify_phase4_pre_handoff.sh`.
- [ ] Update architecture, handoff, README, and project-state docs.
- [ ] Run:

```bash
bash -n tools/verify_mission_api_workflow_policy.sh tools/verify_phase4_pre_handoff.sh
./tools/verify_mission_api_workflow_policy.sh
./tools/verify_phase4_pre_handoff.sh
git diff --check
```

## Task 5: Package Verification

- [ ] Run:

```bash
source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_mission
source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_mission
source /opt/ros/humble/setup.bash && colcon test-result --verbose
```

## Plan Self-Review

- The plan does not add fleet-level multi-robot assignment.
- The plan does not mutate scheduler semantics.
- The plan keeps the `MissionControl.srv` schema stable.
- The plan does not touch perception, default launch baseline, real-model Nav2
  tuning, stair dynamics, localization, or terrain-aware connector generation.
