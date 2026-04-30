# Phase 4B-Min Mission Segment Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 4B-min mission segment runtime that computes the existing manual route, splits it into flat/stair/flat segments, calls `/stair_exec` for stair segments, and reports stable mission result keys.

**Architecture:** `go2w_mission` owns segment decomposition and the one-shot mission runtime. `go2w_control` remains the owner of command arbitration and `/stair_exec`. `go2w_navigation` remains the owner of route graph assets and `nav2_route` configuration.

**Tech Stack:** ROS 2 Humble, `ament_cmake`, `ament_cmake_python`, `rclpy`, `nav2_msgs`, `go2w_control.action.StairExec`, `pytest`, Bash verification scripts.

---

## File Structure

- `go2w_mission/go2w_mission/phase4b_mission_segments.py`: pure mission segment data model and route-edge segmentation helpers.
- `go2w_mission/test/test_phase4b_mission_segments.py`: unit tests for flat/stair/flat segmentation, no-stair routes, missing edge rejection, and stair result classification.
- `go2w_mission/go2w_mission/phase4b_mission_runtime.py`: one-shot mission runtime CLI that calls `/compute_route`, builds mission segments, executes stair segments through `/stair_exec`, and prints stable key-value diagnostics.
- `go2w_mission/scripts/go2w_phase4b_mission_runtime`: executable entrypoint for the one-shot runtime.
- `go2w_mission/launch/phase4b_mission_runtime.launch.py`: minimal Phase 4B-min launch path for route server, lifecycle manager, command gate, and stair executor.
- `go2w_mission/CMakeLists.txt`: install the new launch/script and register new pytest test.
- `tools/verify_phase4b_mission_segments.sh`: replayable verifier for success, failure, cancel, timeout, route-unavailable, and connector-unavailable modes.
- `docs/verification/phase4b_mission_segment_runtime.md`: final acceptance evidence.
- `docs/architecture/architecture_state.md`, `README.md`, `docs/handoff/current_project_state.md`, `docs/handoff/next_agent_notes.md`, `docs/handoff/risk_cleanup_log.md`, `docs/handoff/reading_order_and_file_map.md`: state and handoff synchronization.

## Task 1: Segment Model And Result Classification

**Files:**
- Create: `go2w_mission/go2w_mission/phase4b_mission_segments.py`
- Create: `go2w_mission/test/test_phase4b_mission_segments.py`
- Modify: `go2w_mission/CMakeLists.txt`

- [ ] **Step 1: Write failing segment tests**

Create `go2w_mission/test/test_phase4b_mission_segments.py`:

```python
from pathlib import Path

import pytest

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph
from go2w_mission.phase4b_mission_segments import (
    MissionSegment,
    build_mission_segments,
    classify_stair_result,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = (
    REPO_ROOT
    / "go2w_navigation"
    / "graphs"
    / "phase3c_hospital_multifloor_route.geojson"
)


def _graph() -> Phase4ARouteGraph:
    return Phase4ARouteGraph.from_file(GRAPH_PATH)


def test_route_with_stair_edge_splits_into_flat_stair_flat() -> None:
    segments = build_mission_segments(_graph(), [300, 301, 500, 400, 401])

    assert segments == [
        MissionSegment(segment_type="flat", edge_ids=(300, 301)),
        MissionSegment(
            segment_type="stair",
            edge_ids=(500,),
            connector_id="stair_a",
            floor_from="F1",
            floor_to="F2",
        ),
        MissionSegment(segment_type="flat", edge_ids=(400, 401)),
    ]


def test_flat_only_route_remains_one_flat_segment() -> None:
    segments = build_mission_segments(_graph(), [300, 302])

    assert segments == [MissionSegment(segment_type="flat", edge_ids=(300, 302))]


def test_missing_edge_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing_route_edge:999"):
        build_mission_segments(_graph(), [300, 999])


def test_stair_result_classification() -> None:
    assert classify_stair_result("SUCCEEDED") == "MISSION_SUCCEEDED"
    assert classify_stair_result("FAILED") == "MISSION_FAILED"
    assert classify_stair_result("CANCELED") == "MISSION_CANCELED"
    assert classify_stair_result("OTHER") == "MISSION_FAILED"
```

