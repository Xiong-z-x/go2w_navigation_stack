# Phase 2E FAST-LIO Contract Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local `go2w_perception` contract adapter that supplies FAST-LIO with per-point timing and republishes FAST-LIO outputs using project frame IDs, without publishing TF or claiming `odom -> base_link`.

**Architecture:** Keep external FAST_LIO_ROS2 unchanged after the Phase 2C no-Livox/no-TF patch. Add repository-local Python nodes under `go2w_perception`: one input adapter for PointCloud2 timing and one output adapter for frame-contract republishing. Add a Phase 2E verifier that treats missing timing warnings, bad contract frames, forbidden TF, and runtime cleanup residue as hard failures.

**Tech Stack:** ROS 2 Humble, `ament_cmake`, `ament_cmake_python`, `rclpy`, `sensor_msgs_py.point_cloud2`, `sensor_msgs/msg/PointCloud2`, `nav_msgs/msg/Odometry`, `nav_msgs/msg/Path`, Bash verification scripts, pytest.

---

## Scope Lock

This plan implements one task only: Phase 2E FAST-LIO input/output contract stabilization.

It must not:

- publish TF;
- claim `odom -> base_link`;
- modify Gazebo world, URDF, controller YAML, or sensor declarations;
- modify Nav2, mission, or staircase files;
- vendor FAST_LIO_ROS2 source into this repository;
- expand the external FAST-LIO patch unless this plan is explicitly revised.

## 6-Item Task Card

- Task Goal: stabilize FAST-LIO input timing and output frame contracts with local `go2w_perception` adapters before TF authority activation.
- Current Phase: `Phase 2`.
- Allowed Files: `go2w_perception/CMakeLists.txt`, `go2w_perception/package.xml`, `go2w_perception/go2w_perception/*`, `go2w_perception/scripts/go2w_fastlio_input_adapter`, `go2w_perception/scripts/go2w_fastlio_output_adapter`, `go2w_perception/test/*`, `go2w_perception/config/phase2e_fastlio_contract.yaml`, `go2w_perception/launch/phase2e_fastlio_contract.launch.py`, `tools/verify_phase2e_fastlio_contract.sh`, `docs/verification/phase2_fastlio_contract_stabilization.md`, `docs/architecture/architecture_state.md`, `README.md`.
- Forbidden Files: `go2w_sim/*`, `go2w_description/*`, `go2w_control/*`, `go2w_navigation/*`, `go2w_mission/*`, `go2w_perception/patches/fast_lio_ros2/*`, vendored external FAST_LIO_ROS2 source, Nav2 files, mission orchestration files, staircase executor files.
- Required Commands: `pytest go2w_perception/test`, `colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim`, `shellcheck tools/verify_phase2e_fastlio_contract.sh`, `bash -n tools/verify_phase2e_fastlio_contract.sh`, `./tools/verify_phase2e_fastlio_contract.sh`, `./tools/verify_go2w_sim_launch.sh`, `git diff --check`.
- Definition of Done: adapted FAST-LIO input contains a float32 `time` field, Phase 2E FAST-LIO log contains zero `Failed to find match for field 'time'`, contract odometry uses `header.frame_id=odom` and `child_frame_id=base_link`, contract cloud/path topics use project frames, `/tf` contains neither `camera_init -> body` nor `odom -> base_link`, all required commands pass, docs are updated, and `main` is pushed.

## File Structure

- Create: `go2w_perception/go2w_perception/__init__.py`
- Create: `go2w_perception/go2w_perception/pointcloud_timing_adapter.py`
- Create: `go2w_perception/go2w_perception/fastlio_frame_contract_adapter.py`
- Create: `go2w_perception/scripts/go2w_fastlio_input_adapter`
- Create: `go2w_perception/scripts/go2w_fastlio_output_adapter`
- Create: `go2w_perception/test/test_pointcloud_timing_adapter.py`
- Create: `go2w_perception/test/test_fastlio_frame_contract_adapter.py`
- Create: `go2w_perception/config/phase2e_fastlio_contract.yaml`
- Create: `go2w_perception/launch/phase2e_fastlio_contract.launch.py`
- Create: `tools/verify_phase2e_fastlio_contract.sh`
- Create: `docs/verification/phase2_fastlio_contract_stabilization.md`
- Modify: `go2w_perception/CMakeLists.txt`
- Modify: `go2w_perception/package.xml`
- Modify: `README.md`
- Modify: `docs/architecture/architecture_state.md`

