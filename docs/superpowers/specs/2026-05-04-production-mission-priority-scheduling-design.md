# Production Mission Priority Scheduling Design

## Goal
Add the smallest production Mission Orchestrator priority-scheduling slice on top of the existing bounded `RunMission` queue.

## Scope
### In scope
- Add an explicit `priority` field to `go2w_mission/action/RunMission.action`.
- Keep scheduling non-preemptive: the active mission is never interrupted by a newly admitted higher-priority mission.
- Order queued missions by `priority DESC, ticket ASC`.
- Keep equal-priority behavior FIFO.
- Persist and report priority through queue replay, task history, and operator state summaries.
- Add a focused priority scheduling verifier and documentation evidence.

### Out of scope
- Active mission preemption.
- Fleet-level task assignment.
- Operator UI or remote policy backend.
- Perception TF authority changes.
- Default real-model baseline changes.
- Stair dynamics, gait tuning, body-height control, wheel-lock controller tuning.
- AMCL, `map_server`, `map -> odom`, elevation, traversability, or automatic connector generation.

## Interface
`RunMission.action` gains:

```text
int32 priority
```

Priority semantics:

- `0`: normal mission priority.
- Positive values: higher priority.
- Negative values: lower priority.
- Higher numeric priority activates before lower numeric priority while waiting in queue.
- Equal priority keeps ticket FIFO order.

The field is part of the mission request identity only for scheduling and audit metadata. It does not change route computation, flat goal yaw handling, recovery checkpoint keying, or control ownership.

## Scheduler Policy
`MissionScheduleGate` remains bounded by total outstanding missions. Its queue entries carry `ticket` and `priority`.

Activation order is:

```text
active mission first if already active
else highest priority queued entry
else oldest ticket among equal priority entries
```

This avoids implicit preemption and keeps the existing `MissionControl cancel_active` path as the only operator-triggered active interruption mechanism.

## Persistence And Diagnostics
- `MissionQueueRecord` records `priority`.
- `MissionQueueReplayState.queued_tickets` reflects activation order, not raw ticket order.
- `MissionTaskHistoryRecord` records `priority`.
- `MissionOrchestratorState` stores queued ticket / priority pairs in summaries so operator status explains why a queued mission is next.

Existing JSON loads must tolerate old records without priority by defaulting to `0`.

## Testing
The implementation is test-first:

- A pure scheduler test proves higher-priority queued missions activate before lower-priority queued missions.
- A pure scheduler test proves equal priority remains FIFO.
- Mission API integration proves a high-priority queued `RunMission` submitted after a lower-priority queued mission activates first once the active mission releases.
- Queue replay tests prove restored records preserve priority activation order.
- Task history tests prove terminal records include priority.

## Validation
Minimum verification:

```bash
bash -n tools/verify_mission_api_priority_scheduling.sh
PYTHONPATH="$PWD/go2w_mission" python3 -m pytest go2w_mission/test/test_mission_scheduling_policy.py -q
./tools/verify_mission_api_priority_scheduling.sh
source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_mission
source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_mission
source /opt/ros/humble/setup.bash && colcon test-result --verbose
./tools/verify_phase4_pre_handoff.sh
git diff --check
```

Run the stable control-chain regression only if mission package changes unexpectedly affect runtime scope.

## Done Definition
- `RunMission` accepts explicit priority.
- Queued high-priority missions activate before lower-priority queued missions.
- Equal priority remains FIFO.
- Queue-full, queued cancel, pause/resume, replay, history, and archive behavior remain covered.
- Documentation states this is priority scheduling only, not a complete production Mission Orchestrator.
