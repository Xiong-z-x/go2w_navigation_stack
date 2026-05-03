# Production Mission Orchestrator Scheduling Policy Design

## Goal
Add the next smallest production-style Mission Orchestrator capability without turning
`go2w_mission` into a full long-lived task manager.

This pass introduces a bounded FIFO scheduling policy for `RunMission`:

- one mission may execute actively;
- one mission may wait in queue;
- a third concurrent goal is rejected with deterministic diagnostics;
- a queued goal may still be canceled before it becomes active;
- existing mission recovery and route segmentation behavior remain unchanged.

## Scope
### In scope
- A small in-memory mission scheduler for `go2w_mission`.
- FIFO queueing for `RunMission` goals with a bounded capacity.
- Deterministic diagnostics for queued, active, canceled, and queue-full outcomes.
- Focused unit tests for queue admission, queue order, queue-full rejection, and queue cancellation.
- Documentation and verification sync for the new scheduling policy.

### Out of scope
- Persistent task backend.
- Operator UI / pause / resume workflow.
- Priority scheduling beyond FIFO.
- Multi-queue orchestration.
- Perception TF authority changes.
- `map_server` / AMCL / `map -> odom`.
- Stair dynamics or gait tuning.
- Terrain-aware connector generation.

## Design
### Why queueing now
The current skeleton already has:

- route segmentation,
- flat/stair dispatch,
- checkpoint/recovery,
- flat-goal yaw canonicalization,
- single goal acceptance and cancellation handling.

The missing production-style layer is scheduling policy. A bounded FIFO queue is the
smallest useful next step because it exercises the orchestration boundary without
introducing persistence, operator workflow, or priority semantics.

### Policy shape
Use a small in-memory scheduler with:

- `capacity = 2` total outstanding goals by default,
- one active goal,
- one waiting goal,
- deterministic reject when capacity is full.

The scheduler must:

- admit goals in arrival order,
- let a queued goal block until it becomes active,
- allow a queued goal to observe cancellation before activation,
- release the active slot in `finally`,
- never mutate perception, navigation, or stair contracts.

### Diagnostics
The mission action contract already exposes a free-form `state` field in feedback.
Queueing may use that field for internal state transitions such as:

- `QUEUED`
- `SCHEDULED`
- `RUNNING`

The result contract stays unchanged. Queue-full rejection should still use
`MISSION_BUSY` with a message that explains the queue limit was reached.

### Integration surface
The scheduling policy lives inside `go2w_mission` only.
`mission_api.py` stays the entry point for `RunMission`, but the queueing policy should
be isolated in a small helper so it can be unit-tested without ROS launch overhead.

## Implementation Sketch
1. Add a tiny scheduler helper module in `go2w_mission`.
2. Wire `MissionApiRuntime.execute()` through the scheduler.
3. Preserve the existing route / recovery / flat execution flow once a goal becomes active.
4. Add focused tests for:
   - queue admission order,
   - queue-full rejection,
   - queued cancel,
   - mission API integration with a queued goal.

## Validation
- `python3 -m py_compile` on the touched mission files.
- Focused `pytest` for the scheduler helper and mission API integration.
- `colcon build --symlink-install --packages-select go2w_mission`.
- `colcon test --packages-select go2w_mission`.
- `colcon test-result --verbose`.
- `git diff --check`.
- If a mission verifier is added, run the new verifier script too.

## Done Definition
The pass is complete when:

- `RunMission` admits one active goal plus one queued goal in FIFO order;
- a third concurrent goal is rejected deterministically;
- queued goals can be canceled before activation;
- the existing recovery / yaw / flat execution behavior remains stable;
- docs and verification files match the new scheduling policy.
