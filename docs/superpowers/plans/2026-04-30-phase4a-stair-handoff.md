# Phase 4A Stair Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 4A minimal stair-state-machine and command-ownership handoff skeleton.

**Architecture:** `go2w_mission` owns route interpretation and handoff sequencing, while `go2w_control` owns the `/stair_exec` Action endpoint and final `/cmd_vel` arbitration. `go2w_navigation` remains the owner of the Phase 3C route graph asset and receives only the required geometry consistency fix.

**Tech Stack:** ROS 2 Humble, `ament_cmake`, `ament_cmake_python`, `rosidl_default_generators`, `rclpy`, `nav2_msgs`, `geometry_msgs`, `std_msgs`, `pytest`, Bash verification scripts.

---

## File Structure

- `go2w_control/action/StairExec.action`: dedicated stair execution Action contract.
- `go2w_control/go2w_control/command_gate.py`: command ownership gate core and ROS node.
- `go2w_control/go2w_control/stair_executor.py`: skeleton `/stair_exec` Action server.
- `go2w_control/scripts/go2w_command_gate`: executable entrypoint for the gate.
- `go2w_control/scripts/go2w_stair_executor`: executable entrypoint for the Action server.
- `go2w_control/test/test_command_gate.py`: unit tests for command ownership.
- `go2w_mission/go2w_mission/phase4a_route_graph.py`: graph parsing, metadata lookup, geometry validation.
- `go2w_mission/go2w_mission/phase4a_handoff_demo.py`: one-shot state-machine demo client.
- `go2w_mission/scripts/go2w_phase4a_handoff_demo`: executable entrypoint for the demo.
- `go2w_mission/launch/phase4a_stair_handoff.launch.py`: launches route server, lifecycle manager, gate, and stair executor.
- `go2w_mission/test/test_phase4a_route_graph.py`: route graph tests.
- `go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson`: fix edge geometry mismatches.
- `tools/verify_phase4a_stair_handoff.sh`: replayable Phase 4A verifier.
- `docs/verification/phase4a_stair_handoff_acceptance.md`: final evidence record.
- `docs/architecture/architecture_state.md`, `README.md`, and `docs/handoff/*`: status synchronization.

## Task 1: Route Graph Validation And Geometry Fix

**Files:**
- Create: `go2w_mission/go2w_mission/__init__.py`
- Create: `go2w_mission/go2w_mission/phase4a_route_graph.py`
- Create: `go2w_mission/test/test_phase4a_route_graph.py`
- Modify: `go2w_mission/CMakeLists.txt`
- Modify: `go2w_mission/package.xml`
- Modify: `go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson`

- [ ] **Step 1: Write failing graph tests**

Create `go2w_mission/test/test_phase4a_route_graph.py` with tests that load
`go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson`, assert no
edge geometry mismatches, and assert route `100 -> 202` includes stair edge
`500`.

- [ ] **Step 2: Run RED**

Run:

```bash
pytest go2w_mission/test/test_phase4a_route_graph.py -q
```

Expected: FAIL because `go2w_mission.phase4a_route_graph` does not exist.

- [ ] **Step 3: Add minimal graph module**

