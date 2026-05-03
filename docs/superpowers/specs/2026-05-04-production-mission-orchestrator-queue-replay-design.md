# Production Mission Orchestrator Queue Replay Design

## Goal
Add a minimal durable queue replay backend to `go2w_mission` without turning it into a
full long-lived task manager.

This pass introduces:

- a durable queue record store for outstanding `RunMission` admissions;
- operator-triggered queue replay after restart;
- replay-aware scheduler restoration that preserves FIFO order;
- focused tests and verification for replay / cancel / queue-full behavior.

## Scope
### In scope
- JSON-backed queue record store / ledger.
- Replay command wiring through the existing `MissionControl` service surface.
- Replay-aware startup state and scheduler restoration.
- Focused unit tests and a verifier script.
- Documentation sync for the replay slice.

### Out of scope
- Priority scheduling beyond FIFO.
- Fleet-level mission management.
- Perception TF authority changes.
- `map_server` / AMCL / `map -> odom`.
- Stair dynamics or gait tuning.
- Terrain-aware connector generation.

## Design
### Queue record store
Persist only outstanding queue records:

- ticket
- mission key
- mission request payload
- queue position
- state (`QUEUED` or `ACTIVE`)
- timestamps
- last transition message

This is a durable replay ledger for outstanding work, not a long-term workflow engine.

### Replay behavior
On startup:

- load the queue ledger;
- if outstanding records exist, mark the replay as pending;
- block fresh admissions until the operator explicitly issues replay.

On `MissionControl` replay command:

- restore the scheduler from the persisted ticket order;
- clear the replay-pending marker;
- let queued goals continue in FIFO order;
- keep cancellation and queue-full diagnostics unchanged.

### Integration surface
`MissionApiRuntime` keeps the existing checkpoint/recovery pipeline.
The new replay slice only adds a separate durable queue store and operator-triggered
replay path.

The existing bounded FIFO scheduler remains the active execution policy once replay
has been acknowledged.

## Validation
- `python3 -m py_compile` on the touched mission files.
- Focused `pytest` for replay store, scheduler restore, and mission API behavior.
- `colcon build --symlink-install --packages-select go2w_mission`.
- `colcon test --packages-select go2w_mission`.
- `colcon test-result --verbose`.
- `git diff --check`.

## Done Definition
The pass is complete when:

- outstanding queue records survive restart;
- replay pending state is visible to operators;
- explicit replay restores the queue order;
- queued cancellation still works before activation;
- docs and verification files stay aligned with the code.

