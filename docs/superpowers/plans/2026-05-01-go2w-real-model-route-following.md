# Go2W Real Model Route Following Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in runtime verifier proving the real Go2W model can complete a short same-floor Nav2 `NavigateToPose` goal through `/cmd_vel` and produce diagnosable real-model motion feedback.

**Architecture:** Keep the existing Phase 3A placeholder verifier unchanged. Add a separate shell verifier that launches `sim_go2w_real.launch.py`, starts the existing perception and Nav2 same-floor stack, sends one conservative `odom`-frame goal, and checks controller state, TF authority, `/cmd_vel`, `/diff_drive_controller/odom`, and `/go2w/perception/odom`. Record the result as post-Phase-4 hardening evidence without changing the formal Phase 4 accepted label.

**Tech Stack:** ROS 2 Humble, Gazebo Fortress / `ign gazebo-6`, `ros_gz_sim`, `gz_ros2_control`, Nav2, FAST-LIO external workspace, Bash verifier, Python `rclpy` action client embedded in the verifier.

---

## File Structure

- Create `tools/verify_go2w_real_model_route_following.sh`: self-contained runtime acceptance script. It owns cleanup, temporary evidence directory, FAST-LIO params, embedded Nav2 goal client, real-model launch, checks, and result keys.
- Create `docs/verification/go2w_real_model_route_following.md`: evidence record for the runtime verifier.
- Modify `docs/architecture/architecture_state.md`: add the verified post-Phase-4 hardening state only after runtime evidence passes.
- Modify `docs/handoff/current_project_state.md`: record the new verified fact and remaining limitations.
- Modify `docs/handoff/next_agent_notes.md`: update next-agent guidance and avoid overstating real-model route-following as stair dynamics.
- Modify `docs/handoff/risk_cleanup_log.md`: mark the real-model route-following risk as mitigated when verifier passes.
- Modify `README.md`: add the operator-facing command summary.

## Task 1: Add the Runtime Verifier Script

**Files:**
- Create: `tools/verify_go2w_real_model_route_following.sh`

- [ ] **Step 1: Create script skeleton with strict cleanup**

Use `apply_patch` to add a Bash script that defines repo paths before `set -u`, then enables `set -u` after helper setup. Include PID cleanup for sim, perception, FAST-LIO, and Nav2.

```bash
#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_CACHE_ROOT="${GO2W_FASTLIO_CACHE_ROOT:-${REPO_ROOT}/.go2w_external}"
FASTLIO_WS="${GO2W_FASTLIO_WS:-${FASTLIO_CACHE_ROOT}/workspaces/fast_lio_ros2}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
FASTLIO_SETUP="${FASTLIO_WS}/install/setup.bash"
EVIDENCE_DIR="${GO2W_REAL_ROUTE_EVIDENCE_DIR:-/tmp/go2w_real_model_route_following_${$}}"
PHASE3A_WORLD="${GO2W_REAL_ROUTE_WORLD:-${REPO_ROOT}/install/go2w_sim/share/go2w_sim/worlds/phase3a_feature_world.sdf}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 90) + 130 ))}"
PARTITION="go2w_real_route_${$}"
REBUILD_REPO="${GO2W_REAL_ROUTE_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_REAL_ROUTE_CLEAN_EVIDENCE:-0}"
NAV_TIMEOUT_SECONDS="${GO2W_REAL_ROUTE_NAV_TIMEOUT_SECONDS:-120}"
NAV_GOAL_OFFSET_X="${GO2W_REAL_ROUTE_GOAL_OFFSET_X:-0.04}"
NAV_GOAL_OFFSET_Y="${GO2W_REAL_ROUTE_GOAL_OFFSET_Y:-0.00}"
NAV_GOAL_YAW_OFFSET="${GO2W_REAL_ROUTE_GOAL_YAW_OFFSET:-0.0}"
MIN_PERCEPTION_ODOM_DELTA="${GO2W_REAL_ROUTE_MIN_PERCEPTION_ODOM_DELTA:-0.003}"
MIN_DIFF_DRIVE_ODOM_DELTA="${GO2W_REAL_ROUTE_MIN_DIFF_DRIVE_ODOM_DELTA:-0.003}"
SIM_PID=""
PERCEPTION_PID=""
FASTLIO_PID=""
NAV2_PID=""

set -u
```

- [ ] **Step 2: Add reusable check helpers**

Add helpers equivalent to Phase 3A verifier: `print_kv`, `source_file_checked`, `terminate_pid`, `cleanup`, `maybe_build_repo`, `wait_for_log`, `require_topic_once`, `require_field_once`, lifecycle checks, controller checks, topic checks, TF edge checks, forbidden-node checks, and log exception checks. Keep helper behavior fail-fast and print relevant log snippets.

- [ ] **Step 3: Add FAST-LIO parameter writer**

Embed a `write_fastlio_params` function that writes `${EVIDENCE_DIR}/real_route_fastlio.yaml` with:

```yaml
laser_mapping:
  ros__parameters:
    use_sim_time: true
    common.lid_topic: /fastlio/input/lidar_points
    common.imu_topic: /imu
    common.time_sync_en: false
    common.time_offset_lidar_to_imu: 0.0
    preprocess.lidar_type: 2
    preprocess.scan_line: 16
    preprocess.scan_rate: 10
    preprocess.timestamp_unit: 2
    preprocess.blind: 0.1
    preprocess.point_filter_num: 1
    preprocess.feature_extract_enable: false
    mapping.acc_cov: 0.1
    mapping.gyr_cov: 0.1
    mapping.b_acc_cov: 0.0001
    mapping.b_gyr_cov: 0.0001
    mapping.fov_degree: 180.0
    mapping.det_range: 100.0
    mapping.extrinsic_est_en: true
    mapping.extrinsic_T: [0.0, 0.0, 0.0]
    mapping.extrinsic_R: [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    publish.path_en: true
    publish.scan_publish_en: true
    publish.dense_publish_en: true
    publish.scan_bodyframe_pub_en: true
    publish.map_en: true
    publish.effect_map_en: false
    publish.tf_publish_en: false
    pcd_save.pcd_save_en: false
    pcd_save.interval: -1
```

- [ ] **Step 4: Add embedded Nav2 goal client**

Write `${EVIDENCE_DIR}/real_route_goal_client.py` from the verifier. The client must:

- subscribe to `/go2w/perception/odom`
- subscribe to `/diff_drive_controller/odom`
- subscribe to `/cmd_vel`
- send a short `NavigateToPose` goal in `odom`
- print stable keys:
  - `real_route_goal_status`
  - `real_route_cmd_vel_nonzero_count`
  - `real_route_perception_odom_delta_xy`
  - `real_route_diff_drive_odom_delta_xy`
  - `real_route_goal_result`

The pass condition is:

```python
result.status == GoalStatus.STATUS_SUCCEEDED
self._cmd_vel_count >= 2
perception_delta_xy >= min_perception_delta
diff_drive_delta_xy >= min_diff_drive_delta
```

- [ ] **Step 5: Add launch and validation sequence**

The script sequence must be:

```bash
"${REPO_ROOT}/tools/prepare_phase2d_fastlio_external.sh"
maybe_build_repo
source_file_checked "${ROS_SETUP}" "ros_setup"
source_file_checked "${REPO_SETUP}" "repo_setup"
source_file_checked "${FASTLIO_SETUP}" "fastlio_setup"
"${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true
export ROS_DOMAIN_ID="${DOMAIN_ID}"
export GZ_PARTITION="${PARTITION}"
write_fastlio_params
write_nav_goal_client
ros2 launch go2w_sim sim_go2w_real.launch.py use_gpu:=false headless:=true launch_rviz:=false world:="${PHASE3A_WORLD}" world_name:=go2w_phase3a_feature_world >"${EVIDENCE_DIR}/sim.log" 2>&1 &
```

Then check real-model launch, controllers, stand initializer, `/clock`, `/imu`, `/lidar_points`, no pre-activation `odom -> base_link`, perception adapter, FAST-LIO, Nav2 lifecycle, goal result, forbidden nodes, logs, and post-Nav2 TF authority.

- [ ] **Step 6: Add final result keys**

The script must end with:

```bash
print_kv "sim_log" "${EVIDENCE_DIR}/sim.log"
print_kv "perception_log" "${EVIDENCE_DIR}/perception.log"
print_kv "fastlio_log" "${EVIDENCE_DIR}/fastlio.log"
print_kv "nav2_log" "${EVIDENCE_DIR}/nav2.log"
print_kv "nav_goal_log" "${EVIDENCE_DIR}/nav_goal.txt"
print_kv "go2w_real_model_route_following_result" "PASS"
```

- [ ] **Step 7: Run static syntax check**

Run:

```bash
bash -n tools/verify_go2w_real_model_route_following.sh
```

Expected: exit code `0`.

## Task 2: Execute Focused Runtime Verification and Fix Only Root Causes

**Files:**
- Modify only files allowed by the design if a real failure exposes a root cause.

- [ ] **Step 1: Run the verifier**

Run:

```bash
./tools/verify_go2w_real_model_route_following.sh
```

Expected key:

```text
go2w_real_model_route_following_result: PASS
```

- [ ] **Step 2: If the verifier fails, classify the failure**

Classify the first failure into one of:

- environment / dependency
- build
- launch
- controller activation
- sensor topic
- perception adapter
- FAST-LIO runtime
- TF authority
- Nav2 lifecycle
- action goal
- odometry / movement threshold

Record the evidence directory and first failing key before changing files.

- [ ] **Step 3: Apply the smallest correction**

Allowed corrections:

- controller activation timeout or real-model launch order in `go2w_sim/launch/sim_go2w_real.launch.py`
- conservative controller parameters in `go2w_sim/config/controllers_go2w_real.yaml`
- conservative verifier thresholds or goal offset in `tools/verify_go2w_real_model_route_following.sh`
- cleanup coverage in `tools/cleanup_sim_runtime.sh`

Forbidden corrections:

- disabling motion checks
- enabling `diff_drive_controller.enable_odom_tf`
- adding `map -> odom`
- switching default launch to real model
- changing perception TF ownership