Create `go2w_mission/go2w_mission/phase4a_route_graph.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RouteNode:
    node_id: int
    x: float
    y: float
    properties: dict[str, Any]


@dataclass(frozen=True)
class RouteEdge:
    edge_id: int
    start_id: int
    end_id: int
    coordinates: list[tuple[float, float]]
    properties: dict[str, Any]

    @property
    def is_stair_required(self) -> bool:
        return (
            self.properties.get("mode") == "stair"
            and bool(self.properties.get("stair_exec_required"))
            and bool(self.properties.get("connector_id"))
        )


class Phase4ARouteGraph:
    def __init__(self, nodes: dict[int, RouteNode], edges: dict[int, RouteEdge]) -> None:
        self.nodes = nodes
        self.edges = edges

    @classmethod
    def from_file(cls, path: str | Path) -> "Phase4ARouteGraph":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes: dict[int, RouteNode] = {}
        edges: dict[int, RouteEdge] = {}
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            if geometry.get("type") == "Point":
                node_id = int(props["id"])
                x, y = geometry["coordinates"][:2]
                nodes[node_id] = RouteNode(node_id, float(x), float(y), dict(props))
            elif geometry.get("type") == "MultiLineString":
                edge_id = int(props["id"])
                coords = [
                    (float(point[0]), float(point[1]))
                    for point in geometry["coordinates"][0]
                ]
                edges[edge_id] = RouteEdge(
                    edge_id=edge_id,
                    start_id=int(props["startid"]),
                    end_id=int(props["endid"]),
                    coordinates=coords,
                    properties=dict(props),
                )
        return cls(nodes=nodes, edges=edges)

    def geometry_mismatches(self) -> list[str]:
        mismatches: list[str] = []
        for edge in self.edges.values():
            start = self.nodes[edge.start_id]
            end = self.nodes[edge.end_id]
            if edge.coordinates[0] != (start.x, start.y):
                mismatches.append(f"edge_{edge.edge_id}_start")
            if edge.coordinates[-1] != (end.x, end.y):
                mismatches.append(f"edge_{edge.edge_id}_end")
        return mismatches

    def stair_edges_for_ids(self, edge_ids: list[int]) -> list[RouteEdge]:
        return [
            self.edges[edge_id]
            for edge_id in edge_ids
            if edge_id in self.edges and self.edges[edge_id].is_stair_required
        ]
```

- [ ] **Step 4: Run tests and observe geometry failure**

Run:

```bash
PYTHONPATH=. pytest go2w_mission/test/test_phase4a_route_graph.py -q
```

Expected: FAIL with mismatches for edge `311` and edge `400`.

- [ ] **Step 5: Fix graph geometry**

Modify:

- edge `311` coordinates to `[[[3.0, 0.0], [1.5, 0.0]]]`;
- edge `400` coordinates to `[[[6.0, 0.0], [7.5, 0.0]]]`.

- [ ] **Step 6: Run GREEN**

Run:

```bash
PYTHONPATH=. pytest go2w_mission/test/test_phase4a_route_graph.py -q
python3 -m json.tool go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson >/dev/null
```

Expected: both commands exit `0`.

## Task 2: Control Action And Command Gate

**Files:**
- Create: `go2w_control/action/StairExec.action`
- Create: `go2w_control/go2w_control/__init__.py`
- Create: `go2w_control/go2w_control/command_gate.py`
- Create: `go2w_control/scripts/go2w_command_gate`
- Create: `go2w_control/test/test_command_gate.py`
- Modify: `go2w_control/CMakeLists.txt`
- Modify: `go2w_control/package.xml`

- [ ] **Step 1: Write command gate tests**

Create `go2w_control/test/test_command_gate.py` with tests for default owner,
flat forwarding, stair forwarding, invalid owner rejection, and muted source
behavior.

- [ ] **Step 2: Run RED**

Run:

```bash
pytest go2w_control/test/test_command_gate.py -q
```

Expected: FAIL because `go2w_control.command_gate` does not exist.

- [ ] **Step 3: Add Action definition**

Create `go2w_control/action/StairExec.action`:

```text
string connector_id
uint16 edge_id
string direction
float32 expected_duration_sec
bool force_fail
bool force_timeout
---
bool success
string result_code
string message
builtin_interfaces/Duration elapsed_time
---
string phase
float32 progress
string owner
```

- [ ] **Step 4: Add command gate implementation**

Create `go2w_control/go2w_control/command_gate.py` with a pure
`CommandGateCore` plus `CommandGateNode` that subscribes to owner requests,
flat commands, and stair commands, then publishes only the active owner's
command to `/cmd_vel`.

- [ ] **Step 5: Run GREEN for command gate tests**

Run:

```bash
PYTHONPATH=. pytest go2w_control/test/test_command_gate.py -q
```

Expected: PASS.

- [ ] **Step 6: Wire package build**

Modify `go2w_control/CMakeLists.txt` to use `ament_cmake_python`,
`rosidl_default_generators`, `ament_python_install_package(${PROJECT_NAME})`,
`rosidl_generate_interfaces`, install scripts, and add pytest tests.

## Task 3: Stair Executor Action Server

