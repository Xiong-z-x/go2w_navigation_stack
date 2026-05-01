# Phase 5A Live Route Tracking Observation Gate Implementation Plan

> 实现已完成；当前验证与结论见 `docs/verification/phase5a_live_route_tracking.md`。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fake Phase 4D route-tracking feedback path with a live `nav2_route`-backed observation gate that can observe real `ComputeAndTrackRoute` feedback reaching staircase edge `500` under a controlled TF trajectory fixture.

**Architecture:** `go2w_mission` will own a small live route-tracking probe that sends a real `ComputeAndTrackRoute` goal to `nav2_route`, publishes a controlled TF trajectory fixture, and records feedback edges from the real server. `go2w_navigation` keeps ownership of the `route_server` runtime and graph assets; the existing Phase 4 skeleton remains intact for baseline acceptance, but the new verifier path stops using the fake feedback executor. The new gate is deliberately observation-only and does not attempt stair dynamics or `stair_exec` integration.

**Tech Stack:** ROS 2 Humble, `rclpy`, `tf2_ros`, `nav2_msgs/action/ComputeAndTrackRoute`, `pytest`, Bash runtime verifier, existing Phase 3C route graph assets.

---

## Task Card

1. **Task Goal**  
   Add a live route-tracking probe and verifier that uses the real `nav2_route` `route_server` feedback stream.

2. **Current Phase**  
   Post-Phase-4 risk-reduction task (`Phase 5A`), after `Phase 4 accepted`.

3. **Allowed Files**  
   - `go2w_mission/go2w_mission/phase5a_live_route_tracking.py`
   - `go2w_mission/scripts/go2w_phase5a_live_route_tracking`
   - `go2w_mission/launch/phase5a_live_route_tracking.launch.py`
   - `go2w_mission/test/test_phase5a_live_route_tracking.py`
   - `go2w_mission/CMakeLists.txt`
   - `go2w_navigation/launch/phase3b_route_graph.launch.py` only if a launch-level parameter override is required
   - `tools/verify_phase5a_live_route_tracking.sh`
   - `docs/verification/phase5a_live_route_tracking.md`
   - `docs/architecture/architecture_state.md`
   - `docs/handoff/next_agent_notes.md`
   - `docs/handoff/risk_cleanup_log.md`
   - `README.md` if the operator summary needs the new gate

4. **Forbidden Files**  
   - `go2w_control/*`
   - `go2w_perception/*`
   - `go2w_sim/*`
   - any `map_server` / `AMCL` / `elevation` / `traversability` files
   - any Unitree model import files
   - any change to the perception-owned `odom -> base_link` authority contract
   - any change that turns `stair_exec` into a service or ties it into the live route probe

5. **Required Commands**  
   - `python3 -m pytest go2w_mission/test/test_phase5a_live_route_tracking.py -q`
   - `bash -n tools/verify_phase5a_live_route_tracking.sh`
   - `./tools/verify_phase5a_live_route_tracking.sh`
   - `git diff --check`
   - `colcon build --symlink-install --packages-select go2w_mission go2w_navigation`
   - `colcon test --packages-select go2w_mission go2w_navigation`
   - `colcon test-result --verbose`

6. **Definition of Done**  
   - The new live probe can launch the real `nav2_route` `route_server`.
   - The probe records feedback from the real `ComputeAndTrackRoute` action, not from the fake Phase 4D executor.
   - The verifier observes feedback edge `500` from the real route server under the controlled TF trajectory fixture.
   - The verifier remains observation-only and does not claim stair dynamics or production mission orchestration.
   - The new docs and handoff notes clearly separate verified facts from remaining risks.

## Task 1: Write the failing pure tests

**Files:**
- Create: `go2w_mission/test/test_phase5a_live_route_tracking.py`

- [ ] **Step 1: Write the failing test**

