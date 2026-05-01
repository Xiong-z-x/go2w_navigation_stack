# Go2W Production Mission API Skeleton Design

## Task Goal
Add a long-lived mission API skeleton in `go2w_mission` that accepts a single mission goal, computes the existing Phase 3C route, decomposes it into flat/stair segments, dispatches flat segments through the navigation-owned `NavigateToPose` gate, dispatches stair segments through the dedicated `/stair_exec` Action, and returns stable mission result keys plus feedback.

This task is about the mission API boundary only. It does not implement production recovery policy, real multi-floor autonomy, AMCL, `map_server`, terrain discovery, or stair locomotion tuning.

## Current Phase
Phase 4 accepted, post-Phase-4 hardening.

## Allowed Files
- `go2w_mission/action/*`
- `go2w_mission/go2w_mission/*`
- `go2w_mission/scripts/*`
- `go2w_mission/launch/*`
- `go2w_mission/test/*`
- `go2w_mission/CMakeLists.txt`
- `go2w_mission/package.xml`
- `tools/verify_mission_api_skeleton.sh`
- `docs/verification/mission_api_skeleton.md`
- `docs/architecture/architecture_state.md`
- `docs/handoff/current_project_state.md`
- `docs/handoff/next_agent_notes.md`
- `docs/handoff/risk_cleanup_log.md`
- `README.md`

## Forbidden Files
- `go2w_control/action/StairExec.action`
- `go2w_control/go2w_control_runtime/*` except for imports used by the mission client
- `go2w_navigation/go2w_navigation_runtime/*` except for imports used by the mission client
- `go2w_description/*`
- `go2w_sim/*`
- `go2w_perception/*`
- any TF authority or localization contract

## Required Commands
- `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_mission_api_skeleton.py -q`
- `bash -n tools/verify_mission_api_skeleton.sh`
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_mission`
- `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_mission`
- `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
- `./tools/verify_mission_api_skeleton.sh`

## Definition of Done
- `go2w_mission` exposes a stable mission Action API skeleton.
- The mission server reuses the existing route segmentation and flat/stair execution helpers.
- The runtime verifier proves success, invalid-goal diagnostics, cancel handling, and unavailable-action diagnostics.
- Documentation and architecture state describe the API as a skeleton, not a production orchestrator.

## Design

### Interface
Add a new `go2w_mission/action/RunMission.action` with request fields for start node, goal node, route graph path, route frame, and conservative timing knobs. Keep the result small and stable: success flag, result code, message, segment count, and a compact segment summary. Feedback should describe the current stage, segment index, segment type, active owner, and progress.

### Runtime
Add a long-lived mission server node in `go2w_mission` that:
1. validates the mission goal,
2. computes the route from the Phase 3C graph,
3. decomposes the route into mission segments,
4. dispatches flat segments through the existing navigation action,
5. dispatches stair segments through `/stair_exec`,
6. returns stable result keys and feedback.

The server should reuse the current helper functions where possible instead of rebuilding the route logic.

### Error Handling
The skeleton should diagnose:
- invalid start/goal combinations,
- missing or unreadable graph files,
- route server unavailable,
- flat action unavailable,
- stair action unavailable,
- mission cancel requests,
- route or connector unavailability.

It should not claim recovery behavior beyond those diagnoses.

### Testing
Start with pure tests for goal validation and mission result classification. Then add a runtime verifier that launches the existing route, flat, and stair skeletons, sends a real mission goal, and checks the stable keys from the action response and log stream.

## Self-Review
- No placeholder sections remain.
- The API boundary is separated from control and navigation ownership.
- The runtime verifier is bounded to existing skeleton behavior.
- The design does not introduce production recovery policy or localization.
