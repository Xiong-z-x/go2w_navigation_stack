# Go2W 跨楼层导航系统

本仓库是 Go2W 跨楼层自主导航巡检系统的 ROS 2 Humble 主仓库，采用
simulation-first 路线推进。

当前架构事实源不是本 README，而是：

- `docs/architecture/system_blueprint.md`
- `docs/architecture/interface_contracts.md`
- `docs/architecture/architecture_state.md`

## 当前状态

- 当前正式阶段：`Phase 2`
- `Phase 1` 状态：仿真可控闭环已完成并进入可审计验收状态
- 当前唯一允许推进方向：FAST-LIO2 input/output plumbing，以及感知侧接管
  `odom -> base_link` TF authority

`Phase 2` 之前不要引入 Nav2、`nav2_route`、mission orchestration、楼梯执行逻辑或
地形升维内容。

## 运行环境基线

当前仓库冻结为 ROS 2 Humble + Gazebo Fortress-only 基线：

- Ubuntu 22.04 / WSL2
- ROS 2 Humble
- Gazebo Fortress：`ignition-gazebo6` / `ign gazebo-6`
- ROS-Gazebo bridge：`ros-humble-ros-gz-*`
- 控制链：`ros-humble-gz-ros2-control`

不要在当前基线上混入 Gazebo Harmonic / Garden 运行时，例如：

- `gz-sim8`
- `libgz-*`
- `python3-gz*`
- `packages.osrfoundation.org` Gazebo runtime path

## Gazebo / GPU 说明

当前接受的稳定 Gazebo 基线是软件渲染：

```bash
ros2 launch go2w_sim sim.launch.py use_gpu:=false
```

当前 WSLg 能看到 RTX 3050 的 D3D12 OpenGL 加速，但 Gazebo Fortress GUI 的
`use_gpu:=true` 路径仍会触发 Ogre2 `GL3PlusTextureGpu::copyTo`
`UnimplementedException`。2026-04-27 的 re-baseline 进一步确认：
`go2w_sim use_gpu:=true headless:=true` 也会在 Gazebo sensors/rendering
线程触发同类异常。因此 Gazebo GPU rendering 不属于当前验收合同，也不是
`Phase 1` 或首个 `Phase 2` 阻塞项。

RViz 可独立使用当前 WSLg/NVIDIA OpenGL 路径；后续 CUDA / FAST-LIO / ML
用 GPU 需要按各自链路单独验证。完整记录见：

```bash
docs/verification/gazebo_gpu_rebaseline.md
```

## Phase 1 已验收闭环

`Phase 1` 已验证以下能力：

- Gazebo Sim 可启动到 `ign gazebo-6`
- `robot_state_publisher` 正常发布机器人模型
- `gz_ros2_control` 可加载并激活 controller manager
- `joint_state_broadcaster` 和 `diff_drive_controller` 可进入 `active`
- `/cmd_vel` 控制链可驱动占位差速底盘
- `/clock`、`/imu`、`/lidar_points`、`/robot_description` 可发布
- RViz 可启动并使用 Phase 1 配置显示 RobotModel、TF 和 PointCloud2
- `diff_drive_controller` 不发布 `odom -> base_link`
- `odom -> base_link` authority 已预留给 Phase 2 FAST-LIO 接管

完整验收记录见：

```bash
docs/verification/phase1_runtime_acceptance.md
```

## 构建

从仓库根目录执行：

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
```

只验证当前仿真闭环相关包时，可执行：

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_description go2w_sim
```

## Headless 验证

推荐优先运行无 GUI 验证，避免 WSLg 图形层干扰主线判断：

```bash
./tools/verify_go2w_sim_launch.sh
```

该脚本会：

- 清理残留 Gazebo / RViz / `go2w_sim` launch 进程
- 启动 `go2w_sim` 的 Fortress-only headless 路径
- 验证启动日志使用 `ign gazebo-6`
- 验证 `joint_state_broadcaster` 和 `diff_drive_controller` 为 `active`
- 验证 `/clock`、`/imu`、`/lidar_points` 能产生消息

如需在已启动仿真后检查 Phase 1 topic / TF 验收项：

```bash
./tools/verify_phase1_runtime.sh
```

## GUI / RViz 启动

默认 GUI + RViz 路径：

```bash
./tools/cleanup_sim_runtime.sh
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch go2w_sim sim.launch.py use_gpu:=false headless:=false launch_rviz:=true
```

当前 RViz 配置文件：

```bash
go2w_description/rviz/go2w_phase1.rviz
```

## 当前 Phase 2 边界

下一步只允许进入首个 Phase 2 perception baseline：

- FAST-LIO2 input/output plumbing
- perception 对 `odom -> base_link` TF authority 的接管
- 必要的 `go2w_sim` 输入输出对接
- 稳定 odom / point cloud / map baseline

禁止顺手推进：

- Nav2 / `nav2_route`
- route graph authoring
- mission orchestration
- staircase execution logic
- elevation mapping / traversability

## 协作纪律

每个实现任务必须提供完整 6 项任务单：

1. Task Goal
2. Current Phase
3. Allowed Files
4. Forbidden Files
5. Required Commands
6. Definition of Done

任务单不完整时，不进入实现。
