# Phase 2B FAST-LIO2 External Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:executing-plans to implement this plan task-by-task. The project
> owner has approved direct-to-main work for this repository; do not create a
> separate feature branch unless explicitly instructed.

**Goal:** Establish the FAST-LIO2 external dependency build path and no-TF
dry-run gate without activating `odom -> base_link`.

**Architecture:** Keep FAST-LIO2 source outside this repository. Commit only
audit tooling, verification evidence, and state/README updates.

**Tech Stack:** ROS 2 Humble, external FAST_LIO_ROS2 ROS 2 branch, Gazebo
Fortress accepted baseline.

---

### Task 1: Record Phase 2B Design And Plan

**Files:**
- Create:
  `docs/superpowers/specs/2026-04-27-phase2b-fastlio-dryrun-design.md`
- Create:
  `docs/superpowers/plans/2026-04-27-phase2b-fastlio-dryrun.md`

- [x] **Step 1: Write the design**

Capture the approved Phase 2B boundary, external-source policy, no-TF dry-run
gate, and decision rules.

- [x] **Step 2: Write this implementation plan**

Keep tasks scoped to audit/build evidence and state synchronization.

### Task 2: Add External FAST-LIO2 Audit Tool

**Files:**
- Create: `tools/check_phase2_fastlio_external.sh`

- [x] **Step 1: Create the script**

The script must inspect an external FAST_LIO_ROS2 checkout, print package and
source facts, and check current ROS package availability.

- [x] **Step 2: Verify the script can run**

Run:

```bash
tools/check_phase2_fastlio_external.sh /tmp/fast_lio_ros2_probe
```

Expected: deterministic audit output. Missing external build dependencies are
reported as evidence, not hidden.

### Task 3: Clone And Build-Check External FAST-LIO2

**Files:**
- Modify: `docs/verification/phase2_fastlio_dryrun.md`

- [x] **Step 1: Clone external source into scratch space**

Run:

```bash
rm -rf /tmp/fast_lio_ros2_probe
git clone --depth 1 --branch ros2 https://github.com/Ericsii/FAST_LIO_ROS2.git /tmp/fast_lio_ros2_probe
```

- [x] **Step 2: Run source and dependency audit**

Run:

```bash
tools/check_phase2_fastlio_external.sh /tmp/fast_lio_ros2_probe
```

- [x] **Step 3: Attempt isolated build**

Run:

```bash
rm -rf /tmp/go2w_phase2b_fastlio_ws
mkdir -p /tmp/go2w_phase2b_fastlio_ws/src
ln -s /tmp/fast_lio_ros2_probe /tmp/go2w_phase2b_fastlio_ws/src/FAST_LIO_ROS2
source /opt/ros/humble/setup.bash
cd /tmp/go2w_phase2b_fastlio_ws
colcon build --symlink-install --packages-select fast_lio
```

Expected: build either succeeds or fails with a captured dependency error.

- [x] **Step 4: Record no-TF dry-run result**

If the wrapper has hard-coded TF publication or the build fails, do not launch
FAST-LIO2. Record the runtime dry-run as blocked with the specific reason.

### Task 4: State And Operator Documentation

**Files:**
- Modify: `docs/verification/phase2_fastlio_dryrun.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `README.md`

- [x] **Step 1: Create or update verification evidence**

Record clone commit, ROS package availability, build result, source output
topics, TF publication status, and next required decision.

- [x] **Step 2: Update architecture state**

Record that Phase 2B found the current FAST-LIO2 dry-run gate status and that
`odom -> base_link` remains unclaimed.

- [x] **Step 3: Update README**

Add a short Phase 2B status note pointing operators to the verification record.

### Task 5: Final Verification And Commit

**Files:**
- All Phase 2B files above.

- [x] **Step 1: Verify accepted simulation baseline**

Run:

```bash
./tools/verify_go2w_sim_launch.sh
```

Expected: existing Phase 1 simulation baseline still passes.

- [x] **Step 2: Check whitespace**

Run:

```bash
git diff --check
```

Expected: exit code `0`.

- [x] **Step 3: Commit and push**

Run:

```bash
git add README.md docs/architecture/architecture_state.md docs/verification/phase2_fastlio_dryrun.md docs/superpowers/specs/2026-04-27-phase2b-fastlio-dryrun-design.md docs/superpowers/plans/2026-04-27-phase2b-fastlio-dryrun.md tools/check_phase2_fastlio_external.sh
git commit -m "docs: record phase2 fastlio dryrun gate"
git push origin main
```

Expected: commit is pushed to `origin/main`.
