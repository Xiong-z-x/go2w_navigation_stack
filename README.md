# Go2W 跨楼层导航系统

本仓库是 Go2W 跨楼层自主导航巡检系统的 ROS 2 Humble 主仓库，采用
simulation-first 路线推进。

当前架构事实源不是本 README，而是：

- `docs/architecture/system_blueprint.md`
- `docs/architecture/interface_contracts.md`
- `docs/architecture/architecture_state.md`

## 当前状态

- 当前正式阶段：`Phase 3`
- `Phase 1` 状态：仿真可控闭环已完成并进入可审计验收状态
- `Phase 2` 状态：FAST-LIO2 输入/输出、感知侧 `odom -> base_link`
  TF authority、稳定 perception baseline、首个 Nav2 costmap consumer gate
  已完成并验收
- `Phase 3A` 状态：最小同层 Nav2 planner/controller/BT 导航闭环已完成并验收
- 当前唯一允许推进方向：Phase 3B 的最小 `nav2_route` / 手工 route graph
  基线，必须继续按单任务、完整任务单、最小改动推进

不要把 Phase 3B 直接扩展成 mission orchestration、楼梯执行、多楼层行为、
elevation mapping 或 traversability。

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

`use_gpu` 只用于 Gazebo rendering 选择，不代表所有 GUI 统一走同一路径。
默认 launch 会让 Gazebo 保持软件渲染，同时对 RViz 进程单独注入已验证的
WSLg/NVIDIA OpenGL 环境。后续 CUDA / FAST-LIO / ML 用 GPU 需要按各自链路
单独验证。完整记录见：

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

该命令保持 Gazebo `use_gpu:=false`，但 RViz 进程会默认使用已验证的
WSLg/NVIDIA OpenGL 环境。

当前 RViz 配置文件：

```bash
go2w_description/rviz/go2w_phase1.rviz
```

`go2w_sim` 默认仍启动 `empty_world.sdf`。Phase 3A 另提供专用特征验证世界，
用于给 FAST-LIO-backed Nav2 闭环提供可观测几何：

```bash
ros2 launch go2w_sim sim.launch.py \
  use_gpu:=false \
  headless:=true \
  launch_rviz:=false \
  world:="$(pwd)/install/go2w_sim/share/go2w_sim/worlds/phase3a_feature_world.sdf" \
  world_name:=go2w_phase3a_feature_world
```

## Phase 2 已验收基线

Phase 2 已完成：

- FAST-LIO2 input/output plumbing
- perception 对 `odom -> base_link` TF authority 的接管
- 必要的 `go2w_sim` 输入输出对接
- 稳定 odom / point cloud / map baseline
- 首个 Nav2 costmap consumer gate

Phase 2 总体验收记录见：

```bash
docs/verification/phase2_runtime_acceptance.md
```

Phase 2A 完成 FAST-LIO2 输入契约审计。记录见：

```bash
docs/verification/phase2_fastlio_input_audit.md
```

审计结果：`/lidar_points` 具备 `x,y,z,intensity,ring`，但缺少每点时间字段。
该问题已在 Phase 2E 通过本地 perception adapter 收口。

Phase 2B 进一步检查外部 FAST_LIO_ROS2 dry-run gate，发现候选 wrapper
需要处理 `livox_ros_driver2` 构建依赖和硬编码 TF 发布路径
`camera_init -> body`。记录见：

```bash
docs/verification/phase2_fastlio_dryrun.md
```

Phase 2C 已建立外部 FAST_LIO_ROS2 patch gate：仓库只保存 patch 与验证工具，
不 vendor FAST-LIO2 源码。当前 patch 已验证可在
`FAST_LIO_ENABLE_LIVOX=OFF` 下完成 isolated build，并将 FAST-LIO TF 发布
通过 `publish.tf_publish_en` 参数默认关闭。记录见：

```bash
docs/verification/phase2_fastlio_patch_gate.md
```

Phase 2D 新增自动化 no-TF runtime dry-run。准备脚本会复用或拉取外部
FAST_LIO_ROS2 到 `/tmp`，应用 Phase 2C patch，并在 scratch workspace 构建：

```bash
./tools/prepare_phase2d_fastlio_external.sh
```

运行时采证脚本会启动 headless `go2w_sim`，启动 patched FAST-LIO，采样输出
topic 与 TF：

```bash
./tools/verify_phase2d_fastlio_no_tf_dryrun.sh
```

Phase 2D 结果：FAST-LIO 可在 no-TF 配置下启动并发布 `/Odometry`、
`/cloud_registered`、`/cloud_registered_body`、`/Laser_map`、`/path`；
未发布 `camera_init -> body` TF。其遗留的点云 `time` 字段和输出 frame
问题已在 Phase 2E 收口。记录见：

