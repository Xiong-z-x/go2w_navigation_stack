# Phase 4C-Min Flat Segment Execution Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Phase 4B's print-only flat segment placeholder with a navigation-owned flat segment Action gate and verify `flat -> stair -> flat` sequencing.

**Architecture:** `go2w_navigation` owns the verifier flat navigation Action server using the standard `nav2_msgs/action/NavigateToPose` surface. `go2w_mission` owns route segmentation and task sequencing. `go2w_control` continues to own command arbitration and `/stair_exec`.

**Tech Stack:** ROS 2 Humble, `ament_cmake`, `ament_cmake_python`, `rclpy`, `nav2_msgs/action/NavigateToPose`, `go2w_control.action.StairExec`, `pytest`, Bash runtime verifiers.

---

## File Structure

- `go2w_navigation/go2w_navigation_runtime/__init__.py`: runtime package marker.
- `go2w_navigation/go2w_navigation_runtime/flat_nav_executor.py`: navigation-owned `NavigateToPose` verifier Action server and flat execution policy.
- `go2w_navigation/scripts/go2w_flat_nav_executor`: executable entrypoint.
- `go2w_navigation/test/test_phase4c_flat_nav_executor.py`: unit tests for flat policy.
- `go2w_navigation/CMakeLists.txt`: install runtime package, script, launch, and pytest test.
- `go2w_navigation/package.xml`: add `ament_cmake_python`, `geometry_msgs`, `rclpy`, and `std_msgs` dependencies.
- `go2w_mission/go2w_mission/phase4b_mission_runtime.py`: add flat action client and flat segment execution.
- `go2w_mission/test/test_phase4b_mission_runtime.py`: add flat goal and flat timeout classification tests.
- `go2w_mission/launch/phase4b_mission_runtime.launch.py`: optionally launch `go2w_flat_nav_executor`.
- `tools/verify_phase4c_flat_segment_gate.sh`: runtime verifier for flat/stair/flat sequence and flat error modes.
- `docs/verification/phase4c_flat_segment_gate.md`: final acceptance evidence.
- `docs/architecture/architecture_state.md`, `README.md`, `docs/handoff/*`, `tools/verify_phase4_pre_handoff.sh`: state synchronization after acceptance.

## Task 1: Navigation Flat Action Skeleton

**Files:**
- Create: `go2w_navigation/go2w_navigation_runtime/__init__.py`
- Create: `go2w_navigation/go2w_navigation_runtime/flat_nav_executor.py`
- Create: `go2w_navigation/scripts/go2w_flat_nav_executor`
- Create: `go2w_navigation/test/test_phase4c_flat_nav_executor.py`
- Modify: `go2w_navigation/CMakeLists.txt`
- Modify: `go2w_navigation/package.xml`

- [ ] **Step 1: Write failing policy tests**

Create `go2w_navigation/test/test_phase4c_flat_nav_executor.py`:

```python
from go2w_navigation_runtime.flat_nav_executor import FlatNavPolicy


def test_flat_nav_policy_result_code() -> None:
    policy = FlatNavPolicy(min_duration_sec=0.05, timeout_duration_sec=5.0)

    assert policy.result_code(force_fail=False, canceled=False) == "SUCCEEDED"
    assert policy.result_code(force_fail=True, canceled=False) == "FAILED"
    assert policy.result_code(force_fail=False, canceled=True) == "CANCELED"


def test_flat_nav_policy_duration() -> None:
    policy = FlatNavPolicy(min_duration_sec=0.05, timeout_duration_sec=5.0)

    assert policy.execution_duration(0.01, force_timeout=False) == 0.05
    assert policy.execution_duration(0.25, force_timeout=False) == 0.25
    assert policy.execution_duration(0.25, force_timeout=True) == 5.0
```

- [ ] **Step 2: Run RED**

Run:

```bash
PYTHONPATH=go2w_navigation python3 -m pytest go2w_navigation/test/test_phase4c_flat_nav_executor.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'go2w_navigation_runtime'`.

- [ ] **Step 3: Implement flat navigation runtime package**

Create `go2w_navigation/go2w_navigation_runtime/__init__.py`:

```python
"""Runtime helpers for Go2W navigation verification nodes."""
```

Create `go2w_navigation/go2w_navigation_runtime/flat_nav_executor.py`:

