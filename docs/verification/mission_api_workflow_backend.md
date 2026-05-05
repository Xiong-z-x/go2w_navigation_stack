# Mission API Workflow Backend Verification

## Scope
This document records the minimal workflow-event backend slice for
`go2w_mission` `MissionControl`.

The current backend is intentionally narrow:

- `go2w_mission.mission_workflow_backend` persists a bounded JSON workflow
  event ledger.
- Mission lifecycle events record admission, activation, and terminal
  completion / cancellation for accepted local `RunMission` goals.
- Mutating operator control commands record workflow-control events.
- `MissionControl(command="workflow_events")` returns a read-only backend
  summary through the existing `MissionControl.srv` response schema.
- Combined `MissionControl` summaries include workflow backend diagnostics.

This is not a fleet-level workflow engine, active preemption, cross-robot goal
transfer, multi-robot dispatch optimization, or a complete production Mission
Orchestrator.

## Implemented Runtime Surface
- `go2w_mission.mission_workflow_backend.MissionWorkflowEventStateStore`
  persists bounded event records in JSON.
- `go2w_mission.mission_api.MissionApiRuntime` loads the workflow-event store
  at startup, appends lifecycle / mutating-control events, and exposes
  `MissionControl(command="workflow_events")`.
- `mission_api.launch.py` exposes:
  - `mission_workflow_events_file`
  - `mission_workflow_event_retention_limit`
- Existing scheduler, priority ordering, assignment admission, queue replay,
  task history, and workflow-policy snapshot semantics are unchanged.

## Verification Run
- Date: `2026-05-06`
- Command:

```bash
./tools/verify_mission_api_workflow_backend.sh
```

- Result:

```text
3 passed in 0.02s
mission_workflow_backend_result: PASS
```

## Verified Facts
- The workflow-event store round-trips JSON state and retains the newest
  records under a bounded retention limit.
- A completed accepted mission records `ADMIT`, `ACTIVE`, and `COMPLETE`
  events.
- `MissionControl(command="workflow_events")` returns
  `workflow_events_snapshot` and includes `workflow_backend=...` diagnostics.

## Package Verification
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_mission`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_mission`
  passed.
- `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
  reported `129 tests, 0 errors, 0 failures, 0 skipped` after the subsequent
  stair phase-target focused test was added.

## Key Result Lines
```text
3 passed in 0.02s
mission_workflow_backend_result: PASS
```

## Open Validation Items
- This does not add a full persistent workflow engine or fleet-level
  assignment.
- This does not preempt active missions or change scheduler admission.
- This does not change perception TF authority, default launch baseline,
  stair dynamics, AMCL / `map_server`, elevation mapping, traversability, or
  automatic connector generation.
