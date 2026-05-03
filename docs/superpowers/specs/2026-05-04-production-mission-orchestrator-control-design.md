# Production Mission Orchestrator Control Design

## Goal
Add a small production-style operator control slice to `go2w_mission` without
turning it into a full long-lived task manager.

This pass introduces:

- a persistent operator-state snapshot backend;
- a `MissionControl` service for `pause`, `resume`, `status`, and cooperative
  `cancel_active`;
- pause-aware admission gating so new missions are frozen while the operator
  keeps the queue intact;
- focused tests and verification for the control surface.

## Scope
### In scope
- JSON-backed operator-state snapshot store.
- Mission-control service contract and runtime wiring.
- Pause / resume / status / cancel_active control behavior.
- Focused unit tests and a verifier script.
- Documentation sync for the new control slice.

### Out of scope
- Durable queue replay across process restarts.
- Priority scheduling beyond FIFO.
- Fleet-level mission management.
- Perception TF authority changes.
- `map_server` / AMCL / `map -> odom`.
- Stair dynamics or gait tuning.
- Terrain-aware connector generation.

## Design
### Operator-state snapshot
Store a compact JSON snapshot for the mission operator mode:

- `OPEN` or `PAUSED`
- pause reason
- active mission key and ticket
- current queue snapshot
- last command and last message

This is a control-plane state record, not a replayable mission task backend.

### Control surface
Expose `MissionControl` with commands:

- `pause`
- `resume`
- `status`
- `cancel_active`

Behavior:

- `pause` freezes new admissions while preserving the current queue;
- `resume` re-opens admissions and lets queued goals continue;
- `status` returns a snapshot string for operators and logs;
- `cancel_active` cooperatively interrupts the active mission through the
  existing mission cancel checks.

### Integration surface
`MissionApiRuntime` keeps the current checkpoint/recovery pipeline. The new
control slice only adds a separate operator state store and control path.

The existing bounded FIFO scheduler remains unchanged except for a pause-aware
activation check.

## Validation
- `python3 -m py_compile` on the touched mission files.
- Focused `pytest` for operator control and scheduling policy behavior.
- `colcon build --symlink-install --packages-select go2w_control go2w_mission`.
- `colcon test --packages-select go2w_mission`.
- `colcon test-result --verbose`.
- `git diff --check`.

## Done Definition
The pass is complete when:

- the operator state store round-trips;
- pause blocks new admissions and resume restores the queue;
- `status` reports the current mode snapshot;
- `cancel_active` cooperatively cancels the active mission;
- docs and verification files stay aligned with the code.
