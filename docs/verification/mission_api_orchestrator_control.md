# Mission API Orchestrator Control Verification

## Scope
This document records the operator-control slice for `go2w_mission` `RunMission`.

It verifies that the mission API now exposes a persistent operator-state
snapshot backend and a control surface for:

- `pause`
- `resume`
- `status`
- cooperative `cancel_active`

The control slice is intentionally narrow:

- pause freezes new admissions while leaving the current queue intact;
- resume re-opens admissions and lets queued goals continue;
- `status` returns the current operator-mode snapshot;
- `cancel_active` cooperatively interrupts the active mission through the
  existing mission execution checks.

This control slice is still not a priority scheduler or full long-lived
production Mission Orchestrator. Durable queue replay is covered separately in
`docs/verification/mission_api_queue_replay.md`.

## Implemented Runtime Surface
- `go2w_mission.mission_orchestrator.MissionOrchestratorStateStore` persists the
  operator snapshot as JSON.
- `go2w_mission.mission_api.MissionApiRuntime` loads the operator state on
  startup, updates it on admission / activation / completion, and exposes the
  control helper used by the service callback.
- `go2w_mission/launch/mission_api.launch.py` exposes:
  - `mission_orchestrator_state_file`
  - `mission_control_service_name`
- `go2w_mission/srv/MissionControl.srv` defines the operator control service
  contract.

## Verification Run
- Date: `2026-05-04`
- Command:

```bash
./tools/verify_mission_api_orchestrator_control.sh
```

- Result:

```text
mission_orchestrator_control_result: PASS
```

- Focused pytest result:

```text
6 passed in 0.50s
```

## Package Verification
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_control go2w_mission`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_mission`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
  reported `47 tests, 0 errors, 0 failures, 0 skipped`.

## Verified Facts
- The operator snapshot state store round-trips `PAUSED` state and summary text.
- A paused mission API rejects new mission admission with `MISSION_BUSY` /
  `mission_paused`.
- A queued goal remains queued while paused and resumes after the operator
  issues `resume`.
- `cancel_active` cooperatively stops the active mission and returns
  `MISSION_CANCELED` / `mission_operator_canceled`.
- The operator control slice is persisted separately from the mission
  checkpoint/recovery store.

## Key Result Lines
```text
mission_orchestrator_control_result: PASS
6 passed in 0.50s
Summary: 47 tests, 0 errors, 0 failures, 0 skipped
```

## Open Validation Items
- This verifies operator control and persistent operator state. Durable queue
  replay is covered separately in `docs/verification/mission_api_queue_replay.md`.
- This does not add priority scheduling.
- The active mission cancellation is cooperative through the existing mission
  execution checks, not a preemptive hard stop.
