# Go2W Real Model and Motion Mode Baseline Implementation Plan

> 实现已完成；当前验证与结论见 `docs/verification/go2w_real_model_motion_mode_baseline.md`。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 引入可选的真实 Go2W 模型、wheeled / legged 运动模式与启动站立基线，同时保留当前 placeholder 默认路径和既有 Phase 4 / Phase 5 验收链路。

**Architecture:** `go2w_description` 提供真实 Go2W 机器人描述资产与可切换 launch 入口；`go2w_sim` 提供独立的真实模型仿真 launch 与 controller profile，使用四个 foot wheel 的 diff-drive 配置和 leg position 控制；`go2w_control` 持有运动模式、站立姿态和 owner->mode 映射的纯数据与最小 runtime 辅助逻辑。旧的 placeholder 仍是默认路径，新的真实模型路径是 opt-in。

**Tech Stack:** ROS 2 Humble, `gz_ros2_control`, `controller_manager`, `diff_drive_controller`, `position_controllers`, `rclpy`, `std_msgs`, `pytest`, Bash headless verifier.

---

## Task Card

1. **Task Goal**  
   把真实 Go2W 模型、运动模式和初始化站立做成一个可选且可验证的基线，不破坏现有 placeholder 默认链路。

2. **Current Phase**  
   `Phase 4 accepted` 之后的独立模型/控制基线任务；这是一个新的 opt-in 子任务，不改变当前正式 active phase 标签。

3. **Allowed Files**
   - `go2w_description/urdf/go2w_real.urdf`
   - `go2w_description/urdf/go2w_placeholder.urdf`
   - `go2w_description/launch/description.launch.py`
   - `go2w_description/CMakeLists.txt`
   - `go2w_description/package.xml`
   - `go2w_description/UNITREE_MODEL_LICENSE.txt`
   - `go2w_description/config/joint_names_go2w_description.yaml`
   - `go2w_description/dae/*`
   - `go2w_description/test/test_go2w_real_model.py`
   - `go2w_control/go2w_control_runtime/command_gate.py`
   - `go2w_control/go2w_control_runtime/motion_profiles.py`
   - `go2w_control/go2w_control_runtime/stand_initializer.py`
   - `go2w_control/scripts/go2w_command_gate`
   - `go2w_control/scripts/go2w_stand_initializer`
   - `go2w_control/CMakeLists.txt`
   - `go2w_control/package.xml`
   - `go2w_control/test/test_motion_profiles.py`
   - `go2w_control/test/test_command_gate.py`
   - `go2w_sim/config/controllers_go2w_real.yaml`
   - `go2w_sim/launch/sim_go2w_real.launch.py`
   - `go2w_sim/package.xml`
   - `tools/verify_go2w_real_model_baseline.sh`
   - `tools/cleanup_sim_runtime.sh`
   - `docs/verification/go2w_real_model_motion_mode_baseline.md`
   - `docs/architecture/architecture_state.md`
   - `docs/handoff/README.md`
   - `docs/handoff/current_project_state.md`
   - `docs/handoff/next_agent_notes.md`
   - `docs/handoff/new_model_initialization_prompt.md`
   - `docs/handoff/risk_cleanup_log.md`
   - `README.md`

4. **Forbidden Files**
   - `go2w_navigation/*`
   - `go2w_perception/*`
   - `go2w_mission/*`
   - any `map_server` / AMCL / elevation / traversability files
   - any change to the perception-owned `odom -> base_link` authority contract
   - any change that turns `stair_exec` into a service
   - any change that rewires existing Phase 4 / Phase 5 verifier semantics

