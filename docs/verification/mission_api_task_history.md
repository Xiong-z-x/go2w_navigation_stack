# Mission API Task History Verification

## Scope
This document records the long-term task-management slice for `go2w_mission`
`RunMission`.

It verifies that the mission API now has a bounded terminal mission history
backend:

- terminal `RunMission` records are persisted in a JSON task-history ledger;
- accepted missions create a task-history context at admission time;
- active missions update that context at activation time;
- mission success, failure, or cancellation appends a terminal history record;
- `MissionControl history` returns an operator-visible history summary;
- `MissionControl archive_history` trims old records to a bounded retention
  limit.

This verifier itself is still not priority scheduling, assignment policy,
fleet-level mission management, or a complete production Mission Orchestrator.

## Implemented Runtime Surface
- `go2w_mission.mission_task_history.MissionTaskHistoryStateStore` persists
  terminal mission records as JSON.
- `go2w_mission.mission_api.MissionApiRuntime` loads the history store on
  startup, captures admission / activation context, and appends terminal records
  from `_finish()`.
- `MissionControl` now supports `history` and `archive_history` in addition to
  `pause`, `resume`, `status`, `cancel_active`, and `replay_queue`.
- `status`, `pause`, `resume`, `cancel_active`, and `replay_queue` summaries now
  include the task-history summary.
- `go2w_mission/launch/mission_api.launch.py` exposes:
  - `mission_task_history_file`
  - `mission_task_history_retention_limit`

## Verification Run
- Date: `2026-05-04`
- Command:

```bash
./tools/verify_mission_api_task_history.sh
```

- Result:

```text
3 passed, 8 deselected in 0.04s
mission_task_history_result: PASS
```

## Verified Facts
- The task-history store round-trips terminal mission records.
- `archive_to_limit()` keeps the newest terminal records and trims old records.
- A successful `RunMission` execution appends a `SUCCEEDED` terminal history
  record with the expected mission key and result code.
- `MissionControl history` returns a snapshot containing the task-history
  record count and latest result.
- `MissionControl archive_history` accepts `retain=<N>` and trims history to
  the requested retention limit.

## Package Verification
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_mission`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_mission --event-handlers console_direct+`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
  reported `112 tests, 0 errors, 0 failures, 0 skipped`.

## Key Result Lines
```text
3 passed, 8 deselected in 0.04s
mission_task_history_result: PASS
```

## Open Validation Items
- This verifies terminal history persistence and bounded archive behavior, not
  priority scheduling or assignment policy.
- This does not resurrect ROS action goal handles after process restart.
- This does not add multi-robot dispatch optimization, cross-robot goal transfer,
  or a full workflow backend.
  The read-only operator workflow-policy snapshot is covered separately in
  `docs/verification/mission_api_workflow_policy.md`.
- It does not change perception TF authority, default launch baseline, stair
  dynamics, AMCL / `map_server`, or terrain-aware connector generation.