```bash
docs/verification/phase2_fastlio_no_tf_dryrun.md
```

Phase 2E 已新增本地 `go2w_perception` contract adapters：

- 输入 adapter：`/lidar_points` -> `/fastlio/input/lidar_points`，补齐
  FAST-LIO 所需 `time` 字段
- 输出 adapter：FAST-LIO raw `/Odometry`、`/path`、`/cloud_registered`、
  `/cloud_registered_body`、`/Laser_map` -> `/go2w/perception/*` contract topics
- frame contract：raw `camera_init/body` 消息帧重写为项目侧 `odom/base_link`
  消息语义
- Phase 2E 本身仍不发布 TF，不声明 `odom -> base_link`

验证命令：

```bash
./tools/verify_phase2e_fastlio_contract.sh
```

Phase 2E 结果：adapted pointcloud 已带 `time` 字段，FAST-LIO missing-time
warning 为 `0`，contract odometry 为 `odom/base_link`，contract clouds/path 使用
项目 frame，未发布 `camera_init -> body` TF，`odom -> base_link` 仍未被声明。
记录见：

```bash
docs/verification/phase2_fastlio_contract_stabilization.md
```

Phase 2F 已新增 dedicated perception TF authority activation dry-run：

- TF authority node：订阅 `/go2w/perception/odom`
- 发布 TF：`odom -> base_link`
- duplicate authority 检查：激活前无 `odom -> base_link`，且
  `diff_drive_controller.enable_odom_tf=False`
- FAST-LIO upstream TF 检查：不发布 `camera_init -> body`

验证命令：

```bash
./tools/verify_phase2f_tf_authority.sh
```

Phase 2F 结果：`odom -> base_link` 已由 perception 侧 runtime dry-run
发布并验证，FAST-LIO missing-time warning 仍为 `0`，`camera_init -> body` TF
仍缺席。记录见：

```bash
docs/verification/phase2_tf_authority_activation.md
```

Phase 2G 已新增 perception runtime stability acceptance：

- 默认 30 秒 command window
- 验证 `/go2w/perception/odom`、`/tf`、`/fastlio/input/lidar_points`、
  `/go2w/perception/cloud_registered` 的非零频率
- 验证 `/go2w/perception/path`、`/go2w/perception/cloud_body`、
  `/go2w/perception/laser_map` 有消息
- 验证 `odom -> base_link` 持续存在，`camera_init -> body` 仍缺席
- 验证 FAST-LIO missing-time warning 仍为 `0`

验证命令：

```bash
./tools/verify_phase2g_perception_stability.sh
```

Phase 2G 结果：30 秒稳定性窗口通过，perception baseline 已具备进入
首个 Nav2/costmap consumer gate 的仓库证据。记录见：

```bash
docs/verification/phase2_perception_stability_acceptance.md
```

Phase 2H 已新增第一个 Nav2 costmap consumer gate：

- standalone `/costmap/costmap` lifecycle node
- `global_frame=odom`
- `robot_base_frame=base_link`
- PointCloud2 observation source：`/go2w/perception/cloud_body`
- 发布 `/costmap/costmap`
- 不启动 planner、controller、BT、`nav2_route`、mission、楼梯、多楼层、
  elevation 或 traversability 节点

验证命令：

```bash
./tools/verify_phase2h_costmap_consumer.sh
```

当前 Phase 2H 结果：运行时门禁通过，Phase 2 总体验收完成。记录见：

```bash
docs/verification/phase2_costmap_consumer_gate.md
```

## 当前 Phase 3 边界

Phase 3A 已新增最小同层 Nav2 导航闭环：

- planner、controller、BT Navigator lifecycle 均可进入 `active`
- local/global costmap 消费 `/go2w/perception/cloud_body`
- Nav2 消费 `/go2w/perception/odom`
- `/navigate_to_pose` 可在 `odom` frame 下完成短距离同层 goal
- Nav2 发布 `/cmd_vel`
- perception odometry 在 goal 期间发生变化
- `odom -> base_link` 仍由 perception 侧发布
- 不发布临时 `map -> odom`
- 不启动 `nav2_route`、route graph、mission、楼梯、多楼层、elevation 或
  traversability 节点

验证命令：

```bash
./tools/verify_phase3a_nav2_same_floor.sh
```

当前 Phase 3A 结果：运行时门禁通过。记录见：

```bash
docs/verification/phase3a_nav2_same_floor.md
```

下一步只允许进入 Phase 3B 的最小 `nav2_route` / 手工 route graph 基线。必须
继续消费 Phase 3A 已验收的 odom、TF、Nav2 和 costmap 输入。

禁止顺手推进：

- mission orchestration
- staircase execution logic
- multi-floor behavior
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
