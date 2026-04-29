# Phase 2G Perception Runtime Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify the activated Phase 2 perception chain remains stable over a longer headless simulation motion window.

**Architecture:** Add a single runtime acceptance verifier and evidence document. Reuse Phase 2F launch and patched no-TF FAST-LIO; do not add new ROS nodes or change package interfaces.

**Tech Stack:** ROS 2 Humble, Gazebo Fortress headless launch, Bash verifier, `ros2 topic hz`, `ros2 topic echo`, `ros2 param get`, patched external FAST_LIO_ROS2 scratch workspace.

---

## Scope Lock

This plan implements one task only: Phase 2G perception runtime stability acceptance.

It must not:

- modify Gazebo world, URDF, controller YAML, or sensor declarations;
- modify any ROS package source code;
- modify Nav2, mission, control, or staircase files;
- vendor FAST_LIO_ROS2 source into this repository;
- re-enable FAST-LIO upstream TF publication;
- treat this as Nav2 readiness.

## File Structure

- Create: `tools/verify_phase2g_perception_stability.sh`
- Create: `docs/verification/phase2_perception_stability_acceptance.md`
- Create: `docs/superpowers/specs/2026-04-30-phase2g-perception-stability-design.md`
- Create: `docs/superpowers/plans/2026-04-30-phase2g-perception-stability.md`
- Modify: `README.md`
- Modify: `docs/architecture/architecture_state.md`

## Task 1: Runtime Stability Verifier

**Files:**
- Create: `tools/verify_phase2g_perception_stability.sh`

- [ ] **Step 1: Create verifier from Phase 2F runtime pattern**

Use the Phase 2F verifier structure, with these Phase 2G additions:

- `GO2W_PHASE2G_STABILITY_SECONDS`, default `30`
- bounded `/cmd_vel` publisher for the full stability window
- `ros2 topic hz` captures for `/go2w/perception/odom`, `/tf`,
  `/fastlio/input/lidar_points`, and `/go2w/perception/cloud_registered`
- once-message checks for `/go2w/perception/path`,
  `/go2w/perception/cloud_body`, and `/go2w/perception/laser_map`
- before/after odometry x-position comparison
- `/cmd_vel` publish-count check
- process-alive checks after the stability window

- [ ] **Step 2: Run shell checks**

Run:

```bash
bash -n tools/verify_phase2g_perception_stability.sh
shellcheck tools/verify_phase2g_perception_stability.sh
```

Expected: no output.

## Task 2: Documentation And State Update

**Files:**
- Create: `docs/verification/phase2_perception_stability_acceptance.md`
- Modify: `README.md`
- Modify: `docs/architecture/architecture_state.md`

- [ ] **Step 1: Add verification document**

Record Phase 2G scope, forbidden scope, verifier command, observed output, and
current decision.

- [ ] **Step 2: Update architecture state**

After the verifier passes, mark Phase 2G as accepted and set the next boundary
to the first Nav2/costmap consumer gate only if it remains limited to consuming
the verified perception outputs.

- [ ] **Step 3: Update README**

Add the Phase 2G verifier command and explicitly state that Nav2 is still a
separate next task.

## Task 3: Final Verification And Commit

**Files:**
- All changed files from Tasks 1-2.

- [ ] **Step 1: Run required verification**

Run:

```bash
python3 -m pytest go2w_perception/test -q
source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim
bash -n tools/verify_phase2g_perception_stability.sh
shellcheck tools/verify_phase2g_perception_stability.sh
./tools/verify_phase2g_perception_stability.sh
./tools/verify_go2w_sim_launch.sh
git diff --check
```

- [ ] **Step 2: Commit and push**

Run:

```bash
git status --short --branch
git add README.md docs/architecture/architecture_state.md docs/verification/phase2_perception_stability_acceptance.md docs/superpowers/specs/2026-04-30-phase2g-perception-stability-design.md docs/superpowers/plans/2026-04-30-phase2g-perception-stability.md tools/verify_phase2g_perception_stability.sh
git diff --cached --check
git commit -m "test: accept phase2g perception stability"
git push origin main
```