## Task 1: Package Wiring And Test Harness

**Files:**
- Modify: `go2w_perception/package.xml`
- Modify: `go2w_perception/CMakeLists.txt`
- Create: `go2w_perception/go2w_perception/__init__.py`

- [ ] **Step 1: Add Python/runtime dependencies to package.xml**

Use this dependency block while preserving existing package metadata:

```xml
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>ament_cmake_python</buildtool_depend>

  <exec_depend>builtin_interfaces</exec_depend>
  <exec_depend>geometry_msgs</exec_depend>
  <exec_depend>nav_msgs</exec_depend>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>sensor_msgs</exec_depend>
  <exec_depend>sensor_msgs_py</exec_depend>
  <exec_depend>std_msgs</exec_depend>

  <test_depend>ament_lint_auto</test_depend>
  <test_depend>ament_lint_common</test_depend>
  <test_depend>python3-pytest</test_depend>
```

- [ ] **Step 2: Update CMakeLists.txt for Python package, scripts, config, launch, and pytest**

Use this structure:

```cmake
cmake_minimum_required(VERSION 3.8)
project(go2w_perception)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/go2w_fastlio_input_adapter
  scripts/go2w_fastlio_output_adapter
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
```

- [ ] **Step 3: Create Python package marker**

Create `go2w_perception/go2w_perception/__init__.py`:

```python
"""Go2W perception contract adapters."""
```

- [ ] **Step 4: Run package build to catch wiring errors**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception
```

Expected:

```text
Summary: 1 package finished
```

## Task 2: PointCloud2 Timing Adapter

**Files:**
- Create: `go2w_perception/go2w_perception/pointcloud_timing_adapter.py`
- Create: `go2w_perception/test/test_pointcloud_timing_adapter.py`
- Create: `go2w_perception/scripts/go2w_fastlio_input_adapter`

- [ ] **Step 1: Write tests for deterministic per-point timing**

Create `go2w_perception/test/test_pointcloud_timing_adapter.py` with tests that cover:

```python
def test_compute_relative_times_three_points():
    from go2w_perception.pointcloud_timing_adapter import compute_relative_times

    assert compute_relative_times(3, 0.1) == [0.0, 0.05, 0.1]


def test_compute_relative_times_single_point():
    from go2w_perception.pointcloud_timing_adapter import compute_relative_times

    assert compute_relative_times(1, 0.1) == [0.0]


def test_compute_relative_times_rejects_negative_scan_period():
    from go2w_perception.pointcloud_timing_adapter import compute_relative_times

    try:
        compute_relative_times(3, -0.1)
    except ValueError as exc:
        assert "scan_period_sec must be positive" in str(exc)
    else:
        raise AssertionError("negative scan period was accepted")
```

- [ ] **Step 2: Run tests and verify they fail before implementation**

Run:

```bash
pytest go2w_perception/test/test_pointcloud_timing_adapter.py -q
```

Expected before implementation:

```text
ModuleNotFoundError
```

- [ ] **Step 3: Implement pure timing helpers**

`go2w_perception/go2w_perception/pointcloud_timing_adapter.py` must expose:

```python
from __future__ import annotations


def compute_relative_times(point_count: int, scan_period_sec: float) -> list[float]:
    if point_count < 0:
        raise ValueError("point_count must be non-negative")
    if scan_period_sec <= 0.0:
        raise ValueError("scan_period_sec must be positive")
    if point_count == 0:
        return []
    if point_count == 1:
        return [0.0]
    step = scan_period_sec / float(point_count - 1)
    return [float(index) * step for index in range(point_count)]
```

- [ ] **Step 4: Implement ROS adapter node behavior**

The node must:

- parameterize `input_topic`, `output_topic`, `scan_period_sec`, `time_field_name`, and `force_recompute_time`;
- subscribe to `/lidar_points` by default;
- publish `/fastlio/input/lidar_points` by default;
- require `x`, `y`, `z`, `intensity`, and `ring`;
- add or replace float32 `time`;
- preserve `header`, `height`, `width`, `is_dense`, and point order;
- fail closed by logging an error and not publishing when required fields are missing.

Use `sensor_msgs_py.point_cloud2.read_points` and `create_cloud` for the first implementation. Performance optimization is out of scope for Phase 2E.

- [ ] **Step 5: Add executable wrapper**

If using installed scripts, create `go2w_perception/scripts/go2w_fastlio_input_adapter`:

```python
#!/usr/bin/env python3
from go2w_perception.pointcloud_timing_adapter import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests and build**

