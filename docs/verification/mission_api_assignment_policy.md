# Mission API Assignment Policy Verification

## Scope
This document records the minimal fleet-assignment admission slice for
`go2w_mission` `RunMission`.

The current policy is intentionally narrow:

- `RunMission` accepts an explicit `assigned_robot_id` request field.
- The local mission API accepts blank assignment as the local robot default.
- The local mission API accepts goals assigned to its configured
  `mission_robot_id`.
- The local mission API rejects goals assigned to another robot before queue
  admission.
- Queue replay, task history, and control-state summaries preserve assignment
  diagnostics for accepted local goals.

This is not fleet-level multi-robot dispatch optimization, active mission
preemption, cross-robot action transfer, or a complete production Mission
Orchestrator.

## Implemented Runtime Surface
- `go2w_mission/action/RunMission.action` exposes `string assigned_robot_id`.
- `go2w_mission.mission_assignment` derives a deterministic assignment
  decision from local and requested robot ids.
- `go2w_mission.mission_api.MissionApiRuntime` rejects mismatched assignment
  before scheduler admission and normalizes accepted assignment to the local
  robot id.
- `go2w_mission.mission_queue_replay.MissionQueueReplayStateStore` persists
  `assigned_robot_id` for outstanding queue records.
- `go2w_mission.mission_task_history.MissionTaskHistoryStateStore` persists
  `assigned_robot_id` for terminal mission records.
- `mission_api.launch.py` exposes `mission_robot_id`, defaulting to
  `go2w_local`.

## Verification Run
- Date: `2026-05-06`
- Command:

```bash
./tools/verify_mission_api_assignment_policy.sh
```

- Result:

```text
4 passed in 0.04s
mission_assignment_policy_result: PASS
```

## Verified Facts
- Blank `assigned_robot_id` is accepted as the configured local robot id.
- A mismatched `assigned_robot_id` returns
  `MISSION_ASSIGNMENT_REJECTED` /
  `mission_assigned_to_other_robot:<robot_id>`.
- Rejected non-local goals do not enter scheduler, queue replay, or terminal
  history.
- Accepted local goals write `assigned_robot_id` to terminal task history and
  expose assignment diagnostics through `MissionControl status`.

## Key Result Lines
```text
4 passed in 0.04s
mission_assignment_policy_result: PASS
```

## Open Validation Items
- This does not assign tasks across multiple running robots.
- This does not preempt active missions.
- This does not change priority ordering, queue replay, task-history retention,
  workflow policy, perception TF authority, default launch baseline, stair
  dynamics, AMCL / `map_server`, or terrain-aware connector generation.
