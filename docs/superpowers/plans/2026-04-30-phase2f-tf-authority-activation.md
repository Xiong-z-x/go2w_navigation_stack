# Phase 2F TF Authority Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate and verify the perception-side `odom -> base_link` TF authority from Phase 2E FAST-LIO contract odometry.

**Architecture:** Add one dedicated `go2w_perception` TF authority node that subscribes to `/go2w/perception/odom` and publishes only `odom -> base_link`. Keep Phase 2E no-TF launch unchanged, and add a separate Phase 2F launch plus runtime verifier for duplicate-authority checks.

**Tech Stack:** ROS 2 Humble, `rclpy`, `tf2_ros.TransformBroadcaster`, `nav_msgs/msg/Odometry`, `geometry_msgs/msg/TransformStamped`, pytest, Bash verifier scripts.

---

## Scope Lock

This plan implements one task only: Phase 2F perception TF authority activation dry-run.

It must not:

- modify Gazebo world, URDF, controller YAML, or sensor declarations;
- modify Nav2, mission, control, or staircase files;
- vendor FAST_LIO_ROS2 source into this repository;
- re-enable FAST-LIO upstream TF publishing;
- change the Phase 2E no-TF launch behavior.

## File Structure

- Create: `go2w_perception/go2w_perception/fastlio_tf_authority.py`
- Create: `go2w_perception/scripts/go2w_fastlio_tf_authority`
- Create: `go2w_perception/config/phase2f_tf_authority.yaml`
- Create: `go2w_perception/launch/phase2f_tf_authority.launch.py`
- Create: `go2w_perception/test/test_fastlio_tf_authority.py`
- Create: `tools/verify_phase2f_tf_authority.sh`
- Create: `docs/verification/phase2_tf_authority_activation.md`
- Modify: `go2w_perception/CMakeLists.txt`
- Modify: `go2w_perception/package.xml`
- Modify: `README.md`
- Modify: `docs/architecture/architecture_state.md`

## Task 1: TF Authority Unit Boundary

**Files:**
- Create: `go2w_perception/test/test_fastlio_tf_authority.py`
- Create: `go2w_perception/go2w_perception/fastlio_tf_authority.py`
- Create: `go2w_perception/scripts/go2w_fastlio_tf_authority`
- Modify: `go2w_perception/package.xml`
- Modify: `go2w_perception/CMakeLists.txt`

- [ ] **Step 1: Write failing tests for odometry-to-transform conversion**

Create tests that import `odometry_to_transform` and
`validate_odometry_contract`, then verify:

```python
def test_odometry_to_transform_preserves_contract_stamp_and_pose():
    msg = Odometry()
    msg.header.stamp.sec = 12
    msg.header.stamp.nanosec = 34
    msg.header.frame_id = "odom"
    msg.child_frame_id = "base_link"
    msg.pose.pose.position.x = 1.0
    msg.pose.pose.position.y = 2.0
    msg.pose.pose.position.z = 3.0
    msg.pose.pose.orientation.w = 1.0

    tf_msg = odometry_to_transform(msg, "odom", "base_link")

    assert tf_msg.header.stamp.sec == 12
    assert tf_msg.header.stamp.nanosec == 34
    assert tf_msg.header.frame_id == "odom"
    assert tf_msg.child_frame_id == "base_link"
    assert tf_msg.transform.translation.x == 1.0
    assert tf_msg.transform.translation.y == 2.0
    assert tf_msg.transform.translation.z == 3.0
    assert tf_msg.transform.rotation.w == 1.0
```

- [ ] **Step 2: Verify tests fail before implementation**

Run:

```bash
python3 -m pytest go2w_perception/test/test_fastlio_tf_authority.py -q
```

Expected: import failure for `go2w_perception.fastlio_tf_authority`.

- [ ] **Step 3: Implement minimal TF conversion helpers and node**

Implement `validate_odometry_contract`, `odometry_to_transform`, and
`FastlioTfAuthority`. The node subscribes to `/go2w/perception/odom` and sends
the transform via `tf2_ros.TransformBroadcaster`.

- [ ] **Step 4: Add script and package wiring**