5. **Required Commands**
   - `python3 -m pytest go2w_description/test/test_go2w_real_model.py -q`
   - `PYTHONPATH=go2w_control python3 -m pytest go2w_control/test/test_motion_profiles.py go2w_control/test/test_command_gate.py -q`
   - `bash -n tools/cleanup_sim_runtime.sh`
   - `bash -n tools/verify_go2w_real_model_baseline.sh`
   - `git diff --check`
   - `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_description go2w_control go2w_sim`
   - `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_description go2w_control go2w_sim`
   - `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
   - `./tools/verify_go2w_real_model_baseline.sh`

6. **Definition of Done**
   - 真实 Go2W 模型资产已进入仓库并可被 launch 加载。
   - 站立姿态、wheeled / legged 运动参数已显式定义并能被测试读取。
   - `command_gate` 可观测地输出 active owner 与 active mode 的映射。
   - 真实模型专用 launch / verifier 可以在 headless 下启动并完成基础检查。
   - 旧 placeholder 默认路径保持可用，既有 Phase 4 / Phase 5 验证不被破坏。
   - 文档明确区分已验证事实、仍未覆盖的真实运动学和后续风险。

## Task 1: Add the real Go2W model assets and selectable description launch

**Files:**
- Create: `go2w_description/urdf/go2w_real.urdf`
- Create: `go2w_description/dae/*`
- Create: `go2w_description/config/joint_names_go2w_description.yaml`
- Modify: `go2w_description/launch/description.launch.py`
- Modify: `go2w_description/CMakeLists.txt`
- Modify: `go2w_description/package.xml`
- Create: `go2w_description/test/test_go2w_real_model.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import xml.etree.ElementTree as ET


def test_real_go2w_model_has_expected_joint_names():
    urdf_path = Path("go2w_description/urdf/go2w_real.urdf")
    root = ET.fromstring(urdf_path.read_text(encoding="utf-8"))
    joint_names = {
        joint.attrib["name"]
        for joint in root.findall("joint")
        if joint.attrib["name"].endswith("_joint")
    }

    assert {"FL_hip_joint", "FL_thigh_joint", "FL_calf_joint", "FL_foot_joint"} <= joint_names
    assert {"FR_hip_joint", "FR_thigh_joint", "FR_calf_joint", "FR_foot_joint"} <= joint_names
    assert {"RL_hip_joint", "RL_thigh_joint", "RL_calf_joint", "RL_foot_joint"} <= joint_names
    assert {"RR_hip_joint", "RR_thigh_joint", "RR_calf_joint", "RR_foot_joint"} <= joint_names
    assert "imu_joint" in joint_names
    assert "radar_joint" in joint_names
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m pytest go2w_description/test/test_go2w_real_model.py -q`

Expected: file or model missing failure before implementation.

- [ ] **Step 3: Implement the minimal real model path**

Add the official Go2W URDF and meshes, keep the placeholder file, and let `description.launch.py` select the file by a `model_variant` argument.

- [ ] **Step 4: Run the test and confirm it passes**

Run: `python3 -m pytest go2w_description/test/test_go2w_real_model.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add go2w_description
git commit -m "feat: add selectable real Go2W model baseline"
```

## Task 2: Add motion profiles and startup standing helpers

**Files:**
- Modify: `go2w_control/go2w_control_runtime/command_gate.py`
- Create: `go2w_control/go2w_control_runtime/motion_profiles.py`
- Create: `go2w_control/go2w_control_runtime/stand_initializer.py`
- Modify: `go2w_control/scripts/go2w_command_gate`
- Create: `go2w_control/scripts/go2w_stand_initializer`
- Modify: `go2w_control/CMakeLists.txt`
- Modify: `go2w_control/package.xml`
- Create: `go2w_control/test/test_motion_profiles.py`
- Modify: `go2w_control/test/test_command_gate.py`

- [ ] **Step 1: Write the failing test**

```python
from go2w_control_runtime.motion_profiles import get_go2w_motion_profiles


def test_go2w_motion_profiles_cover_wheeled_and_legged_modes():
    profiles = get_go2w_motion_profiles()

    assert profiles.wheeled.owner == "flat"
    assert profiles.wheeled.mode == "wheeled"
    assert profiles.legged.owner == "stair"
    assert profiles.legged.mode == "legged"
    assert profiles.legged.stand_pose[:3] == (0.0, 0.67, -1.3)
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `PYTHONPATH=go2w_control python3 -m pytest go2w_control/test/test_motion_profiles.py go2w_control/test/test_command_gate.py -q`

Expected: module or symbol missing failure before implementation.

- [ ] **Step 3: Implement the minimal motion-profile data**

Add pure dataclasses for wheeled and legged mode, with the official stand pose values and the owner->mode mapping published by `command_gate`.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `PYTHONPATH=go2w_control python3 -m pytest go2w_control/test/test_motion_profiles.py go2w_control/test/test_command_gate.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add go2w_control
git commit -m "feat: add Go2W motion profiles and stand helper"
```

## Task 3: Add the real-model sim path, verifier, and evidence

**Files:**
- Create: `go2w_sim/config/controllers_go2w_real.yaml`
- Create: `go2w_sim/launch/sim_go2w_real.launch.py`
- Modify: `go2w_sim/package.xml`
- Create: `tools/verify_go2w_real_model_baseline.sh`
- Modify: `tools/cleanup_sim_runtime.sh`
- Create: `docs/verification/go2w_real_model_motion_mode_baseline.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `docs/handoff/next_agent_notes.md`
- Modify: `docs/handoff/risk_cleanup_log.md`
- Modify: `README.md`

- [ ] **Step 1: Write the verifier**

The verifier should:
- clean up stale sim processes,
- launch the real-model sim path in headless mode,
- confirm the controller manager brings up `joint_state_broadcaster`, the wheel `diff_drive_controller`, and the leg posture controller,
- confirm the stand initializer publishes the expected stand command,
- emit stable key-value diagnostics for the evidence file.

- [ ] **Step 2: Add the evidence document**

Write `docs/verification/go2w_real_model_motion_mode_baseline.md` with:
- verified facts,
- current inference only,
- open items,
- exact commands used,
- controller names and active states.

- [ ] **Step 3: Update docs**

Record that the real Go2W model now exists as an opt-in baseline, while the placeholder path remains the default for legacy verifiers.

- [ ] **Step 4: Run the full local checks**

Run:
- `bash -n tools/cleanup_sim_runtime.sh`
- `bash -n tools/verify_go2w_real_model_baseline.sh`
- `git diff --check`
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_description go2w_control go2w_sim`
- `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_description go2w_control go2w_sim`
- `source /opt/ros/humble/setup.bash && colcon test-result --verbose`
- `./tools/verify_go2w_real_model_baseline.sh`

Expected: no formatting regressions, no package test regressions, and a fresh real-model headless evidence record.