**Files:**
- Create: `go2w_control/go2w_control/stair_executor.py`
- Create: `go2w_control/scripts/go2w_stair_executor`
- Modify: `go2w_control/CMakeLists.txt`
- Modify: `go2w_control/package.xml`

- [ ] **Step 1: Add minimal Action server**

Create `go2w_control/go2w_control/stair_executor.py` with an `ActionServer`
for `/stair_exec`. On accepted goals, publish owner `stair`, publish bounded
`/go2w/control/stair_cmd_vel`, emit feedback, and publish owner `flat` before
returning success or failure.

- [ ] **Step 2: Support cancel and timeout simulation**

In the execution loop, check `goal_handle.is_cancel_requested`. If
`force_timeout` is true, keep executing long enough for the mission client
timeout path to trigger.

- [ ] **Step 3: Run build for generated interface**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control
```

Expected: build exits `0`.

## Task 4: Mission Handoff Demo And Launch

**Files:**
- Create: `go2w_mission/go2w_mission/phase4a_handoff_demo.py`
- Create: `go2w_mission/scripts/go2w_phase4a_handoff_demo`
- Create: `go2w_mission/launch/phase4a_stair_handoff.launch.py`
- Modify: `go2w_mission/CMakeLists.txt`
- Modify: `go2w_mission/package.xml`

- [ ] **Step 1: Implement one-shot demo client**

Create a mission demo that calls `/compute_route`, extracts returned edge IDs,
maps stair edge metadata through `Phase4ARouteGraph`, publishes flat command
before stair entry, sends `/stair_exec`, waits for result with a configurable
timeout, and prints stable key-value output.

- [ ] **Step 2: Add launch file**

Create a launch file that starts:

- `nav2_route` `route_server` with Phase 3C graph and params;
- `nav2_lifecycle_manager` for `route_server`;
- `go2w_control` command gate;
- `go2w_control` stair executor.

- [ ] **Step 3: Build affected packages**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
```

Expected: build exits `0`.

## Task 5: Phase 4A Verifier

**Files:**
- Create: `tools/verify_phase4a_stair_handoff.sh`

- [ ] **Step 1: Add verifier script**

Create a Bash verifier that sources ROS and repo setup, builds affected
packages when needed, launches the Phase 4A bringup, waits for route server,
waits for `/stair_exec`, runs success/failure/cancel/timeout demo modes, checks
`/cmd_vel` command gating evidence, and cleans up all child processes.

- [ ] **Step 2: Static checks**

Run:

```bash
bash -n tools/verify_phase4a_stair_handoff.sh
```

Expected: exit `0`.

- [ ] **Step 3: Runtime verifier**

Run:

```bash
./tools/verify_phase4a_stair_handoff.sh
```

Expected: `phase4a_stair_handoff_result: PASS`.

## Task 6: Documentation And State Sync

**Files:**
- Create: `docs/verification/phase4a_stair_handoff_acceptance.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `README.md`
- Modify: `docs/handoff/current_project_state.md`
- Modify: `docs/handoff/next_agent_notes.md`
- Modify: `docs/handoff/risk_cleanup_log.md`

- [ ] **Step 1: Record evidence**

Create the Phase 4A acceptance document with the verifier output and explicit
non-goals.

- [ ] **Step 2: Update state documents**

Update architecture state and handoff docs to say Phase 4A proves only
state-machine and command-ownership handoff. Do not mark real cross-floor
autonomy, real stair locomotion, AMCL, map server, elevation, or traversability
as complete.

- [ ] **Step 3: Final verification**

Run:

```bash
./tools/verify_phase4_pre_handoff.sh
bash -n tools/verify_phase4a_stair_handoff.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
colcon test --packages-select go2w_control go2w_mission go2w_navigation
colcon test-result --verbose
./tools/verify_phase4a_stair_handoff.sh
```

Expected: all commands exit `0`.

## Self-Review
- The plan covers the approved design.
- The first implementation task is test-first and catches the known graph risk.
- The Action contract remains dedicated to `stair_exec`.
- The plan does not add production mission orchestration or real stair dynamics.
- The verifier is required before any completion claim.