```python
from go2w_mission.phase5a_live_route_tracking import build_route_pose_samples
from go2w_mission.phase4a_route_graph import Phase4ARouteGraph, RouteNode


def test_build_route_pose_samples_uses_graph_coordinates_in_order():
    graph = Phase4ARouteGraph(
        nodes={
            100: RouteNode(node_id=100, x=0.0, y=0.0, properties={"id": 100}),
            101: RouteNode(node_id=101, x=1.5, y=0.0, properties={"id": 101}),
            102: RouteNode(node_id=102, x=3.0, y=0.0, properties={"id": 102}),
        },
        edges={},
    )

    samples = build_route_pose_samples(graph, [100, 101, 102], hold_sec=0.25)

    assert [sample.node_id for sample in samples] == [100, 101, 102]
    assert [(sample.x, sample.y) for sample in samples] == [(0.0, 0.0), (1.5, 0.0), (3.0, 0.0)]
    assert all(sample.hold_sec == 0.25 for sample in samples)
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase5a_live_route_tracking.py -q`

Expected: `ModuleNotFoundError` for `go2w_mission.phase5a_live_route_tracking`.

- [ ] **Step 3: Stop here until the implementation task is ready**

No production code yet.

## Task 2: Implement the live probe and launch it against the real route server

**Files:**
- Create: `go2w_mission/go2w_mission/phase5a_live_route_tracking.py`
- Create: `go2w_mission/scripts/go2w_phase5a_live_route_tracking`
- Create: `go2w_mission/launch/phase5a_live_route_tracking.launch.py`
- Modify: `go2w_mission/CMakeLists.txt`

- [ ] **Step 1: Implement the minimal runtime**

The runtime should:
- load the Phase 3C route graph,
- build a TF trajectory from node IDs `100, 101, 102, 200, 201, 202`,
- publish a static `map -> odom` transform and a dynamic `odom -> base_link` trajectory fixture,
- send a real `ComputeAndTrackRoute` goal to `/compute_and_track_route`,
- record feedback edges and stop once edge `500` is observed,
- cancel the goal after the observation is achieved,
- print stable key-value diagnostics such as `phase5a_feedback_edge`, `phase5a_stair_edge_detected`, and `phase5a_live_route_tracking_result`.

- [ ] **Step 2: Add a launch file**

The launch file should bring up:
- `nav2_route route_server`,
- `nav2_lifecycle_manager`,
- the live probe executable.

It should override the route server `operations` parameter to a minimal observation-friendly setting so the route tracker can advance instead of looping on rerouting behavior.

- [ ] **Step 3: Add package installation**

Install the new Python module and script entrypoint through `ament_cmake_python` and `install(PROGRAMS ...)`.

- [ ] **Step 4: Run the pure test and the live probe**

Run:
- `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase5a_live_route_tracking.py -q`
- `bash -n tools/verify_phase5a_live_route_tracking.sh`
- `./tools/verify_phase5a_live_route_tracking.sh`

Expected:
- the pure test passes,
- the live probe reaches edge `500`,
- the verifier reports `phase5a_live_route_tracking_result: PASS`.

## Task 3: Add the verifier and update evidence

**Files:**
- Create: `tools/verify_phase5a_live_route_tracking.sh`
- Create: `docs/verification/phase5a_live_route_tracking.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `docs/handoff/next_agent_notes.md`
- Modify: `docs/handoff/risk_cleanup_log.md`
- Modify: `README.md`

- [ ] **Step 1: Write the verifier**

The script should:
- source ROS and the workspace,
- choose a safe `ROS_DOMAIN_ID`,
- launch the new live route-tracking stack,
- wait for `/compute_and_track_route`,
- run the live probe,
- confirm the stair edge observation,
- clean up all launched processes.

- [ ] **Step 2: Record evidence**

Write `docs/verification/phase5a_live_route_tracking.md` with:
- what was verified,
- what was only inferred,
- what remains unverified,
- the exact verifier command,
- the result keys from the run.

- [ ] **Step 3: Update handoff state**

Mark the new evidence as live route-server-backed observation and keep the remaining stair-dynamics gap explicit.

- [ ] **Step 4: Re-run the full local checks**

Run:
- `git diff --check`
- `colcon build --symlink-install --packages-select go2w_mission go2w_navigation`
- `colcon test --packages-select go2w_mission go2w_navigation`
- `colcon test-result --verbose`

Expected: no formatting regressions and no package test regressions.
