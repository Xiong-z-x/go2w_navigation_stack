# Phase 4D-Min Route Tracking Feedback Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a route tracking feedback observation gate using the standard `ComputeAndTrackRoute` feedback shape.

**Architecture:** `go2w_navigation` provides a verifier `ComputeAndTrackRoute` Action server. `go2w_mission` provides a one-shot observer client that detects staircase edge `500` and a `stair_exec` operation trigger from feedback.

**Tech Stack:** ROS 2 Humble, `rclpy`, `nav2_msgs/action/ComputeAndTrackRoute`, `pytest`, Bash runtime verifier.

---

## File Structure

- `go2w_navigation/go2w_navigation_runtime/route_tracking_feedback_executor.py`: verifier action server.
- `go2w_navigation/scripts/go2w_route_tracking_feedback_executor`: executable entrypoint.
- `go2w_navigation/test/test_phase4d_route_tracking_feedback_executor.py`: pure tests for feedback sequence.
- `go2w_mission/go2w_mission/phase4d_route_tracking_observer.py`: mission observer client.
- `go2w_mission/scripts/go2w_phase4d_route_tracking_observer`: executable entrypoint.
- `go2w_mission/test/test_phase4d_route_tracking_observer.py`: pure tests for feedback observation state.
- `go2w_mission/launch/phase4d_route_tracking_feedback.launch.py`: verifier launch.
- `tools/verify_phase4d_route_tracking_feedback.sh`: runtime verifier.

## Task 1: Navigation Feedback Executor

**Files:**
- Create: `go2w_navigation/go2w_navigation_runtime/route_tracking_feedback_executor.py`
- Create: `go2w_navigation/scripts/go2w_route_tracking_feedback_executor`
- Create: `go2w_navigation/test/test_phase4d_route_tracking_feedback_executor.py`
- Modify: `go2w_navigation/CMakeLists.txt`

- [ ] Write pure tests for `build_feedback_sequence(include_operation=True)`.
- [ ] Run RED with `PYTHONPATH=go2w_navigation python3 -m pytest go2w_navigation/test/test_phase4d_route_tracking_feedback_executor.py -q`.
- [ ] Implement the feedback sequence helper and Action server.
- [ ] Install the script and register pytest in CMake.
- [ ] Run GREEN and commit `feat: add phase4d route tracking feedback executor`.

## Task 2: Mission Route Tracking Observer

**Files:**
- Create: `go2w_mission/go2w_mission/phase4d_route_tracking_observer.py`
- Create: `go2w_mission/scripts/go2w_phase4d_route_tracking_observer`
- Create: `go2w_mission/test/test_phase4d_route_tracking_observer.py`
- Modify: `go2w_mission/CMakeLists.txt`

- [ ] Write pure tests for `RouteTrackingObservation`.
- [ ] Run RED with `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase4d_route_tracking_observer.py -q`.
- [ ] Implement observer state and one-shot Action client.
- [ ] Install the script and register pytest in CMake.
- [ ] Run GREEN and commit `feat: add phase4d route tracking observer`.

## Task 3: Launch And Runtime Verifier

**Files:**
- Create: `go2w_mission/launch/phase4d_route_tracking_feedback.launch.py`
- Create: `tools/verify_phase4d_route_tracking_feedback.sh`

- [ ] Create launch file for `go2w_route_tracking_feedback_executor`.
- [ ] Create verifier that builds packages, launches the server, waits for
  `/compute_and_track_route`, and verifies success, missing operation, and
  unavailable action paths.
- [ ] Run `bash -n tools/verify_phase4d_route_tracking_feedback.sh`.
- [ ] Run `./tools/verify_phase4d_route_tracking_feedback.sh`.
- [ ] Commit `test: add phase4d route tracking feedback verifier`.

## Task 4: Documentation And State Sync

**Files:**
- Create: `docs/verification/phase4d_route_tracking_feedback.md`
- Modify architecture, README, handoff, and pre-handoff verifier.

- [ ] Record Phase 4D evidence.
- [ ] Update active phase to `Phase 4D-min`.
- [ ] Add `tools/verify_phase4d_route_tracking_feedback.sh` to pre-handoff gate.
- [ ] Run Phase 4A/4B/4C/4D verifiers and package tests.
- [ ] Commit `docs: record phase4d route tracking feedback acceptance`.

## Plan Self-Review

- No placeholders remain.
- Tasks are single-purpose and independently commit-ready.
- No frozen control or perception interface changes are included.
