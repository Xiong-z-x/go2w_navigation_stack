# Phase 2C FAST-LIO2 Patch Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:executing-plans to implement this plan task-by-task. The project
> owner has approved direct-to-main work for this repository; do not create a
> separate feature branch or git worktree unless explicitly instructed.

**Goal:** Establish a reproducible external FAST_LIO_ROS2 patch gate that
removes the immediate Livox build blocker and disables FAST-LIO TF publication
by default, without launching FAST-LIO2 runtime.

**Architecture:** Keep external FAST_LIO_ROS2 source in `/tmp`. Commit only
patch files, audit tooling, verification records, and state documentation.

**Tech Stack:** ROS 2 Humble, external `Ericsii/FAST_LIO_ROS2` ROS 2 branch,
Gazebo Fortress accepted baseline.

---

### Task 1: Record Design And Plan

**Files:**
- Create:
  `docs/superpowers/specs/2026-04-28-phase2c-fastlio-patch-gate-design.md`
- Create:
  `docs/superpowers/plans/2026-04-28-phase2c-fastlio-patch-gate.md`

- [x] **Step 1: Write the design**

Capture Phase 2C boundary, patch scope, no-TF gate, and out-of-scope items.

- [x] **Step 2: Write this implementation plan**

Keep all tasks focused on external patch/build evidence.

### Task 2: Add External Patch And Patch Tool

**Files:**
- Create: `go2w_perception/patches/fast_lio_ros2/phase2c_no_livox_no_tf.patch`
- Create: `tools/apply_phase2c_fastlio_patch.sh`
- Modify: `tools/check_phase2_fastlio_external.sh`

- [x] **Step 1: Add patch file**

The patch must make Livox support optional and add a default-disabled FAST-LIO
TF publication parameter.

- [x] **Step 2: Add patch apply tool**

The tool must apply the patch to an external FAST_LIO_ROS2 checkout and avoid
hardcoded user absolute paths.

- [x] **Step 3: Enhance external audit**

The audit tool must distinguish hard-coded TF from parameter-gated TF and must
report optional Livox build support.

### Task 3: Apply Patch And Build In Scratch Workspace

**Files:**
- Create or modify: `docs/verification/phase2_fastlio_patch_gate.md`

- [x] **Step 1: Acquire external source**

Use `/tmp/fast_lio_ros2_probe`. Git clone is preferred; GitHub branch archive is
allowed if clone stalls.

- [x] **Step 2: Apply patch**

Run:

```bash
tools/apply_phase2c_fastlio_patch.sh /tmp/fast_lio_ros2_probe
```

- [x] **Step 3: Audit patched source**

Run:

```bash
tools/check_phase2_fastlio_external.sh /tmp/fast_lio_ros2_probe
```

- [x] **Step 4: Attempt isolated build**

Run:

```bash
rm -rf /tmp/go2w_phase2c_fastlio_ws
mkdir -p /tmp/go2w_phase2c_fastlio_ws/src
ln -s /tmp/fast_lio_ros2_probe /tmp/go2w_phase2c_fastlio_ws/src/FAST_LIO_ROS2
source /opt/ros/humble/setup.bash
cd /tmp/go2w_phase2c_fastlio_ws
colcon build --symlink-install --packages-select fast_lio --cmake-args -DFAST_LIO_ENABLE_LIVOX=OFF
```

Expected: build succeeds or fails with a recorded concrete blocker.

### Task 4: Record Evidence And State

**Files:**
- Modify: `docs/verification/phase2_fastlio_patch_gate.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `README.md`

- [x] **Step 1: Record patch and build evidence**

Record source acquisition method, patch apply result, audit output, build
result, and no-TF status.

- [x] **Step 2: Update architecture state**

Record whether Phase 2C cleared the build/no-TF gate or what blocker remains.

- [x] **Step 3: Update README**

Point operators to the Phase 2C verification record and keep FAST-LIO2 runtime
marked inactive.

### Task 5: Final Verification And Commit

**Files:**
- All Phase 2C files above.

- [x] **Step 1: Build affected package**

Run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception
```

- [x] **Step 2: Verify accepted simulation baseline**

Run:

```bash
./tools/verify_go2w_sim_launch.sh
```

- [x] **Step 3: Check whitespace**

Run:

```bash
git diff --check
```

- [ ] **Step 4: Commit and push**

Run:

```bash
git add README.md docs/architecture/architecture_state.md docs/verification/phase2_fastlio_patch_gate.md docs/superpowers/specs/2026-04-28-phase2c-fastlio-patch-gate-design.md docs/superpowers/plans/2026-04-28-phase2c-fastlio-patch-gate.md go2w_perception/patches/fast_lio_ros2/phase2c_no_livox_no_tf.patch tools/apply_phase2c_fastlio_patch.sh tools/check_phase2_fastlio_external.sh
git commit -m "docs: add phase2 fastlio patch gate"
git push origin main
```
