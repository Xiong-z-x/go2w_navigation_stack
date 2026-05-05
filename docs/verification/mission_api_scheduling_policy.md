# Mission API Scheduling Policy Verification

## Scope
This document records the bounded FIFO scheduling policy for `go2w_mission` `RunMission`.

The current policy is intentionally small:

- one mission may execute actively;
- one mission may wait in queue;
- a third concurrent goal is rejected deterministically;
- a queued goal may still be canceled before activation;
- the existing mission recovery, route segmentation, and real-model flat execution behavior remain unchanged.

This verifier itself is still not a complete production Mission Orchestrator and not priority scheduling.
Operator pause/resume/status/cancel_active control is covered by a separate control gate.
Priority scheduling, durable queue replay, bounded task history, and workflow policy are covered by separate gates.

## Implemented Runtime Surface
- `go2w_mission.mission_scheduler.MissionScheduleGate` provides bounded FIFO admission.
- `go2w_mission.mission_api.MissionApiRuntime` now wires `RunMission` through the scheduler.
- `--mission-queue-capacity` is exposed by `go2w_mission/launch/mission_api.launch.py`.
- Queue-full admission returns `MISSION_BUSY` with `mission_queue_full`.
- Queued cancellation returns `MISSION_CANCELED` with `mission_queue_canceled`.
- Queue state is reported through the existing action feedback `state` field using values such as
  `QUEUED` and `SCHEDULED`.

## Verification Run
- Date: `2026-05-04`
- Command:

```bash
./tools/verify_mission_api_scheduling_policy.sh
```

- Result:

```text
mission_scheduling_policy_result: PASS
```

- Focused pytest result:

```text
19 passed in 1.26s
```

## Package Verification
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_mission`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_mission`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
  reported `112 tests, 0 errors, 0 failures, 0 skipped`.

## Verified Facts
- `RunMission` admits one active goal plus one queued goal in FIFO order.
- A third concurrent goal is rejected with deterministic `MISSION_BUSY` /
  `mission_queue_full` diagnostics.
- A queued goal can be canceled before activation and returns `MISSION_CANCELED` /
  `mission_queue_canceled`.
- The policy is in-memory only and does not introduce a persistent task backend.
- The mission recovery / route segmentation / real-model flat execution behavior remains
  unchanged.

## Key Result Lines
```text
mission_scheduling_policy_result: PASS
19 passed in 1.26s
Summary: 112 tests, 0 errors, 0 failures, 0 skipped
```

## Open Validation Items
- This verifies bounded queueing, not a complete production Mission Orchestrator.
- Priority scheduling, durable queue replay, bounded task history, and workflow
  policy are covered separately in dedicated verification documents.
- The bounded queue remains an in-memory scheduling policy layered on top of the existing
  mission execution path.
