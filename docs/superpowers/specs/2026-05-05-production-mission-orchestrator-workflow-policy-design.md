# Production Mission Orchestrator Workflow Policy Design

## Goal
Add the next smallest production-style Mission Orchestrator capability after
bounded queueing, priority scheduling, operator control, queue replay, and task
history.

This pass introduces an explicit operator workflow policy snapshot for
`MissionControl`:

- a read-only `workflow` command;
- a stable workflow summary in `status` and other control responses;
- available operator commands derived from current runtime state;
- focused tests and verifier evidence.

## Scope
### In scope
- A small `go2w_mission.mission_workflow_policy` helper module.
- Workflow snapshot fields derived from current orchestrator, queue replay, and
  task-history state.
- A read-only `MissionControl` command named `workflow`.
- State-summary diagnostics that include workflow mode, mission activity,
  queue state, history state, and available operator commands.
- Focused unit tests and a dedicated verifier script.

### Out of scope
- Fleet-wide multi-robot task assignment.
- New action or service interface fields.
- Active mission preemption.
- New scheduler ordering beyond the existing non-preemptive priority queue.
- Persistent long-term workflow engine.
- Perception TF authority, default launch baseline, stair dynamics, real-model
  Nav2 tuning, `map_server` / AMCL, elevation, traversability, or automatic
  connector generation.

## Design
### Why this slice
The existing Mission API has multiple production-style slices, but the operator
workflow is still implicit in `MissionApiRuntime.handle_orchestrator_command`.
That makes it harder for a future fleet supervisor or operator UI to understand
what the next safe control action is.

The smallest useful improvement is a derived policy snapshot:

- it does not change mission execution semantics;
- it keeps the existing `MissionControl.srv` contract;
- it makes operator workflow state observable and testable.

### Workflow snapshot
The policy helper builds a snapshot from:

- `MissionOrchestratorState`
- `MissionQueueReplayState`
- `MissionTaskHistoryState`

The snapshot reports:

- `mode`: `OPEN` or `PAUSED`;
- `mission_state`: `ACTIVE` or `IDLE`;
- `queue_state`: `REPLAY_PENDING`, `QUEUED`, or `EMPTY`;
- `history_state`: `READY` or `EMPTY`;
- `available_commands`: deterministic operator commands allowed by the current
  state.

`available_commands` is diagnostic only. The existing command handlers remain
the authority for mutations, but their summaries now expose the same policy
view.

### MissionControl integration
Add a read-only command:

```text
MissionControl(command="workflow")
```

It returns:

- `accepted=true`
- current `mode`
- `message="workflow_snapshot"`
- `state_summary` containing the workflow summary plus existing orchestrator,
  queue replay, and task-history summaries.

`status`, `pause`, `resume`, `cancel_active`, `replay_queue`, `history`, and
`archive_history` also keep returning the combined summary, now with the
workflow policy prefix.

## Validation
- `python3 -m py_compile` on touched mission modules and tests.
- Focused pytest for the workflow policy module and Mission API integration.
- `tools/verify_mission_api_workflow_policy.sh`.
- `tools/verify_phase4_pre_handoff.sh`.
- `colcon build --symlink-install --packages-select go2w_mission`.
- `colcon test --packages-select go2w_mission`.
- `colcon test-result --verbose`.

## Done Definition
The pass is complete when:

- `MissionControl(command="workflow")` returns a deterministic workflow
  snapshot;
- `status` and other MissionControl summaries expose the same workflow policy
  view;
- focused tests prove workflow mode / mission / queue / history state and
  available-command diagnostics;
- handoff, architecture, README, and verification documents distinguish this
  narrow workflow-policy slice from full fleet-level assignment.
