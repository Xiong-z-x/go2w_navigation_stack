# Phase 1 Runtime Acceptance

## Purpose
This document records the reproducible runtime acceptance procedure for the Phase 1 simulation controllability baseline.
Its goal is to prove, with fixed commands, that the current change set:

- publishes `/clock`
- publishes `/imu`
- publishes `/lidar_points`
- does not let the current Phase 1 control chain publish `odom -> base_link`
- exposes `lidar_link`, `imu_link`, and the temporary Gazebo sensor alias frames required for RViz point cloud visualization

## Preconditions
- Work from the repository root.
- Build the workspace first:

```bash
source /opt/ros/humble/setup.bash && colcon build --symlink-install
```

- Start the simulation in terminal A:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch go2w_sim sim.launch.py
```

- Run the checks below in terminal B after Gazebo, controllers, and RViz have started.

## Fixed Command Sequence

### 1. Message existence
```bash
timeout 15s ros2 topic echo --once /clock
timeout 15s ros2 topic echo --once /imu
timeout 15s ros2 topic echo --once /lidar_points
```

Expected result:
- all three commands return one message before timeout

### 2. Topic inventory
```bash
ros2 topic list
```

Expected result:
- `/clock`
- `/imu`
- `/lidar_points`
- `/robot_description`
- `/tf`
- `/tf_static`

### 3. Topic rates
```bash
ros2 topic hz /imu
ros2 topic hz /lidar_points
```

Expected result:
- `/imu` has a stable non-zero rate
- `/lidar_points` has a stable non-zero rate

### 4. TF graph
```bash
ros2 run tf2_tools view_frames
```

How the `odom -> base_link` conclusion is derived:
- inspect the generated `frame_yaml` in the command output
- confirm that `base_link` is parented to `base_footprint`
- confirm that no frame block shows `parent: 'odom'`

This reasoning matters because the Phase 1 goal is not to create a new odom authority.
The goal is only to ensure that `diff_drive_controller` is no longer publishing `odom -> base_link`, so FAST-LIO can take that edge in Phase 2 without TF conflict.

Expected visible frames:
- `base_link`
- `lidar_link`
- `imu_link`
- `go2w_placeholder/base_footprint/lidar_sensor`
- `go2w_placeholder/base_footprint/imu_sensor`

### 5. One-command reproducible verifier
```bash
./tools/verify_phase1_runtime.sh
```

The script:
- dynamically resolves the repository root
- sources `install/setup.bash` from the current workspace
- checks `/clock`, `/imu`, `/lidar_points`
- samples `/imu` and `/lidar_points` rates
- runs `view_frames`
- fails if `base_link` is still parented to `odom`
- fails if the required sensor and alias frames are missing

## Observed Result For The Current Change Set
Observed on the current change set before commit:

- `/clock`: message received
- `/imu`: message received
- `/lidar_points`: message received
- `/imu` rate: about `70 Hz` during the scripted verification window
- `/lidar_points` rate: about `6.7 Hz` during the scripted verification window
- `view_frames`: `base_link` parent is `base_footprint`
- `view_frames`: no `parent: 'odom'` entry exists
- `view_frames`: `lidar_link`, `imu_link`, `go2w_placeholder/base_footprint/lidar_sensor`, and `go2w_placeholder/base_footprint/imu_sensor` are all present

## RViz Expectation
`go2w_description/rviz/go2w_phase1.rviz` is considered correct for Phase 1 runtime acceptance when:

- `RobotModel` is visible
- `TF` is visible
- `PointCloud2` subscribes to `/lidar_points`
- fixed frame is `base_link`

This is a Phase 1 observability baseline only.
The alias TF that maps Gazebo sensor-scoped frames back onto `lidar_link` and `imu_link` is a temporary compatibility layer and must not become the long-term perception baseline.

## Known Constraints
- Gazebo GUI remains on the software-rendering baseline with `use_gpu:=false`
- the placeholder URDF still mixes geometry, control plugin, and sensor declarations in one file
- the Gazebo sensor alias frames are transitional and are intentionally accepted only for Phase 1
