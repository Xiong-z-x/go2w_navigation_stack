# Mission API Priority Scheduling Verification

## Scope
This document records the non-preemptive priority scheduling slice for
`go2w_mission` `RunMission`.

The current policy is intentionally narrow:

- `RunMission` accepts an explicit `priority` request field;
- active missions are not preempted by newly admitted higher-priority missions;
- queued missions activate by `priority DESC, ticket ASC`;
- equal-priority missions keep FIFO order;
- queue replay, task history, and operator-state summaries preserve priority
  diagnostics.

This is still not a complete production Mission Orchestrator, fleet-level task
assignment, or active-mission preemption.

## Implemented Runtime Surface
- `go2w_mission/action/RunMission.action` exposes `int32 priority`.
- `go2w_mission.mission_scheduler.MissionScheduleGate` stores priority-aware
  queue entries.
- `go2w_mission.mission_api.MissionApiRuntime` passes priority from admission
  into scheduler, queue replay, task history, and status diagnostics.
- `go2w_mission.mission_queue_replay.MissionQueueReplayStateStore` persists
  priority for outstanding queue records.
- `go2w_mission.mission_task_history.MissionTaskHistoryStateStore` persists
  priority for terminal mission records.
- `go2w_mission.mission_orchestrator.MissionOrchestratorState` reports queued
  priority pairs in operator summaries.

## Verification Run
- Date: `2026-05-04`
- Command:

```bash
./tools/verify_mission_api_priority_scheduling.sh
```

- Result:

```text
14 passed
mission_priority_scheduling_result: PASS
```

## Verified Facts
- Higher-priority queued missions activate before lower-priority queued
  missions after the current active mission releases.
- Equal-priority queued missions remain FIFO by ticket order.
- `RunMission` integration preserves non-preemptive behavior.
- Queue replay restores priority-aware queue order.
- Task history records and summaries include priority.
- Existing queue-full, queued cancel, pause/resume, replay, history, and archive
  tests remain covered by the focused scheduling policy test file.

## Key Result Lines
```text
14 passed
mission_priority_scheduling_result: PASS
```

## Open Validation Items
- This does not preempt the active mission.
- This does not add fleet-level assignment or an operator workflow backend.
- This does not change perception TF authority, default launch baseline, stair
  dynamics, AMCL / `map_server`, or terrain-aware connector generation.