```python
from __future__ import annotations

import argparse
import sys
import time


class FlatNavPolicy:
    def __init__(
        self,
        min_duration_sec: float = 0.05,
        timeout_duration_sec: float = 5.0,
    ) -> None:
        self.min_duration_sec = min_duration_sec
        self.timeout_duration_sec = timeout_duration_sec

    def result_code(self, *, force_fail: bool, canceled: bool) -> str:
        if canceled:
            return "CANCELED"
        if force_fail:
            return "FAILED"
        return "SUCCEEDED"

    def execution_duration(self, requested_sec: float, *, force_timeout: bool) -> float:
        if force_timeout:
            return max(self.timeout_duration_sec, requested_sec)
        return max(self.min_duration_sec, requested_sec)


def _string_msg(value: str):
    from std_msgs.msg import String

    msg = String()
    msg.data = value
    return msg


def _flat_twist():
    from geometry_msgs.msg import Twist

    msg = Twist()
    msg.linear.x = 0.04
    return msg


def _zero_twist():
    from geometry_msgs.msg import Twist

    return Twist()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-name", default="/navigate_to_pose")
    parser.add_argument("--mode", choices=("success", "failure", "timeout"), default="success")
    parser.add_argument("--duration-sec", type=float, default=0.2)
    parser.add_argument("--timeout-duration-sec", type=float, default=5.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    import rclpy
    from nav2_msgs.action import NavigateToPose
    from rclpy.action import ActionServer, CancelResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.node import Node

    args = parse_args(sys.argv[1:] if argv is None else argv)

    class FlatNavExecutorNode(Node):
        def __init__(self) -> None:
            super().__init__("go2w_flat_nav_executor")
            self._policy = FlatNavPolicy(timeout_duration_sec=args.timeout_duration_sec)
            self._callback_group = ReentrantCallbackGroup()
            self._owner_pub = self.create_publisher(
                _string_msg("").__class__,
                "/go2w/control/command_owner",
                10,
            )
            self._flat_cmd_pub = self.create_publisher(
                _flat_twist().__class__,
                "/go2w/control/flat_cmd_vel",
                10,
            )
            self._server = ActionServer(
                self,
                NavigateToPose,
                args.action_name,
                self._execute_callback,
                callback_group=self._callback_group,
                cancel_callback=self._cancel_callback,
            )

        def _cancel_callback(self, _cancel_request):
            return CancelResponse.ACCEPT

        def _execute_callback(self, goal_handle):
            del goal_handle.request
            started = time.monotonic()
            force_timeout = args.mode == "timeout"
            force_fail = args.mode == "failure"
            duration = self._policy.execution_duration(
                args.duration_sec,
                force_timeout=force_timeout,
            )
            self._owner_pub.publish(_string_msg("flat"))

            while rclpy.ok():
                elapsed = time.monotonic() - started
                feedback = NavigateToPose.Feedback()
                feedback.navigation_time.sec = int(elapsed)
                feedback.navigation_time.nanosec = int(
                    (elapsed - feedback.navigation_time.sec) * 1_000_000_000
                )
                feedback.distance_remaining = max(0.0, 1.0 - (elapsed / duration))
                goal_handle.publish_feedback(feedback)
                self._flat_cmd_pub.publish(_flat_twist())

                if goal_handle.is_cancel_requested:
                    self._flat_cmd_pub.publish(_zero_twist())
                    goal_handle.canceled()
                    return NavigateToPose.Result()

                if elapsed >= duration:
                    break
                time.sleep(0.1)

            self._flat_cmd_pub.publish(_zero_twist())

            if force_fail:
                goal_handle.abort()
                return NavigateToPose.Result()

            goal_handle.succeed()
            return NavigateToPose.Result()

    rclpy.init()
    node = FlatNavExecutorNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add executable entrypoint**

Create `go2w_navigation/scripts/go2w_flat_nav_executor`:

```python
#!/usr/bin/env python3
from go2w_navigation_runtime.flat_nav_executor import main


if __name__ == "__main__":
    main()
```

Run:

```bash
chmod +x go2w_navigation/scripts/go2w_flat_nav_executor
```

- [ ] **Step 5: Register package, script, dependencies, and test**

Modify `go2w_navigation/CMakeLists.txt` to include:

```cmake
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(go2w_navigation_runtime)