Run:

```bash
pytest go2w_perception/test/test_pointcloud_timing_adapter.py -q
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception
```

Expected:

```text
pytest: all tests passed
colcon: Summary: 1 package finished
```

## Task 3: FAST-LIO Output Frame Contract Adapter

**Files:**
- Create: `go2w_perception/go2w_perception/fastlio_frame_contract_adapter.py`
- Create: `go2w_perception/test/test_fastlio_frame_contract_adapter.py`
- Create: `go2w_perception/scripts/go2w_fastlio_output_adapter`

- [ ] **Step 1: Write tests for frame conversion helpers**

Create tests:

```python
def test_contract_odometry_frames_are_rewritten():
    from nav_msgs.msg import Odometry
    from go2w_perception.fastlio_frame_contract_adapter import rewrite_odometry_frames

    msg = Odometry()
    msg.header.frame_id = "camera_init"
    msg.child_frame_id = "body"

    rewritten = rewrite_odometry_frames(msg, "camera_init", "body", "odom", "base_link")

    assert rewritten.header.frame_id == "odom"
    assert rewritten.child_frame_id == "base_link"


def test_unexpected_raw_odometry_frame_is_rejected():
    from nav_msgs.msg import Odometry
    from go2w_perception.fastlio_frame_contract_adapter import rewrite_odometry_frames

    msg = Odometry()
    msg.header.frame_id = "map"
    msg.child_frame_id = "body"

    try:
        rewrite_odometry_frames(msg, "camera_init", "body", "odom", "base_link")
    except ValueError as exc:
        assert "unexpected odometry frame" in str(exc)
    else:
        raise AssertionError("unexpected raw frame was accepted")
```

- [ ] **Step 2: Run tests and verify they fail before implementation**

Run:

```bash
pytest go2w_perception/test/test_fastlio_frame_contract_adapter.py -q
```

Expected before implementation:

```text
ModuleNotFoundError
```

- [ ] **Step 3: Implement frame rewrite helpers**

`fastlio_frame_contract_adapter.py` must expose pure helpers:

```python
from __future__ import annotations

import copy

from nav_msgs.msg import Odometry, Path
from sensor_msgs.msg import PointCloud2


def rewrite_odometry_frames(
    msg: Odometry,
    raw_world_frame: str,
    raw_body_frame: str,
    target_world_frame: str,
    target_body_frame: str,
) -> Odometry:
    if msg.header.frame_id != raw_world_frame or msg.child_frame_id != raw_body_frame:
        raise ValueError(
            f"unexpected odometry frame: {msg.header.frame_id}->{msg.child_frame_id}"
        )
    out = copy.deepcopy(msg)
    out.header.frame_id = target_world_frame
    out.child_frame_id = target_body_frame
    return out


def rewrite_path_frame(msg: Path, raw_world_frame: str, target_world_frame: str) -> Path:
    if msg.header.frame_id != raw_world_frame:
        raise ValueError(f"unexpected path frame: {msg.header.frame_id}")
    out = copy.deepcopy(msg)
    out.header.frame_id = target_world_frame
    for pose in out.poses:
        if pose.header.frame_id == raw_world_frame:
            pose.header.frame_id = target_world_frame
    return out


def rewrite_cloud_frame(msg: PointCloud2, target_frame: str) -> PointCloud2:
    out = copy.deepcopy(msg)
    out.header.frame_id = target_frame
    return out
```

- [ ] **Step 4: Implement ROS adapter node behavior**

The node must:

- subscribe to raw FAST-LIO `/Odometry`, `/path`, `/cloud_registered`, `/cloud_registered_body`, and `/Laser_map`;
- publish `/go2w/perception/odom`, `/go2w/perception/path`, `/go2w/perception/cloud_registered`, `/go2w/perception/cloud_body`, and `/go2w/perception/laser_map`;
- rewrite raw `camera_init/body` to contract `odom/base_link`;
- fail closed on unexpected odometry/path raw frames;
- not create a `tf2_ros.TransformBroadcaster`;
- not publish `/tf`.