Install `scripts/go2w_fastlio_tf_authority`, add `tf2_ros` dependency, and add
the script to `CMakeLists.txt`.

- [ ] **Step 5: Run tests and build**

Run:

```bash
python3 -m pytest go2w_perception/test -q
source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim
```

Expected: tests pass and three packages build.

## Task 2: Phase 2F Launch And Runtime Verifier

**Files:**
- Create: `go2w_perception/config/phase2f_tf_authority.yaml`
- Create: `go2w_perception/launch/phase2f_tf_authority.launch.py`
- Create: `tools/verify_phase2f_tf_authority.sh`

- [ ] **Step 1: Add Phase 2F node config**

Set:

```yaml
go2w_fastlio_tf_authority:
  ros__parameters:
    use_sim_time: true
    odometry_topic: /go2w/perception/odom
    parent_frame: odom
    child_frame: base_link
```

- [ ] **Step 2: Add Phase 2F launch**

Launch the existing Phase 2E contract adapters and the new
`go2w_fastlio_tf_authority` node.

- [ ] **Step 3: Add runtime verifier**

The verifier must:

- prepare patched external FAST-LIO through the existing Phase 2D script;
- build `go2w_perception`, `go2w_description`, and `go2w_sim`;
- launch headless `go2w_sim`;
- prove `/clock`, `/imu`, and `/lidar_points` exist;
- prove no `odom -> base_link` exists before Phase 2F launch;
- prove runtime `diff_drive_controller.enable_odom_tf` is `False`;
- launch Phase 2F perception;
- launch FAST-LIO with `publish.tf_publish_en=false`;
- prove adapted pointcloud has `time`;
- prove contract odometry is `odom/base_link`;
- prove `/tf` contains `odom -> base_link`;
- prove `/tf` does not contain `camera_init -> body`;
- prove FAST-LIO missing-time warning count is zero.

- [ ] **Step 4: Run shell checks**

Run:

```bash
bash -n tools/verify_phase2f_tf_authority.sh
shellcheck tools/verify_phase2f_tf_authority.sh
```

Expected: no output.

## Task 3: Documentation And State Update

**Files:**
- Create: `docs/verification/phase2_tf_authority_activation.md`
- Modify: `README.md`
- Modify: `docs/architecture/architecture_state.md`

- [ ] **Step 1: Record Phase 2F evidence document**

Create a verification document that describes Phase 2F scope, forbidden scope,
automation command, expected evidence, and current decision.

- [ ] **Step 2: Update architecture state**

Mark Phase 2F as verified only after the runtime verifier passes. Set the next
boundary to the next Phase 2 perception baseline task, not Nav2.

- [ ] **Step 3: Update README**

Add the Phase 2F verifier command and state that `odom -> base_link` is now a
perception-side TF authority only after verification.

## Task 4: Final Verification And Commit

**Files:**
- All changed files from Tasks 1-3.

- [ ] **Step 1: Run required verification**

Run:

```bash
python3 -m pytest go2w_perception/test -q
source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim
bash -n tools/verify_phase2f_tf_authority.sh
shellcheck tools/verify_phase2f_tf_authority.sh
./tools/verify_phase2f_tf_authority.sh
./tools/verify_go2w_sim_launch.sh
git diff --check
```

- [ ] **Step 2: Commit and push**

Run:

```bash
git status --short --branch
git add README.md docs/architecture/architecture_state.md docs/verification/phase2_tf_authority_activation.md docs/superpowers/specs/2026-04-30-phase2f-tf-authority-activation-design.md docs/superpowers/plans/2026-04-30-phase2f-tf-authority-activation.md go2w_perception/CMakeLists.txt go2w_perception/package.xml go2w_perception/go2w_perception/fastlio_tf_authority.py go2w_perception/scripts/go2w_fastlio_tf_authority go2w_perception/config/phase2f_tf_authority.yaml go2w_perception/launch/phase2f_tf_authority.launch.py go2w_perception/test/test_fastlio_tf_authority.py tools/verify_phase2f_tf_authority.sh
git diff --cached --check
git commit -m "feat: activate phase2f perception tf authority"
git push origin main
```