- [ ] **Step 4: Re-run the failed command**

Run the exact failed verifier command again after each correction.

Expected: either the next diagnosable failure key or final `PASS`.

## Task 3: Add Verification Evidence Document

**Files:**
- Create: `docs/verification/go2w_real_model_route_following.md`

- [ ] **Step 1: Write evidence doc after verifier passes**

Use this structure:

```markdown
# Go2W Real Model Route Following Verification

## Scope
This document records the opt-in real Go2W model same-floor Nav2 route-following gate.

This is not production Mission Orchestrator, real stair locomotion, real cross-floor autonomy, map-frame localization, elevation mapping, traversability, or hardware Unitree SDK2 integration.

## Verification Run
- Date: `YYYY-MM-DDTHH:MM+08:00`
- Command: `./tools/verify_go2w_real_model_route_following.sh`
- Evidence directory: `/tmp/go2w_real_model_route_following_<pid>`
- Result: `go2w_real_model_route_following_result: PASS`

## Verified Facts
- The opt-in real model launch starts headless under the Fortress-only path.
- The real model controllers are active.
- Startup stand initialization completed.
- Sensor topics publish.
- `diff_drive_controller.enable_odom_tf` remains `False`.
- `go2w_perception` owns `odom -> base_link`.
- Nav2 same-floor lifecycle nodes reach `active`.
- A short `NavigateToPose` goal succeeds.
- `/cmd_vel` publishes non-zero commands during the goal.
- `/diff_drive_controller/odom` and `/go2w/perception/odom` report movement over the configured thresholds.
- Forbidden nodes and `map -> odom` are absent.

## Result Keys
```text
go2w_real_model_route_following_result: PASS
```

## Open Validation Items
- The real model remains opt-in.
- This does not verify real stair dynamics.
- This does not make the placeholder path obsolete.
- Odometry scale still needs longer-path validation.
```

## Task 4: Update Architecture and Handoff Docs

**Files:**
- Modify: `docs/architecture/architecture_state.md`
- Modify: `docs/handoff/current_project_state.md`
- Modify: `docs/handoff/next_agent_notes.md`
- Modify: `docs/handoff/risk_cleanup_log.md`
- Modify: `README.md`

- [ ] **Step 1: Update architecture state**

Add a post-Phase-4 hardening bullet stating the verified real-model same-floor route-following gate. Keep formal phase as `Phase 4 accepted`.

- [ ] **Step 2: Update current project state**

Move “real model route tracking not verified” from current gap to verified post-Phase-4 hardening fact, while keeping stair dynamics and default model switch as open items.

- [ ] **Step 3: Update next-agent notes**

Add guidance: next work can move to longer real-model route-following, odometry-scale calibration, or stair dynamics, but must not treat this gate as stair locomotion proof.

- [ ] **Step 4: Update risk cleanup log**

Add or update a row for real-model route-following:

```markdown
| 真实 Go2W 模型尚未验证 Nav2 同层运动闭环 | real-model baseline 只验证 launch/controller/sensors/stand，没有验证 `/navigate_to_pose` 到真实模型运动反馈 | 新增 `tools/verify_go2w_real_model_route_following.sh`，验证 real-model headless launch、Nav2 lifecycle、`/cmd_vel`、`/diff_drive_controller/odom`、`/go2w/perception/odom`、TF authority 和 forbidden-node absence | 已修复 |
```

- [ ] **Step 5: Update README**

Add the command:

```bash
./tools/verify_go2w_real_model_route_following.sh
```

State that it is opt-in and does not replace `sim.launch.py`.

## Task 5: Run Required Checks

**Files:**
- No new file changes unless a check exposes a real issue.

- [ ] **Step 1: Static checks**

Run:

```bash
bash -n tools/verify_go2w_real_model_route_following.sh
git diff --check
```

Expected: both pass.

- [ ] **Step 2: Build relevant packages**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_description go2w_sim go2w_control go2w_perception go2w_navigation
```

Expected: all selected packages finish.

- [ ] **Step 3: Test relevant packages**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon test --packages-select go2w_description go2w_sim go2w_control go2w_perception go2w_navigation
colcon test-result --verbose
```

Expected: `0 errors, 0 failures`.

- [ ] **Step 4: Runtime verifier**

Run:

```bash
./tools/verify_go2w_real_model_route_following.sh
```

Expected: `go2w_real_model_route_following_result: PASS`.

- [ ] **Step 5: Legacy default launch guard if touched**

If any real-model launch or cleanup logic changed after the previous accepted baseline, run:

```bash
./tools/verify_go2w_sim_launch.sh
```

Expected: legacy placeholder path still passes.

## Self-Review

- Spec coverage: The plan covers the independent verifier, runtime evidence, TF authority, controller state, Nav2 goal, motion feedback, docs, and required commands from the approved spec.
- Placeholder scan: No placeholder implementation steps are left; the only variable values in docs are evidence timestamp and evidence directory to be filled from the actual run.
- Scope check: The plan is a single post-Phase-4 hardening task. It explicitly excludes stair dynamics, default-model switch, AMCL, map-frame localization, elevation, traversability, and hardware SDK2.