- [ ] **Step 5: Add executable wrapper**

If using installed scripts, create `go2w_perception/scripts/go2w_fastlio_output_adapter`:

```python
#!/usr/bin/env python3
from go2w_perception.fastlio_frame_contract_adapter import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests and build**

Run:

```bash
pytest go2w_perception/test/test_fastlio_frame_contract_adapter.py -q
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception
```

Expected:

```text
pytest: all tests passed
colcon: Summary: 1 package finished
```

## Task 4: Launch And Configuration

**Files:**
- Create: `go2w_perception/config/phase2e_fastlio_contract.yaml`
- Create: `go2w_perception/launch/phase2e_fastlio_contract.launch.py`

- [ ] **Step 1: Add adapter config**

Create `go2w_perception/config/phase2e_fastlio_contract.yaml`:

```yaml
go2w_fastlio_input_adapter:
  ros__parameters:
    use_sim_time: true
    input_topic: /lidar_points
    output_topic: /fastlio/input/lidar_points
    scan_period_sec: 0.1
    time_field_name: time
    force_recompute_time: true

go2w_fastlio_output_adapter:
  ros__parameters:
    use_sim_time: true
    raw_world_frame: camera_init
    raw_body_frame: body
    target_world_frame: odom
    target_body_frame: base_link
    raw_odometry_topic: /Odometry
    raw_path_topic: /path
    raw_cloud_registered_topic: /cloud_registered
    raw_cloud_body_topic: /cloud_registered_body
    raw_laser_map_topic: /Laser_map
    contract_odometry_topic: /go2w/perception/odom
    contract_path_topic: /go2w/perception/path
    contract_cloud_registered_topic: /go2w/perception/cloud_registered
    contract_cloud_body_topic: /go2w/perception/cloud_body
    contract_laser_map_topic: /go2w/perception/laser_map
```

- [ ] **Step 2: Add launch file**

Create `go2w_perception/launch/phase2e_fastlio_contract.launch.py` with two nodes:

```python
from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    config = PathJoinSubstitution([
        FindPackageShare("go2w_perception"),
        "config",
        "phase2e_fastlio_contract.yaml",
    ])

    return LaunchDescription([
        Node(
            package="go2w_perception",
            executable="go2w_fastlio_input_adapter",
            name="go2w_fastlio_input_adapter",
            output="screen",
            parameters=[config],
        ),
        Node(
            package="go2w_perception",
            executable="go2w_fastlio_output_adapter",
            name="go2w_fastlio_output_adapter",
            output="screen",
            parameters=[config],
        ),
    ])
```

- [ ] **Step 3: Build and smoke-test launch discovery**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception
source install/setup.bash
ros2 launch go2w_perception phase2e_fastlio_contract.launch.py --show-args
```

Expected:

```text
Arguments (pass arguments as '<name>:=<value>'):
```

If no launch arguments are declared, an empty arguments list is acceptable.

## Task 5: Phase 2E Runtime Verifier

**Files:**
- Create: `tools/verify_phase2e_fastlio_contract.sh`
- Create: `docs/verification/phase2_fastlio_contract_stabilization.md`

- [ ] **Step 1: Create verification script with bounded cleanup**

The script must follow the Phase 2D verifier pattern and include:

```bash
#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FASTLIO_WS="${GO2W_FASTLIO_WS:-/tmp/go2w_phase2d_fastlio_ws}"
EVIDENCE_DIR="${GO2W_PHASE2E_EVIDENCE_DIR:-/tmp/go2w_phase2e_fastlio_contract_${$}}"

# Source ROS setup before enabling nounset.
source /opt/ros/humble/setup.bash
source "${REPO_ROOT}/install/setup.bash"
source "${FASTLIO_WS}/install/setup.bash"
set -u
```

Use bounded cleanup with `INT`, short wait, `TERM`, then `KILL`. Do not use an unbounded `wait`.

- [ ] **Step 2: Orchestrate runtime**

The verifier must:

