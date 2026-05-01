# Phase 4E-Min Production Mission API Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a long-lived mission API skeleton in `go2w_mission` that exposes a stable `RunMission` Action, reuses the existing Phase 3C route graph and Phase 4B/4C execution helpers, and produces diagnosable result/feedback keys for success, invalid goal, unavailable route, unavailable action, and cancel paths.

**Architecture:** `go2w_mission` owns the Action API, mission goal validation, route decomposition orchestration, and result/feedback reporting. `go2w_navigation` continues to own route graph assets and flat navigation action dispatch. `go2w_control` continues to own `/stair_exec` and motion arbitration.

**Tech Stack:** ROS 2 Humble, `ament_cmake`, `ament_cmake_python`, `rosidl_default_generators`, `rclpy`, `nav2_msgs`, `go2w_control.action.StairExec`, `pytest`, Bash verifier.

---

## File Structure

- `go2w_mission/action/RunMission.action`: stable mission API contract.
- `go2w_mission/go2w_mission/mission_api.py`: mission request validation, feedback/result helpers, and the Action server node.
- `go2w_mission/scripts/go2w_mission_api`: executable entrypoint.
- `go2w_mission/launch/mission_api.launch.py`: verifier launch for route server, lifecycle manager, command gate, flat executor, stair executor, and mission API server.
- `go2w_mission/test/test_mission_api_skeleton.py`: pure tests for mission goal validation and result classification.
- `go2w_mission/CMakeLists.txt`: action generation, install, and pytest registration.
- `go2w_mission/package.xml`: action generation and runtime dependencies.
- `tools/verify_mission_api_skeleton.sh`: runtime verifier.
- `docs/verification/mission_api_skeleton.md`: acceptance evidence.
- `README.md`, `docs/architecture/architecture_state.md`, `docs/handoff/current_project_state.md`, `docs/handoff/next_agent_notes.md`, `docs/handoff/risk_cleanup_log.md`: state synchronization.

## Task 1: Mission Action Contract and Pure Policy Tests

**Files:**
- Create: `go2w_mission/action/RunMission.action`
- Create: `go2w_mission/go2w_mission/mission_api.py`
- Create: `go2w_mission/test/test_mission_api_skeleton.py`
- Modify: `go2w_mission/CMakeLists.txt`
- Modify: `go2w_mission/package.xml`

- [ ] Write pure tests for mission goal validation and result classification.
- [ ] Run RED with `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_mission_api_skeleton.py -q`.
- [ ] Add the `RunMission` action contract and minimal policy helpers.
- [ ] Register action generation and pytest in CMake/package metadata.
- [ ] Run GREEN and commit `feat: add mission api skeleton contract`.

## Task 2: Mission API Server

**Files:**
- Extend: `go2w_mission/go2w_mission/mission_api.py`
- Create: `go2w_mission/scripts/go2w_mission_api`

- [ ] Implement the long-lived `RunMission` Action server using the existing route segmentation and execution helpers.
- [ ] Add stable feedback keys for route requested, segments ready, flat segment active, stair segment active, and mission complete.
- [ ] Handle cancellation and unavailable-action diagnostics without changing frozen interfaces.

## Task 3: Launch and Runtime Verifier

**Files:**
- Create: `go2w_mission/launch/mission_api.launch.py`
- Create: `tools/verify_mission_api_skeleton.sh`

- [ ] Create the mission API launch path with the existing route server, lifecycle manager, command gate, flat executor, and stair executor.
- [ ] Create a runtime verifier that sends success, invalid goal, unavailable action, and cancel-path goals.
- [ ] Run `bash -n tools/verify_mission_api_skeleton.sh`.
- [ ] Run `./tools/verify_mission_api_skeleton.sh`.
- [ ] Commit `test: add mission api skeleton verifier`.

## Task 4: Documentation And State Sync

**Files:**
- Create: `docs/verification/mission_api_skeleton.md`
- Modify architecture, README, handoff, and risk cleanup docs.

- [ ] Record mission API skeleton evidence.
- [ ] Update current project state and risk cleanup notes.
- [ ] Update the next-agent boundary to distinguish skeleton API from production orchestrator.
- [ ] Run `git diff --check`.
- [ ] Commit `docs: record mission api skeleton acceptance`.

## Plan Self-Review

- The mission API is separate from the control and navigation ownership boundaries.
- The plan reuses existing Phase 4B/4C helpers instead of duplicating route logic.
- The verifier remains bounded to skeleton behavior and does not claim real multi-floor autonomy.