install(PROGRAMS
  scripts/go2w_flat_nav_executor
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_phase4c_flat_nav_executor test/test_phase4c_flat_nav_executor.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
endif()
```

Keep the existing `install(DIRECTORY ...)` block.

Modify `go2w_navigation/package.xml` to add:

```xml
<buildtool_depend>ament_cmake_python</buildtool_depend>
<exec_depend>geometry_msgs</exec_depend>
<exec_depend>rclpy</exec_depend>
<exec_depend>std_msgs</exec_depend>
<test_depend>ament_cmake_pytest</test_depend>
<test_depend>python3-pytest</test_depend>
```

- [ ] **Step 6: Run GREEN and commit**

Run:

```bash
PYTHONPATH=go2w_navigation python3 -m pytest go2w_navigation/test/test_phase4c_flat_nav_executor.py -q
source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_navigation
```

Expected: pytest passes and `go2w_navigation` builds.

Commit:

```bash
git add go2w_navigation
git commit -m "feat: add phase4c flat navigation executor"
```

## Task 2: Mission Runtime Flat Action Dispatch

**Files:**
- Modify: `go2w_mission/go2w_mission/phase4b_mission_runtime.py`
- Modify: `go2w_mission/test/test_phase4b_mission_runtime.py`

- [ ] **Step 1: Write failing mission runtime tests**

Append to `go2w_mission/test/test_phase4b_mission_runtime.py`:

```python
from go2w_mission.phase4b_mission_runtime import (
    build_flat_goal_from_segment,
    final_result_for_flat_timeout,
)
from go2w_mission.phase4a_route_graph import Phase4ARouteGraph, RouteEdge, RouteNode


def _flat_graph() -> Phase4ARouteGraph:
    return Phase4ARouteGraph(
        nodes={
            1: RouteNode(node_id=1, x=0.0, y=0.0, properties={"id": 1}),
            2: RouteNode(node_id=2, x=1.0, y=0.0, properties={"id": 2}),
            3: RouteNode(node_id=3, x=2.0, y=0.0, properties={"id": 3}),
        },
        edges={
            10: RouteEdge(
                edge_id=10,
                start_id=1,
                end_id=2,
                coordinates=[(0.0, 0.0), (1.0, 0.0)],
                properties={"id": 10, "startid": 1, "endid": 2},
            ),
            11: RouteEdge(
                edge_id=11,
                start_id=2,
                end_id=3,
                coordinates=[(1.0, 0.0), (2.0, 0.0)],
                properties={"id": 11, "startid": 2, "endid": 3},
            ),
        },
    )


def test_build_flat_goal_from_segment_uses_last_edge_target() -> None:
    goal = build_flat_goal_from_segment(
        _flat_graph(),
        MissionSegment(segment_type="flat", edge_ids=(10, 11)),
        frame_id="map",
    )

    assert goal.pose.header.frame_id == "map"
    assert goal.pose.pose.position.x == 2.0
    assert goal.pose.pose.position.y == 0.0
    assert goal.pose.pose.orientation.w == 1.0


def test_flat_timeout_result_mapping() -> None:
    assert final_result_for_flat_timeout("flat_timeout") == "MISSION_TIMEOUT"
    assert final_result_for_flat_timeout("flat_cancel") == "MISSION_FAILED"
```

- [ ] **Step 2: Run RED**

Run:

```bash
PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase4b_mission_runtime.py -q
```

Expected: fail with missing `build_flat_goal_from_segment`.

- [ ] **Step 3: Implement flat goal and flat result helpers**

Modify `go2w_mission/go2w_mission/phase4b_mission_runtime.py`:

```python
@dataclass(frozen=True)
class FlatGoalSpec:
    pose: object


def build_flat_goal_from_segment(
    graph: Phase4ARouteGraph,
    segment: MissionSegment,
    *,
    frame_id: str,
) -> FlatGoalSpec:
    from geometry_msgs.msg import PoseStamped

    last_edge = graph.edges[segment.edge_ids[-1]]
    target = graph.nodes[last_edge.end_id]
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.pose.position.x = target.x
    pose.pose.position.y = target.y
    pose.pose.orientation.w = 1.0
    return FlatGoalSpec(pose=pose)


def final_result_for_flat_timeout(mode: str) -> str:
    return "MISSION_TIMEOUT" if mode == "flat_timeout" else "MISSION_FAILED"
```

- [ ] **Step 4: Add flat action client and CLI arguments**

In `Phase4BMissionRuntime.__init__`, import `NavigateToPose`, create
`self.navigate_to_pose_client`, and store `flat_mode`, `flat_result_timeout_sec`,
`flat_nav_action`, and `route_frame_id`.

Add CLI args:

```python
parser.add_argument(
    "--flat-mode",
    choices=("success", "flat_failure", "flat_cancel", "flat_timeout"),
    default="success",
)
parser.add_argument("--flat-result-timeout-sec", type=float, default=4.0)
parser.add_argument("--flat-nav-action", default="/navigate_to_pose")
parser.add_argument("--route-frame-id", default="map")
```

Pass them into the runtime constructor.

- [ ] **Step 5: Execute flat segments through action**

Replace the flat print-only branch in `_execute_segments` with a call to
`_execute_flat_segment(segment)`.

Implement:

```python
def _execute_flat_segment(self, segment: MissionSegment) -> str:
    from action_msgs.msg import GoalStatus

    if not self.navigate_to_pose_client.wait_for_server(timeout_sec=5.0):
        return "FLAT_NAV_UNAVAILABLE"
    print_kv("phase4c_state", "FLAT_SEGMENT_ACTIVE")
    print_kv("phase4c_flat_edges", ",".join(str(edge_id) for edge_id in segment.edge_ids))
    goal = self.navigate_to_pose_type.Goal()
    goal.pose = build_flat_goal_from_segment(
        self.graph,
        segment,
        frame_id=self.route_frame_id,
    ).pose
    send_future = self.navigate_to_pose_client.send_goal_async(goal)
    if not _spin_until(self.node, send_future, 10.0):
        return "FLAT_NAV_FAILED"
    goal_handle = send_future.result()
    if goal_handle is None or not goal_handle.accepted:
        return "FLAT_NAV_FAILED"
    if self.flat_mode == "flat_cancel":
        time.sleep(0.2)
        cancel_future = goal_handle.cancel_goal_async()
        if not _spin_until(self.node, cancel_future, 5.0):
            return "FLAT_NAV_FAILED"
        print_kv("phase4c_flat_cancel", "REQUESTED")
    result_future = goal_handle.get_result_async()
    if not _spin_until(self.node, result_future, self.flat_result_timeout_sec):
        goal_handle.cancel_goal_async()
        return final_result_for_flat_timeout(self.flat_mode)
    wrapped = result_future.result()
    print_kv("phase4c_flat_action_status", wrapped.status)
    if wrapped.status == GoalStatus.STATUS_SUCCEEDED:
        print_kv("phase4c_state", "FLAT_SEGMENT_SUCCEEDED")
        return "MISSION_SUCCEEDED"
    if wrapped.status == GoalStatus.STATUS_CANCELED:
        return "MISSION_CANCELED"
    return "FLAT_NAV_FAILED"
```

In `_execute_segments`, when a flat result is not `MISSION_SUCCEEDED`, print
`phase4b_final_result` with that result and return nonzero except for canceled
or timeout.

- [ ] **Step 6: Run GREEN and commit**

Run:

```bash
PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase4b_mission_runtime.py -q
```

Expected: runtime tests pass.

Commit:

```bash
git add go2w_mission/go2w_mission/phase4b_mission_runtime.py go2w_mission/test/test_phase4b_mission_runtime.py
git commit -m "feat: execute phase4c flat segments via nav action"
```

## Task 3: Phase 4C Launch And Runtime Verifier

**Files:**
- Modify: `go2w_mission/launch/phase4b_mission_runtime.launch.py`
- Create: `tools/verify_phase4c_flat_segment_gate.sh`

- [ ] **Step 1: Add optional flat executor launch node**

Modify `phase4b_mission_runtime.launch.py`:

```python
flat_nav_mode = LaunchConfiguration("flat_nav_mode")
launch_flat_nav_executor = LaunchConfiguration("launch_flat_nav_executor")
```

Add launch arguments for `flat_nav_mode` and `launch_flat_nav_executor`. Add a
`Node` for `go2w_navigation` executable `go2w_flat_nav_executor` with:

```python
condition=IfCondition(launch_flat_nav_executor),
arguments=[
    "--mode", flat_nav_mode,
    "--ros-args", "--log-level", log_level,
],
```

Import `IfCondition` from `launch.conditions`.

- [ ] **Step 2: Write verifier script**

Create `tools/verify_phase4c_flat_segment_gate.sh` using the same bounded cleanup
pattern as `tools/verify_phase4b_mission_segments.sh`. The verifier must:

- build `go2w_navigation go2w_control go2w_mission`,
- start `phase4b_mission_runtime.launch.py launch_flat_nav_executor:=true`,
- wait for `/route_server`, `/go2w_command_gate`, `/go2w_stair_executor`,
  `/go2w_flat_nav_executor`,
- wait for `/compute_route`, `/navigate_to_pose`, `/stair_exec`,
- run the mission runtime in success, flat failure, flat cancel, flat timeout,
  and flat unavailable modes,
- require the stable keys:
  - `phase4b_final_result: MISSION_SUCCEEDED`
  - `phase4b_final_result: FLAT_NAV_FAILED`
  - `phase4b_final_result: MISSION_CANCELED`
  - `phase4b_final_result: MISSION_TIMEOUT`
  - `phase4b_final_result: FLAT_NAV_UNAVAILABLE`
- require success output contains at least two `phase4c_state: FLAT_SEGMENT_SUCCEEDED`
  lines and one `phase4b_state: STAIR_SEGMENT_SUCCEEDED`.

- [ ] **Step 3: Run syntax check and runtime verifier**

Run:

```bash
chmod +x tools/verify_phase4c_flat_segment_gate.sh
bash -n tools/verify_phase4c_flat_segment_gate.sh
./tools/verify_phase4c_flat_segment_gate.sh
```

Expected: `phase4c_flat_segment_gate_result: PASS`.

- [ ] **Step 4: Commit**

```bash
git add go2w_mission/launch/phase4b_mission_runtime.launch.py tools/verify_phase4c_flat_segment_gate.sh
git commit -m "test: add phase4c flat segment verifier"
```

## Task 4: Documentation And State Sync

**Files:**
- Create: `docs/verification/phase4c_flat_segment_gate.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `README.md`
- Modify: `docs/handoff/README.md`
- Modify: `docs/handoff/current_project_state.md`
- Modify: `docs/handoff/next_agent_notes.md`
- Modify: `docs/handoff/risk_cleanup_log.md`
- Modify: `docs/handoff/reading_order_and_file_map.md`
- Modify: `docs/handoff/phase4_migration_handoff_report.md`
- Modify: `docs/handoff/new_model_initialization_prompt.md`
- Modify: `tools/verify_phase4_pre_handoff.sh`

- [ ] **Step 1: Write Phase 4C acceptance evidence**

Create `docs/verification/phase4c_flat_segment_gate.md` with:

- scope and non-scope,
- implemented runtime surface,
- verified facts,
- commands and key output,
- open validation items.

- [ ] **Step 2: Update architecture and handoff state**

Update current phase to `Phase 4C-min`, add the verified flat execution gate,
and keep the non-production boundary explicit.

- [ ] **Step 3: Update pre-handoff verifier**

Add the Phase 4C evidence file and `tools/verify_phase4c_flat_segment_gate.sh`
to required files and bash syntax checks. Add a required evidence pattern:

```bash
require_contains "docs/verification/phase4c_flat_segment_gate.md" 'phase4c_flat_segment_gate_result: PASS' "phase4c_acceptance_evidence"
```

- [ ] **Step 4: Run final verification**

Run:

```bash
./tools/verify_phase4_pre_handoff.sh
timeout 120s ./tools/verify_phase4a_stair_handoff.sh
./tools/verify_phase4b_mission_segments.sh
./tools/verify_phase4c_flat_segment_gate.sh
source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_navigation go2w_control go2w_mission
source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_navigation go2w_control go2w_mission
source /opt/ros/humble/setup.bash && colcon test-result --verbose
git diff --check
```

Expected: all commands pass.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/architecture/architecture_state.md docs/handoff docs/verification/phase4c_flat_segment_gate.md tools/verify_phase4_pre_handoff.sh
git commit -m "docs: record phase4c flat segment acceptance"
```

## Plan Self-Review

- Spec coverage: all design requirements map to Tasks 1-4.
- Placeholder scan: no open placeholders remain.
- Type consistency: flat action uses standard `nav2_msgs/action/NavigateToPose`;
  stair action remains `go2w_control/action/StairExec`.
- Scope guard: no AMCL, `map_server`, `map -> odom`, Unitree model, elevation,
  traversability, or automatic connector generation is included.
