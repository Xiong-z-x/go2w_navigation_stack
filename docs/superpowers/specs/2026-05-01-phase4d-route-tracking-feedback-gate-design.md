# Phase 4D-Min Route Tracking Feedback Gate Design

## Context
Phase 4C-min proves mission sequencing through `flat -> stair -> flat`, but it
still does not cover the Phase 4 blueprint statement that `ComputeAndTrackRoute`
feedback and Route Operation semantics should be observable at staircase
handoff boundaries.

The current repository deliberately does not have a `map -> odom` localization
chain, AMCL, or map server. Forcing the real `nav2_route` route tracking path
against robot motion in this task would mix Phase 4 with localization work.

## Self-Approved Task Card

1. **Task Goal**: Add a Phase 4D-min route tracking feedback observation gate
   that uses the standard `nav2_msgs/action/ComputeAndTrackRoute` feedback shape
   to detect the staircase edge and route operation trigger.
2. **Current Phase**: `Phase 4C-min` accepted; this task advances to
   `Phase 4D-min`.
3. **Allowed Files**:
   - `go2w_navigation/go2w_navigation_runtime/*`
   - `go2w_navigation/scripts/*`
   - `go2w_navigation/test/*`
   - `go2w_navigation/CMakeLists.txt`
   - `go2w_mission/go2w_mission/*phase4d*`
   - `go2w_mission/scripts/*`
   - `go2w_mission/test/*phase4d*`
   - `go2w_mission/CMakeLists.txt`
   - `go2w_mission/launch/*phase4d*`
   - `tools/verify_phase4d_route_tracking_feedback.sh`
   - Phase 4D docs and state/handoff files
4. **Forbidden Files**:
   - `go2w_perception/*`
   - `go2w_sim/*`
   - `go2w_description/*`
   - `go2w_control/action/StairExec.action`
   - Any AMCL, `map_server`, `map -> odom`, elevation, traversability, or
     automatic connector generation changes
5. **Required Commands**:
   - `bash -n tools/verify_phase4d_route_tracking_feedback.sh`
   - `PYTHONPATH=go2w_navigation python3 -m pytest go2w_navigation/test/test_phase4d_route_tracking_feedback_executor.py -q`
   - `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase4d_route_tracking_observer.py -q`
   - `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_navigation go2w_mission`
   - `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_navigation go2w_mission`
   - `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
   - `./tools/verify_phase4d_route_tracking_feedback.sh`
6. **Definition of Done**:
   - A navigation-owned verifier Action server exposes
     `nav2_msgs/action/ComputeAndTrackRoute`.
   - The server publishes feedback including flat edge IDs, stair edge `500`,
     and an operation trigger for `stair_exec`.
   - A mission-owned observer Action client records feedback and reports stable
     keys for route tracking, stair edge detection, and operation trigger
     detection.
   - Missing action server and missing operation trigger paths are diagnosable.
   - No production mission API, real tracking against robot motion, localization
     chain, or stair controller tuning is introduced.

## Selected Architecture

### Navigation Layer
Add `go2w_navigation_runtime.route_tracking_feedback_executor`, a verifier
Action server for `ComputeAndTrackRoute`. It is not a replacement for
`nav2_route`; it is a controlled feedback source that uses the same action type
and feedback fields to validate mission-side observation logic.

### Mission Layer
Add `go2w_mission.phase4d_route_tracking_observer`, a one-shot CLI client that
sends a `ComputeAndTrackRoute` goal and records feedback. It reports:

- `phase4d_route_feedback_seen: PASS`
- `phase4d_stair_edge_detected: PASS`
- `phase4d_operation_triggered: stair_exec`
- `phase4d_route_tracking_result: PASS`

Failure modes:

- action unavailable: `ROUTE_TRACKING_UNAVAILABLE`
- no feedback: `ROUTE_TRACKING_FEEDBACK_MISSING`
- stair edge not observed: `STAIR_EDGE_NOT_OBSERVED`
- operation trigger not observed: `ROUTE_OPERATION_NOT_OBSERVED`

## Scope Guard
This task intentionally does not run real route tracking against robot motion.
It validates the feedback/operation contract that later real `nav2_route`
tracking must satisfy.

## Self-Review
- No placeholders remain.
- Package ownership is preserved.
- The task is single-purpose and does not introduce localization or terrain work.