- [ ] **Step 2: Run RED**

Run:

```bash
PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase4b_mission_segments.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `go2w_mission.phase4b_mission_segments`.

- [ ] **Step 3: Implement segment module**

Create `go2w_mission/go2w_mission/phase4b_mission_segments.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph, RouteEdge


@dataclass(frozen=True)
class MissionSegment:
    segment_type: str
    edge_ids: tuple[int, ...]
    connector_id: str = ""
    floor_from: str = ""
    floor_to: str = ""


def build_mission_segments(
    graph: Phase4ARouteGraph,
    edge_ids: list[int],
) -> list[MissionSegment]:
    segments: list[MissionSegment] = []
    flat_buffer: list[int] = []

    def flush_flat() -> None:
        if flat_buffer:
            segments.append(MissionSegment(segment_type="flat", edge_ids=tuple(flat_buffer)))
            flat_buffer.clear()

    for edge_id in edge_ids:
        edge = graph.edges.get(edge_id)
        if edge is None:
            raise ValueError(f"missing_route_edge:{edge_id}")
        if edge.is_stair_required:
            flush_flat()
            segments.append(_stair_segment(edge))
            continue
        flat_buffer.append(edge_id)

    flush_flat()
    return segments


def _stair_segment(edge: RouteEdge) -> MissionSegment:
    return MissionSegment(
        segment_type="stair",
        edge_ids=(edge.edge_id,),
        connector_id=str(edge.properties.get("connector_id", "")),
        floor_from=str(edge.properties.get("floor_from", "")),
        floor_to=str(edge.properties.get("floor_to", "")),
    )


def classify_stair_result(result_code: str) -> str:
    if result_code == "SUCCEEDED":
        return "MISSION_SUCCEEDED"
    if result_code == "CANCELED":
        return "MISSION_CANCELED"
    return "MISSION_FAILED"
