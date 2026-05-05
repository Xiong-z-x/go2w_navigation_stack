# Phase 4E Mission Recovery Verification

## Scope
This document records the post-Phase-4 mission recovery and persistence gate
for the `RunMission` Action skeleton.

It verifies checkpoint persistence, bounded recovery retry, and resume of the
same mission goal from a stored checkpoint. It is not a complete production
Mission Orchestrator and does not prove real robot-motion route tracking,
physical stair traversal, multi-mission fleet scheduling, AMCL, `map_server`,
or `map -> odom` localization.

## Source Basis
- `go2w_mission/go2w_mission/mission_recovery.py` owns the checkpoint model,
  JSON-backed state store, mission-key helper, and resume eligibility helpers.
- `go2w_mission/go2w_mission/mission_api.py` integrates checkpoint writes,
  bounded retry, and same-goal resume behavior into the existing `RunMission`
  Action skeleton.
- `go2w_mission/launch/mission_api.launch.py` exposes recovery launch
  arguments:
  - `mission_state_file`
  - `mission_retry_limit`
  - `mission_retry_backoff_sec`
  - `mission_recovery_enabled`
- The `RunMission.action` interface is unchanged.

## Verification Run
- Date: `2026-05-02T03:39+08:00`
- Command: `./tools/verify_phase4e_mission_recovery.sh`
- Evidence directory: `/tmp/go2w_phase4e_mission_recovery_13467`
- Result: `phase4e_mission_recovery_result: PASS`

## Verified Facts
- First launch intentionally omitted the stair executor.
- The first mission request from node `100` to node `202` reached the stair
  segment and returned `MISSION_STAIR_UNAVAILABLE`.
- The state file was written with `state=RECOVERABLE`,
  `next_segment_index=1`, and `retry_count=2`.
- The second launch reused the same state file and started the stair executor.
- `go2w_mission_api` loaded the recoverable state and logged
  `mission_recovery_resume ... resume_from=1`.
- The second mission request resumed at the stair segment, completed the stair
  segment, completed the final flat segment, and returned `MISSION_SUCCEEDED`.
- The final state file was updated to `state=SUCCEEDED` and
  `next_segment_index=3`.

## Result Keys
```text
mission_goal_first_run: PASS
mission_goal_second_run: PASS
mission_state_first_run: PASS
mission_state_second_run: PASS
phase4e_mission_recovery_result: PASS
```

## Evidence Snippets
```text
mission_goal_result_code: MISSION_STAIR_UNAVAILABLE
mission_state_state: RECOVERABLE
mission_state_next_segment_index: 1
mission_state_retry_count: 2

mission_recovery_resume: key=100->202:map:phase3c_hospital_multifloor_route.geojson:05b33ef8 resume_from=1 state=RECOVERABLE retry_count=2

mission_goal_result_code: MISSION_SUCCEEDED
mission_state_state: SUCCEEDED
mission_state_next_segment_index: 3
```

## Implementation Notes
- The state file is written atomically as JSON.
- Matching recovery is keyed by start id, goal id, route frame, graph file, and
  route/segment identity.
- A different nonterminal mission checkpoint is treated as busy rather than
  silently overwritten.
- The mission API now also supports bounded FIFO queueing, so concurrent
  `RunMission` requests can either queue, return `MISSION_BUSY` /
  `mission_queue_full`, or be canceled while queued before activation. The
  mission API additionally exposes operator pause/resume/status/cancel_active
  control and a separate operator-triggered queue replay ledger, but the
  recovery verifier itself still does not exercise that queue replay backend.
- Retry is finite; the accepted verifier used the default retry limit and
  observed two retry attempts before the first run became recoverable.

## Open Validation Items
- This is a production-style recovery skeleton, not a complete production
  Mission Orchestrator.
- It does not provide fleet-level scheduling or a complete long-lived task
  manager. Concurrent admission, priority scheduling, operator control, queue
  replay, task history, and workflow policy are covered by separate focused
  gates.
- It still depends on current route, flat navigation, and stair executor
  skeletons.
- It does not replace real robot-motion route tracking or stair dynamics.