1. run `tools/prepare_phase2d_fastlio_external.sh`;
2. run `tools/cleanup_sim_runtime.sh`;
3. export isolated `ROS_DOMAIN_ID` and `GZ_PARTITION`;
4. launch `go2w_sim sim.launch.py use_gpu:=false headless:=true launch_rviz:=false`;
5. launch `go2w_perception phase2e_fastlio_contract.launch.py`;
6. launch `fast_lio fastlio_mapping` with `common.lid_topic=/fastlio/input/lidar_points`, `common.imu_topic=/imu`, `publish.tf_publish_en=false`;
7. sample required input, adapted input, raw FAST-LIO output, and contract output topics;
8. sample `/tf` and `/tf_static`;
9. write all logs under `${EVIDENCE_DIR}`.

- [ ] **Step 3: Add hard assertions**

The verifier must exit non-zero if any assertion fails:

```text
adapted_pointcloud_time_field: PASS
fastlio_missing_time_warning_count: 0
contract_odometry_frame: odom
contract_odometry_child_frame: base_link
contract_cloud_registered_frame: odom
contract_cloud_body_frame: base_link
contract_laser_map_frame: odom
fastlio_tf_camera_init_body: ABSENT
odom_base_link_authority: ABSENT
phase2e_result: PASS
```

Do not accept a partial result for Phase 2E. This task exists to remove the
Phase 2D warnings, not to document them again.

- [ ] **Step 4: Add document skeleton**

Create `docs/verification/phase2_fastlio_contract_stabilization.md` with sections:

```markdown
# Phase 2E FAST-LIO Contract Stabilization

## Purpose

## Phase Boundary

## Automation

## Observed Result

## Current Decision
```

During implementation, fill `Observed Result` with exact command output from the successful verifier.

- [ ] **Step 5: Run static checks**

Run:

```bash
bash -n tools/verify_phase2e_fastlio_contract.sh
shellcheck tools/verify_phase2e_fastlio_contract.sh
```

Expected:

```text
no output
```

## Task 6: Full Validation, Docs, Commit, Push

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `docs/verification/phase2_fastlio_contract_stabilization.md`

- [ ] **Step 1: Run unit tests**

Run:

```bash
pytest go2w_perception/test -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 2: Run scoped build**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim
```

Expected:

```text
Summary: 3 packages finished
```

- [ ] **Step 3: Run Phase 2E verifier**

Run:

```bash
./tools/verify_phase2e_fastlio_contract.sh
```

Expected required lines:

```text
adapted_pointcloud_time_field: PASS
fastlio_missing_time_warning_count: 0
contract_odometry_frame: odom
contract_odometry_child_frame: base_link
fastlio_tf_camera_init_body: ABSENT
odom_base_link_authority: ABSENT
phase2e_result: PASS
```

- [ ] **Step 4: Run Phase 1 baseline regression**

Run:

```bash
./tools/verify_go2w_sim_launch.sh
```

Expected:

```text
gazebo_runtime: ign gazebo-6
joint_state_broadcaster: active
diff_drive_controller: active
clock_message: PASS
imu_message: PASS
lidar_points_message: PASS
```

- [ ] **Step 5: Update state docs**

Update `docs/architecture/architecture_state.md`:

- mark Phase 2E contract stabilization complete only after verifier PASS;
- state that `odom -> base_link` remains unclaimed;
- set the next boundary to a later dedicated TF authority activation task, not Nav2.

Update `README.md`:

- add the Phase 2E verifier command;
- summarize the adapter topic contract;
- state that no TF is published yet.

- [ ] **Step 6: Final checks**

Run:

```bash
git diff --check
git status --short --branch
```

Expected:

```text
git diff --check: no output
git status: only intended Phase 2E files changed before commit
```

- [ ] **Step 7: Commit and push**

Run:

```bash
git add go2w_perception tools/verify_phase2e_fastlio_contract.sh docs/verification/phase2_fastlio_contract_stabilization.md docs/architecture/architecture_state.md README.md
git commit -m "feat: stabilize phase2e fastlio contract"
git push origin main
git status --short --branch
```

Expected:

```text
HEAD -> main, origin/main
working tree clean
```

## Self-Review

- Spec coverage: the plan covers timing input, frame-contract output, no-TF verification, docs, regression, commit, and push.
- Ambiguity scan: executable wrappers, topic names, frame names, and verification result keys are fixed.
- Type consistency: topic names and frame names match across config, launch, verifier, and docs.
- Boundary check: no Nav2, mission, stairs, Gazebo model, controller, or external FAST-LIO patch edits are included.