```

- [ ] **Step 4: Register pytest test**

Modify `go2w_mission/CMakeLists.txt` inside `if(BUILD_TESTING)`:

```cmake
  ament_add_pytest_test(test_phase4b_mission_segments test/test_phase4b_mission_segments.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
```

- [ ] **Step 5: Run GREEN and commit**

Run:

```bash
PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase4b_mission_segments.py -q
```

Expected: `4 passed`.

Commit:

```bash
git add go2w_mission/go2w_mission/phase4b_mission_segments.py \
  go2w_mission/test/test_phase4b_mission_segments.py \
  go2w_mission/CMakeLists.txt
git commit -m "feat: add phase4b mission segment model"
```

## Task 2: One-Shot Mission Runtime CLI

**Files:**
- Create: `go2w_mission/go2w_mission/phase4b_mission_runtime.py`
- Create: `go2w_mission/scripts/go2w_phase4b_mission_runtime`
- Create: `go2w_mission/test/test_phase4b_mission_runtime.py`
- Modify: `go2w_mission/CMakeLists.txt`

- [ ] **Step 1: Write failing runtime policy tests**

Create `go2w_mission/test/test_phase4b_mission_runtime.py`:

```python
from go2w_mission.phase4b_mission_runtime import (
    build_stair_goal_from_segment,
    final_result_for_timeout,
)
from go2w_mission.phase4b_mission_segments import MissionSegment


def test_build_stair_goal_from_segment_success_mode() -> None:
    spec = build_stair_goal_from_segment(
        MissionSegment(
            segment_type="stair",
            edge_ids=(500,),
            connector_id="stair_a",
            floor_from="F1",
            floor_to="F2",
        ),
        mode="success",
        expected_duration_sec=0.3,
    )

    assert spec.connector_id == "stair_a"
    assert spec.edge_id == 500
    assert spec.direction == "F1_to_F2"
    assert spec.expected_duration_sec == 0.3
    assert spec.force_fail is False
    assert spec.force_timeout is False


def test_build_stair_goal_failure_and_timeout_modes() -> None:
    segment = MissionSegment(
        segment_type="stair",
        edge_ids=(500,),
        connector_id="stair_a",
        floor_from="F1",
        floor_to="F2",
    )

    failure = build_stair_goal_from_segment(segment, mode="failure", expected_duration_sec=0.3)
    timeout = build_stair_goal_from_segment(segment, mode="timeout", expected_duration_sec=0.3)
    cancel = build_stair_goal_from_segment(segment, mode="cancel", expected_duration_sec=0.3)

    assert failure.force_fail is True
    assert failure.force_timeout is False
    assert timeout.force_timeout is True
    assert cancel.force_timeout is True


def test_final_result_for_timeout() -> None:
    assert final_result_for_timeout("timeout") == "MISSION_TIMEOUT"
    assert final_result_for_timeout("success") == "MISSION_FAILED"
```

- [ ] **Step 2: Run RED**

Run:

```bash
PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_phase4b_mission_runtime.py -q
```

Expected: FAIL because `go2w_mission.phase4b_mission_runtime` does not exist.

- [ ] **Step 3: Add runtime implementation**

Create `go2w_mission/go2w_mission/phase4b_mission_runtime.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
import argparse
from pathlib import Path
import sys
import time

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph
from go2w_mission.phase4b_mission_segments import (
    MissionSegment,
    build_mission_segments,
    classify_stair_result,
)


@dataclass(frozen=True)
class StairGoalSpec:
    connector_id: str
    edge_id: int
    direction: str
    expected_duration_sec: float
    force_fail: bool
    force_timeout: bool


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def build_stair_goal_from_segment(
    segment: MissionSegment,
    *,
    mode: str,
    expected_duration_sec: float,
) -> StairGoalSpec:
    return StairGoalSpec(
        connector_id=segment.connector_id,
        edge_id=segment.edge_ids[0],
        direction=f"{segment.floor_from}_to_{segment.floor_to}",
        expected_duration_sec=expected_duration_sec,
        force_fail=mode == "failure",
        force_timeout=mode in {"timeout", "cancel"},
    )


def final_result_for_timeout(mode: str) -> str:
    return "MISSION_TIMEOUT" if mode == "timeout" else "MISSION_FAILED"
```

Then extend the same file with the ROS runtime:

```python
def _spin_until(node, future, timeout_sec: float) -> bool:
    import rclpy

    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    return future.done()


class Phase4BMissionRuntime:
    def __init__(
        self,
        *,
        node,
        graph_file: Path,
        start_id: int,
        goal_id: int,
        mode: str,
        expected_duration_sec: float,
        result_timeout_sec: float,
        compute_route_action: str,
    ) -> None:
        from nav2_msgs.action import ComputeRoute
        from rclpy.action import ActionClient

        from go2w_control.action import StairExec

        self.node = node
        self.graph = Phase4ARouteGraph.from_file(graph_file)
        self.start_id = start_id
        self.goal_id = goal_id
        self.mode = mode
        self.expected_duration_sec = expected_duration_sec
        self.result_timeout_sec = result_timeout_sec
        self.compute_route_type = ComputeRoute
        self.stair_exec_type = StairExec
        self.compute_route_client = ActionClient(node, ComputeRoute, compute_route_action)
        self.stair_exec_client = ActionClient(node, StairExec, "/stair_exec")

    def run(self) -> int:
        print_kv("phase4b_state", "ROUTE_REQUESTED")
        edge_ids = self._compute_route_edge_ids()
        if not edge_ids:
            print_kv("phase4b_final_result", "ROUTE_UNAVAILABLE")
            return 2
        print_kv("phase4b_state", "ROUTE_COMPUTED")

        mismatches = self.graph.geometry_mismatches()
        if mismatches:
            print_kv("phase4b_graph_geometry", "FAIL")
            print_kv("phase4b_final_result", "CONNECTOR_UNAVAILABLE")
            return 2

        try:
            segments = build_mission_segments(self.graph, edge_ids)
        except ValueError as exc:
            print_kv("phase4b_segment_error", str(exc))
            print_kv("phase4b_final_result", "CONNECTOR_UNAVAILABLE")
            return 2
        if not any(segment.segment_type == "stair" for segment in segments):
            print_kv("phase4b_final_result", "CONNECTOR_UNAVAILABLE")
            return 2

        print_kv("phase4b_state", "SEGMENTS_READY")
        print_kv("phase4b_segments", _format_segments(segments))
        return self._execute_segments(segments)

    def _compute_route_edge_ids(self) -> list[int]:
        if not self.compute_route_client.wait_for_server(timeout_sec=5.0):
            print_kv("phase4b_route_action_server", "FAIL_UNAVAILABLE")
            return []
        goal = self.compute_route_type.Goal()
        goal.start_id = self.start_id
        goal.goal_id = self.goal_id
        goal.use_start = False
        goal.use_poses = False
        send_future = self.compute_route_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            print_kv("phase4b_route_goal_response", "FAIL_TIMEOUT")
            return []
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print_kv("phase4b_route_goal_accepted", "False")
            return []
        result_future = goal_handle.get_result_async()
        if not _spin_until(self.node, result_future, 10.0):
            print_kv("phase4b_route_result", "FAIL_TIMEOUT")
            return []
        wrapped = result_future.result()
        edge_ids = [int(edge.edgeid) for edge in wrapped.result.route.edges]
        print_kv("phase4b_route_edge_ids", ",".join(str(edge_id) for edge_id in edge_ids))
        return edge_ids

    def _execute_segments(self, segments: list[MissionSegment]) -> int:
        for index, segment in enumerate(segments):
            print_kv("phase4b_segment_index", index)
            print_kv("phase4b_segment_type", segment.segment_type)
            if segment.segment_type == "flat":
                print_kv("phase4b_state", "FLAT_SEGMENT_ACTIVE")
                print_kv("phase4b_flat_edges", ",".join(str(edge_id) for edge_id in segment.edge_ids))
                print_kv("phase4b_state", "FLAT_SEGMENT_SUCCEEDED")
                continue
            result = self._execute_stair_segment(segment)
            if result != "MISSION_SUCCEEDED":
                print_kv("phase4b_final_result", result)
                return 0 if result in {"MISSION_CANCELED", "MISSION_TIMEOUT"} else 2
        print_kv("phase4b_final_result", "MISSION_SUCCEEDED")
        return 0

    def _execute_stair_segment(self, segment: MissionSegment) -> str:
        from action_msgs.msg import GoalStatus

        if not self.stair_exec_client.wait_for_server(timeout_sec=5.0):
            return "MISSION_FAILED"
        print_kv("phase4b_state", "STAIR_SEGMENT_ACTIVE")
        spec = build_stair_goal_from_segment(
            segment,
            mode=self.mode,
            expected_duration_sec=self.expected_duration_sec,
        )
        goal = self.stair_exec_type.Goal()
        goal.connector_id = spec.connector_id
        goal.edge_id = spec.edge_id
        goal.direction = spec.direction
        goal.expected_duration_sec = spec.expected_duration_sec
        goal.force_fail = spec.force_fail
        goal.force_timeout = spec.force_timeout

        send_future = self.stair_exec_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            return "MISSION_FAILED"
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return "MISSION_FAILED"
        if self.mode == "cancel":
            time.sleep(0.3)
            cancel_future = goal_handle.cancel_goal_async()
            if not _spin_until(self.node, cancel_future, 5.0):
                return "MISSION_FAILED"
            print_kv("phase4b_stair_cancel", "REQUESTED")
        result_future = goal_handle.get_result_async()
        if not _spin_until(self.node, result_future, self.result_timeout_sec):
            goal_handle.cancel_goal_async()
            return final_result_for_timeout(self.mode)
        wrapped = result_future.result()
        result = wrapped.result
        print_kv("phase4b_stair_action_status", wrapped.status)
        print_kv("phase4b_stair_result_code", result.result_code)
        if wrapped.status == GoalStatus.STATUS_CANCELED:
            return "MISSION_CANCELED"
        if result.result_code == "SUCCEEDED":
            print_kv("phase4b_state", "STAIR_SEGMENT_SUCCEEDED")
        return classify_stair_result(result.result_code)


def _format_segments(segments: list[MissionSegment]) -> str:
    formatted = []
    for segment in segments:
        edges = "|".join(str(edge_id) for edge_id in segment.edge_ids)
        formatted.append(f"{segment.segment_type}:{edges}")
    return ";".join(formatted)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph-file", required=True)
    parser.add_argument("--start-id", type=int, default=100)
    parser.add_argument("--goal-id", type=int, default=202)
    parser.add_argument(
        "--mode",
        choices=("success", "failure", "cancel", "timeout"),
        default="success",
    )
    parser.add_argument("--expected-duration-sec", type=float, default=0.3)
    parser.add_argument("--result-timeout-sec", type=float, default=4.0)
    parser.add_argument("--compute-route-action", default="/compute_route")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import rclpy
    from rclpy.node import Node

    args = parse_args(sys.argv[1:] if argv is None else argv)
    rclpy.init()
    node = Node("go2w_phase4b_mission_runtime")
    try:
        runtime = Phase4BMissionRuntime(
            node=node,
            graph_file=Path(args.graph_file),
            start_id=args.start_id,
            goal_id=args.goal_id,
            mode=args.mode,
            expected_duration_sec=args.expected_duration_sec,
            result_timeout_sec=args.result_timeout_sec,
            compute_route_action=args.compute_route_action,
        )
        return runtime.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add executable script**

Create `go2w_mission/scripts/go2w_phase4b_mission_runtime`:

```python
#!/usr/bin/env python3
from go2w_mission.phase4b_mission_runtime import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Make it executable:

```bash
chmod +x go2w_mission/scripts/go2w_phase4b_mission_runtime
```

- [ ] **Step 5: Register script and test**

Modify `go2w_mission/CMakeLists.txt`:

```cmake
install(PROGRAMS
  scripts/go2w_phase4a_handoff_demo
  scripts/go2w_phase4b_mission_runtime
  DESTINATION lib/${PROJECT_NAME}
)
```

Add pytest registration:

```cmake
  ament_add_pytest_test(test_phase4b_mission_runtime test/test_phase4b_mission_runtime.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
```

- [ ] **Step 6: Run tests and commit**

Run:

```bash
PYTHONPATH=go2w_mission python3 -m pytest \
  go2w_mission/test/test_phase4b_mission_segments.py \
  go2w_mission/test/test_phase4b_mission_runtime.py \
  -q
```

Expected: `7 passed`.

Commit:

```bash
git add go2w_mission/go2w_mission/phase4b_mission_runtime.py \
  go2w_mission/scripts/go2w_phase4b_mission_runtime \
  go2w_mission/test/test_phase4b_mission_runtime.py \
  go2w_mission/CMakeLists.txt
git commit -m "feat: add phase4b mission runtime"
```

## Task 3: Launch And Runtime Verifier

**Files:**
- Create: `go2w_mission/launch/phase4b_mission_runtime.launch.py`
- Create: `tools/verify_phase4b_mission_segments.sh`
- Modify: `go2w_mission/CMakeLists.txt`

- [ ] **Step 1: Add launch file**

Create `go2w_mission/launch/phase4b_mission_runtime.launch.py` by copying the
Phase 4A launch shape and changing descriptions to Phase 4B-min. It must launch
only:

- `nav2_route/route_server`;
- `nav2_lifecycle_manager/lifecycle_manager`;
- `go2w_control/go2w_command_gate`;
- `go2w_control/go2w_stair_executor`.

Do not launch a persistent Mission Orchestrator node.

- [ ] **Step 2: Add verifier script**

Create `tools/verify_phase4b_mission_segments.sh` with:

```bash
#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE4B_EVIDENCE_DIR:-/tmp/go2w_phase4b_mission_segments_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 100 ))}"
LAUNCH_PID=""

print_kv() { printf '%s: %s\n' "$1" "$2"; }

source_file_checked() {
  local setup_file="$1"
  local key="$2"
  if [ ! -f "${setup_file}" ]; then
    print_kv "${key}" "missing:${setup_file}"
    exit 2
  fi
  set +u
  source "${setup_file}"
  set -u
}

set -u

cleanup() {
  if [ -n "${LAUNCH_PID}" ]; then
    kill -INT -- "-${LAUNCH_PID}" 2>/dev/null || kill -INT "${LAUNCH_PID}" 2>/dev/null || true
    sleep 2
    kill -TERM -- "-${LAUNCH_PID}" 2>/dev/null || kill -TERM "${LAUNCH_PID}" 2>/dev/null || true
    wait "${LAUNCH_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

wait_for_action() {
  local action_name="$1"
  local timeout_seconds="$2"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 5s ros2 action list 2>/dev/null | grep -qx "${action_name}"; then
      print_kv "action_${action_name}" "PRESENT"
      return
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  print_kv "action_${action_name}" "MISSING"
  exit 2
}

run_mode() {
  local mode="$1"
  local expected="$2"
  local output_file="${EVIDENCE_DIR}/mission_${mode}.txt"
  if ! timeout 45s ros2 run go2w_mission go2w_phase4b_mission_runtime \
    --graph-file "${GRAPH_FILE}" \
    --mode "${mode}" \
    --expected-duration-sec 0.3 \
    --result-timeout-sec "$([ "${mode}" = timeout ] && printf '0.5' || printf '4.0')" \
    >"${output_file}" 2>&1; then
    print_kv "mission_${mode}" "PROCESS_FAILED"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  fi
  if grep -qx "phase4b_final_result: ${expected}" "${output_file}"; then
    print_kv "mission_${mode}" "PASS"
    return
  fi
  print_kv "mission_${mode}" "FAIL"
  sed -n '1,240p' "${output_file}" || true
  exit 2
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  print_kv "phase4b_mission_segments_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  (cd "${REPO_ROOT}" && colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation)
  source_file_checked "${REPO_SETUP}" "repo_setup"

  local nav_share
  nav_share="$(ros2 pkg prefix go2w_navigation)/share/go2w_navigation"
  GRAPH_FILE="${nav_share}/graphs/phase3c_hospital_multifloor_route.geojson"
  export GRAPH_FILE

  setsid ros2 launch go2w_mission phase4b_mission_runtime.launch.py \
    use_sim_time:=false >"${EVIDENCE_DIR}/phase4b_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_action "/compute_route" 45
  wait_for_action "/stair_exec" 45

  run_mode "success" "MISSION_SUCCEEDED"
  run_mode "failure" "MISSION_FAILED"
  run_mode "cancel" "MISSION_CANCELED"
  run_mode "timeout" "MISSION_TIMEOUT"

  local route_unavailable_file="${EVIDENCE_DIR}/mission_route_unavailable.txt"
  timeout 20s ros2 run go2w_mission go2w_phase4b_mission_runtime \
    --graph-file "${GRAPH_FILE}" \
    --compute-route-action /missing_compute_route \
    >"${route_unavailable_file}" 2>&1 || true
  grep -qx "phase4b_final_result: ROUTE_UNAVAILABLE" "${route_unavailable_file}"
  print_kv "mission_route_unavailable" "PASS"

  local connector_unavailable_file="${EVIDENCE_DIR}/mission_connector_unavailable.txt"
  timeout 30s ros2 run go2w_mission go2w_phase4b_mission_runtime \
    --graph-file "${GRAPH_FILE}" \
    --start-id 100 \
    --goal-id 103 \
    >"${connector_unavailable_file}" 2>&1 || true
  grep -qx "phase4b_final_result: CONNECTOR_UNAVAILABLE" "${connector_unavailable_file}"
  print_kv "mission_connector_unavailable" "PASS"

  print_kv "phase4b_mission_segments_result" "PASS"
}

main "$@"
```

- [ ] **Step 3: Make verifier executable and syntax-check**

Run:

```bash
chmod +x tools/verify_phase4b_mission_segments.sh
bash -n tools/verify_phase4b_mission_segments.sh
```

Expected: exit `0`.

- [ ] **Step 4: Register launch install and run verifier**

`go2w_mission/CMakeLists.txt` already installs the `launch` directory. Run:

```bash
./tools/verify_phase4b_mission_segments.sh
```

Expected: output includes `phase4b_mission_segments_result: PASS`.

- [ ] **Step 5: Commit**

```bash
git add go2w_mission/launch/phase4b_mission_runtime.launch.py \
  tools/verify_phase4b_mission_segments.sh \
  go2w_mission/CMakeLists.txt
git commit -m "test: add phase4b mission verifier"
```

## Task 4: Documentation And State Sync

**Files:**
- Create: `docs/verification/phase4b_mission_segment_runtime.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `README.md`
- Modify: `docs/handoff/current_project_state.md`
- Modify: `docs/handoff/next_agent_notes.md`
- Modify: `docs/handoff/risk_cleanup_log.md`
- Modify: `docs/handoff/reading_order_and_file_map.md`

- [ ] **Step 1: Write acceptance evidence**

Create `docs/verification/phase4b_mission_segment_runtime.md` with sections:

- Scope;
- Implemented Runtime Surface;
- Verified Facts;
- Verification Evidence;
- Reproduction Command;
- Open Validation Items.

Record fresh command outputs from Task 3 and final package tests.

- [ ] **Step 2: Update state documents**

Update `docs/architecture/architecture_state.md` to set active phase to
`Phase 4B-min` and state that it proves mission-owned segment decomposition and
stair Action dispatch, not production mission orchestration or real navigation.

Update README and handoff notes with the new verifier:

```bash
./tools/verify_phase4b_mission_segments.sh
```

- [ ] **Step 3: Run final verification**

Run:

```bash
./tools/verify_phase4_pre_handoff.sh
timeout 120s ./tools/verify_phase4a_stair_handoff.sh
bash -n tools/verify_phase4b_mission_segments.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
colcon test --packages-select go2w_control go2w_mission go2w_navigation
colcon test-result --verbose
./tools/verify_phase4b_mission_segments.sh
```

Expected:

- both handoff scripts report `PASS`;
- build completes for 3 packages;
- test-result shows 0 errors and 0 failures;
- Phase 4B verifier reports `phase4b_mission_segments_result: PASS`.

- [ ] **Step 4: Commit docs**

```bash
git add docs/verification/phase4b_mission_segment_runtime.md \
  docs/architecture/architecture_state.md \
  README.md \
  docs/handoff/current_project_state.md \
  docs/handoff/next_agent_notes.md \
  docs/handoff/risk_cleanup_log.md \
  docs/handoff/reading_order_and_file_map.md
git commit -m "docs: record phase4b mission segment acceptance"
```

## Self-Review

- Spec coverage: every design requirement has a task.
- Placeholder scan: no open placeholder markers remain.
- Type consistency: `MissionSegment`, `StairGoalSpec`, and result strings are used consistently across tasks.
- Scope check: the plan does not introduce production Mission Orchestrator, real Nav2 flat execution, AMCL, map server, elevation mapping, traversability, automatic connector generation, or `StairExec.action` changes.
