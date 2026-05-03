# Mission API Queue Replay Verification

## Scope
This document records the durable queue replay slice for `go2w_mission` `RunMission`.

It verifies that the mission API now has a replayable queue record backend for
outstanding mission admissions:

- outstanding queue records are persisted in a JSON ledger;
- startup can detect replay-pending queue records;
- new mission admissions are blocked with `MISSION_BUSY` /
  `mission_queue_replay_pending` until the operator acknowledges replay;
- the existing `MissionControl` service accepts `replay_queue`;
- replay restores scheduler ticket order and lets a resubmitted matching mission
  key re-use the persisted queue record;
- queued cancellation / queue-full behavior remains covered by the existing
  scheduling policy tests.

This is still not priority scheduling, fleet-level mission management, or a
complete long-lived production Mission Orchestrator.

## Implemented Runtime Surface
- `go2w_mission.mission_queue_replay.MissionQueueReplayStateStore` persists
  outstanding queue records as JSON.
- `go2w_mission.mission_scheduler.MissionScheduleGate.restore()` restores
  active / queued ticket state from the replay ledger.
- `go2w_mission.mission_api.MissionApiRuntime` records queue admission,
  activation, queued cancel, and mission completion transitions.
- `MissionControl` now supports `replay_queue` in addition to
  `pause`, `resume`, `status`, and `cancel_active`.
- `go2w_mission/launch/mission_api.launch.py` exposes:
  - `mission_queue_replay_state_file`

## Verification Run
- Date: `2026-05-04`
- Command:

```bash
./tools/verify_mission_api_queue_replay.sh
```

- Result:

```text
2 passed, 6 deselected in 0.01s
mission_queue_replay_result: PASS
```

## Verified Facts
- The queue replay store round-trips outstanding queue records.
- A runtime with persisted queue records rejects new `RunMission` admission with
  `MISSION_BUSY` / `mission_queue_replay_pending` before operator replay.
- `MissionControl replay_queue` acknowledges replay and changes the queue replay
  summary to `replay=ACKED`.
- The scheduler restores the persisted queued ticket.
- A resubmitted matching mission key re-uses the persisted queue record instead
  of consuming a new admission ticket.
- The replayed mission removes the outstanding queue record on completion.

## Key Result Lines
```text
2 passed, 6 deselected in 0.01s
mission_queue_replay_result: PASS
```

## Open Validation Items
- This verifies operator-triggered replay of mission queue records, not automatic
  ROS action goal-handle resurrection after a process restart.
- This does not add priority scheduling.
- This does not add fleet-level or long-term mission management.
- It does not change perception TF authority, default launch baseline, stair
  dynamics, AMCL / `map_server`, or terrain-aware connector generation.
