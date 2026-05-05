# Mission API Workflow Policy Verification

## Scope
This document records the operator workflow-policy slice for `go2w_mission`
`MissionControl`.

It verifies a narrow production-style policy view:

- `go2w_mission.mission_workflow_policy` derives a workflow snapshot from
  orchestrator, queue replay, and task-history state.
- `MissionControl(command="workflow")` returns a read-only workflow snapshot.
- Existing MissionControl state summaries now include the same workflow policy
  prefix.
- The snapshot reports mode, mission activity, queue state, history state, and
  available operator commands.

This is not fleet-level task assignment, active preemption, a persistent
workflow engine, or a complete production Mission Orchestrator.

## Implemented Runtime Surface
- `go2w_mission.mission_workflow_policy.MissionWorkflowSnapshot` reports:
  - `mode`
  - `mission_state`
  - `queue_state`
  - `history_state`
  - `available_commands`
- `go2w_mission.mission_api.MissionApiRuntime` now includes workflow summaries
  in combined control-state diagnostics.
- `MissionControl(command="workflow")` is accepted as a read-only query and
  returns `workflow_snapshot`.

## Verification Run
- Date: `2026-05-05`
- Command:

```bash
./tools/verify_mission_api_workflow_policy.sh
```

- Result:

```text
mission_workflow_policy_result: PASS
```

- Focused pytest result:

```text
3 passed in 0.01s
```

## Verified Facts
- Open / idle / empty mission state reports `workflow=mode=OPEN mission=IDLE
  queue=EMPTY history=EMPTY`.
- Paused / active / replay-pending / history-ready state reports `PAUSED`,
  `ACTIVE`, `REPLAY_PENDING`, and `READY`.
- Available command diagnostics are deterministic:
  `status`, `workflow`, `history`, `pause` / `resume`, `cancel_active`,
  `replay_queue`, and `archive_history` appear only when the current state makes
  them meaningful.
- `MissionControl(command="workflow")` returns `accepted=true`,
  `message=workflow_snapshot`, and a state summary containing the workflow
  snapshot plus existing queue replay and task-history summaries.

## Key Result Lines
```text
3 passed in 0.01s
mission_workflow_policy_result: PASS
```

## Open Validation Items
- This does not add fleet-level multi-robot assignment.
- This does not change scheduler admission, priority ordering, queue replay, or
  task-history persistence semantics.
- This keeps the `MissionControl.srv` schema unchanged.
