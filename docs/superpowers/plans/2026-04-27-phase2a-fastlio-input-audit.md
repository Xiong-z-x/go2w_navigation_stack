# Phase 2A FAST-LIO Input Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 2A FAST-LIO2 input audit evidence layer without launching FAST-LIO2 or activating `odom -> base_link`.

**Architecture:** Add one focused ROS 2 inspection tool under `tools/`, one audit document under `docs/verification/`, and minimal state/README updates. The tool observes existing simulation topics and reports whether current `/lidar_points` and `/imu` are sufficient for the next FAST-LIO2 wrapper task.

**Tech Stack:** ROS 2 Humble, `rclpy`, `sensor_msgs/msg/PointCloud2`, `sensor_msgs/msg/Imu`, Gazebo Fortress accepted baseline.

---

### Task 1: Add Phase 2A Input Inspection Tool

**Files:**
- Create: `tools/inspect_phase2_fastlio_inputs.py`

- [x] **Step 1: Create the script**

Add an executable Python script that:

- initializes `rclpy`
- subscribes to `/lidar_points` and `/imu`
- waits up to a configurable timeout
- prints a deterministic plain-text summary
- exits non-zero only when either topic is missing or required XYZ fields are absent

- [x] **Step 2: Verify syntax**

Run:

```bash
python3 -m py_compile tools/inspect_phase2_fastlio_inputs.py
```

Expected: exit code `0`.

- [x] **Step 3: Commit only after all Phase 2A tasks pass**

Do not commit this task alone unless later runtime validation is blocked.

### Task 2: Add Phase 2A Audit Documentation

**Files:**
- Create: `docs/verification/phase2_fastlio_input_audit.md`
- Modify: `README.md`
- Modify: `docs/architecture/architecture_state.md`

- [x] **Step 1: Create the initial audit document**

Document:

- Phase 2A scope
- FAST-LIO2 expected input/output contract
- required commands
- current simulation topics to inspect
- decision rule for direct wrapper vs adapter

- [x] **Step 2: Update README**

Add a short Phase 2A section pointing to the audit document and warning that
FAST-LIO2 runtime and TF authority are not yet active.

- [x] **Step 3: Update architecture state**

Record that Phase 2A input audit is the active implementation boundary and
that `odom -> base_link` remains unclaimed until FAST-LIO2 runtime validation.

### Task 3: Runtime Audit

**Files:**
- Read runtime outputs only.
- Modify `docs/verification/phase2_fastlio_input_audit.md` if the observed fields need to be recorded.

- [x] **Step 1: Clean stale runtime processes**

Run:

```bash
./tools/cleanup_sim_runtime.sh
```

Expected: exit code `0`.

- [x] **Step 2: Run default launch-chain verifier**

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

- [x] **Step 3: Start accepted simulation for topic audit**

Run:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch go2w_sim sim.launch.py use_gpu:=false headless:=true launch_rviz:=false
```

Expected: Gazebo starts with `ign gazebo-6`; controllers activate.

- [x] **Step 4: Run input audit tool in another shell**

Run:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
python3 tools/inspect_phase2_fastlio_inputs.py --timeout-sec 20
```

Expected: deterministic report for `/lidar_points` and `/imu`.

- [x] **Step 5: Record observed fields**

Update `docs/verification/phase2_fastlio_input_audit.md` with the exact field
names and the direct-wrapper vs adapter decision.

- [x] **Step 6: Stop simulation**

Run:

```bash
./tools/cleanup_sim_runtime.sh
```

Expected: no stale `go2w_sim`, Gazebo, or RViz processes remain.

### Task 4: Build And Final Verification

**Files:**
- No new files beyond previous tasks.

- [x] **Step 1: Build perception package**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception
```

Expected: `go2w_perception` builds successfully.

- [x] **Step 2: Run final default launch verifier**

Run:

```bash
./tools/verify_go2w_sim_launch.sh
```

Expected: same PASS summary as Task 3 Step 2.

- [x] **Step 3: Check formatting**

Run:

```bash
git diff --check
```

Expected: exit code `0`.

- [x] **Step 4: Commit and push**

Run:

```bash
git add tools/inspect_phase2_fastlio_inputs.py docs/verification/phase2_fastlio_input_audit.md README.md docs/architecture/architecture_state.md docs/superpowers/specs/2026-04-27-phase2a-fastlio-input-audit-design.md docs/superpowers/plans/2026-04-27-phase2a-fastlio-input-audit.md
git commit -m "docs: add phase2 fastlio input audit"
git push origin main
```

Expected: commit is pushed to `origin/main`.
