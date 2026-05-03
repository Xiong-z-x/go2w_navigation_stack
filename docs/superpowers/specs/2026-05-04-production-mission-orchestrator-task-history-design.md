# Production Mission Orchestrator Task History Design

## Goal
Add the next production Mission Orchestrator slice as a long-term task-management
backend for `go2w_mission`, without turning the package into a full workflow
engine.

This pass introduces:

- an append-only terminal mission history ledger;
- bounded retention for old terminal records;
- operator-visible history and archive commands through the existing
  `MissionControl` service surface;
- focused tests and verification for history persistence, history visibility,
  and bounded archive behavior.

## Scope
### In scope
- JSON-backed long-term mission history store.
- Terminal record capture for accepted `RunMission` executions.
- Operator-visible history summary through `MissionControl`.
- History archiving / retention trimming.
- Focused unit tests and a verifier script.
- Documentation sync for the long-term task-management slice.

### Out of scope
- Priority scheduling.
- Queue admission changes beyond the already completed bounded FIFO policy.
- Fleet-level mission management.
- Perception TF authority changes.
- `map_server` / AMCL / `map -> odom`.
- Stair dynamics or gait tuning.
- Terrain-aware connector generation.

## Why This Slice
Priority scheduling is still a valid future option, but the current `RunMission`
interface has no native priority field. Implementing priority now would require a
new operator encoding convention before there is a stable user-facing priority
signal. Long-term task management is the safer next slice because it fits the
existing mission lifecycle:

- `mission_api` already owns admission, queueing, recovery, and completion.
- `MissionControl` already exposes operator state and queue replay controls.
- The repo already uses JSON state stores for mission orchestration.

The new slice should therefore record what the orchestrator has done over time,
let operators inspect that record, and keep the archive bounded.

## Selected Design
### Long-term history ledger
Add a new JSON ledger that stores terminal mission records only.

Each record should capture:

- a stable run identifier derived from the mission key, queue ticket, and
  admission timestamp;
- mission key, ticket, queue position;
- terminal state and result code;
- terminal message;
- start / goal ids, graph file, route frame id;
- segment count and segment summary;
- admission, activation, completion, and update timestamps.

The ledger is append-only from the mission runtime's perspective. It is not a
queue replay store and does not resurrect action goal handles.

### Runtime integration
`MissionApiRuntime` should:

- create a long-term history context when a mission is admitted;
- update that context when the mission becomes active;
- append a terminal record when the mission finishes, cancels, or fails after
  admission;
- keep the history write best-effort for the mission result path, so a history
  save failure logs a warning but does not alter the mission result.

The existing checkpoint / recovery / queue replay / operator control logic
remains unchanged.

### Operator surface
Extend `MissionControl` with:

- `history` for a read-only task-history snapshot;
- `archive_history` for bounded retention trimming.

The service still uses its existing `command` and `reason` fields. For archive
operations, `reason` may carry an explicit `retain=<N>` override; otherwise the
configured retention limit is used.

`status`, `pause`, `resume`, `cancel_active`, and `replay_queue` should include
the history summary in their state snapshot so operators can see the long-term
ledger without asking for a separate call.

### Retention behavior
Keep the most recent terminal records up to the configured retention limit.
When the ledger exceeds the limit, archive the oldest terminal entries while
preserving the latest records. The retention policy should be explicit in the
stored state and visible in the summary.

## Validation
- `python3 -m py_compile` on the touched mission files.
- Focused `pytest` for history store, archive behavior, and mission API history
capture.
- `colcon build --symlink-install --packages-select go2w_mission`.
- `colcon test --packages-select go2w_mission`.
- `colcon test-result --verbose`.
- A focused verifier script for the history slice.
- `git diff --check`.

## Done Definition
The pass is complete when:

- terminal mission records survive restart in a bounded JSON ledger;
- operators can query task history through `MissionControl`;
- history archiving trims old terminal records without breaking mission
execution;
- docs and verification files stay aligned with the code;
- the change does not affect perception TF authority, default launch baseline,
  stair dynamics, AMCL / `map_server`, or terrain-aware connector generation.
