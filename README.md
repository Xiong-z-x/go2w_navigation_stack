# Go2W 跨楼层导航系统

本仓库是 Go2W 跨楼层自主导航巡检系统的 ROS 2 Humble 主仓库，采用
simulation-first 路线推进。

实际项目仓库根是 `/home/xiongzx/go2w_ws/src/go2w_navigation_stack`。外层
`/home/xiongzx/go2w_ws` 是 ROS workspace，不应用其 git 状态判断项目历史。

当前架构事实源不是本 README，而是：

- `docs/architecture/system_blueprint.md`
- `docs/architecture/interface_contracts.md`
- `docs/architecture/architecture_state.md`

进入新对话或后续 Phase 4 工作前，先读取当前状态和迁移交接包：

- `docs/handoff/README.md`
- `docs/handoff/pre_migration_final_freeze_report.md`
- `docs/handoff/project_state_audit.md`
- `docs/verification/phase4d_route_tracking_feedback.md`
- `docs/verification/phase5a_live_route_tracking.md`
- `docs/verification/go2w_real_model_motion_mode_baseline.md`
- `docs/verification/go2w_control_chain_regression.md`
- `docs/verification/go2w_mission_real_flat_execution.md`
- `docs/verification/go2w_real_model_regression.md`
- `docs/verification/phase4e_stair_fixture.md`
- `docs/verification/phase4e_mission_recovery.md`
- `docs/verification/phase4e_stair_tuning_overrides.md`
- `docs/verification/mission_api_scheduling_policy.md`
- `docs/verification/mission_api_orchestrator_control.md`
- `docs/verification/mission_api_queue_replay.md`
- `docs/verification/mission_api_task_history.md`
- `docs/verification/phase4_runtime_acceptance.md`
- `docs/verification/phase4c_flat_segment_gate.md`
- `docs/verification/phase4b_mission_segment_runtime.md`
- `docs/verification/phase4a_stair_handoff_acceptance.md`
- `docs/verification/mission_api_skeleton.md`
- `docs/verification/go2w_real_model_route_following.md`
- `docs/handoff/phase4_migration_handoff_report.md`
- `docs/handoff/new_model_initialization_prompt.md`

## 当前状态

- 当前正式阶段：`Phase 4 accepted`
- 当前迁移前最终封板：`docs/handoff/pre_migration_final_freeze_report.md`
  已记录 2026-05-02 总自检、风险清理、剩余限制和后续项目改进顺序，并在
  2026-05-04 刷新了 mission hardening 与实际 repo root 接手风险。
- `Phase 1` 状态：仿真可控闭环已完成并进入可审计验收状态
- `Phase 2` 状态：FAST-LIO2 输入/输出、感知侧 `odom -> base_link`
  TF authority、稳定 perception baseline、首个 Nav2 costmap consumer gate
  已完成并验收
- `Phase 3A` 状态：最小同层 Nav2 planner/controller/BT 导航闭环已完成并验收
- `Phase 3B` 状态：最小 `nav2_route` / 手工 route graph 基线已完成并验收
- `Phase 3C` 状态：FAST-LIO 外部依赖生产化、持久多楼层 route graph
  baseline、多层医院仿真 world 资产已完成并验收
- `Phase 3` 状态：同层导航 + 拓扑骨架 + Phase 4 前置硬化资产已完成并验收
- `Phase 4A` 状态：最小楼梯状态机/控制权交接骨架已完成并验收
- `Phase 4B-min` 状态：最小 mission segment runtime 已完成并验收
- `Phase 4C-min` 状态：最小 flat/stair/flat execution gate 已完成并验收
- `Phase 4D-min` 状态：最小 route tracking feedback observation gate 已完成并验收
- `Phase 4` 状态：Phase 4A、Phase 4B-min、Phase 4C-min、Phase 4D-min 和总验收 gate 已完成并验收
- `Phase 5A` 证据门：live route tracking observation gate 已完成并验收，作为 Phase 4D-min 之外的 live route-server-backed 观察证据
- Go2W real model / motion-mode baseline：真实 Go2W 模型、四足轮式 controller profile、
  wheeled/legged mode state、显式 `legged` startup profile 日志和启动站立初始化已作为 opt-in 路径完成验证；同层
  real-model route-following verifier 也已通过短 `NavigateToPose` 目标验证；Phase 4E
  real-model stair fixture、稳定 control-chain regression wrapper 和 opt-in real-model
  regression wrapper 也已通过；mission-runtime real-model flat execution gate 现在也已
  验证 `RunMission` flat-only segment 可在不启动 `go2w_flat_nav_executor` 的情况下调用真实
  Nav2 `/navigate_to_pose`；route-following 仍不纳入稳定 control-chain wrapper；
  旧 `sim.launch.py` placeholder 路径仍是默认基线
- `go2w_mission` 还额外提供 opt-in `RunMission` Action skeleton 与 mission API
  verifier，能诊断 route segmentation、flat/stair dispatch、invalid goal、
  cancel、timeout、route unavailable、flat action unavailable、bounded FIFO queueing 和
  相关诊断；当前已新增 JSON checkpoint、同一 mission goal resume、有限 retry、operator-state
  snapshot backend、`MissionControl` pause/resume/status/cancel_active/replay_queue/history/archive_history
  控制面、operator-triggered durable queue replay ledger 和 bounded terminal task-history
  ledger，但仍不是完整
  production Mission Orchestrator。mission runtime real-model flat execution gate 也已经接通真实
  Nav2 `/navigate_to_pose`，并通过共享 `mission_pose` helper 保留了目标 yaw；
  production Mission Orchestrator scheduling policy、控制面、queue replay 和 task history
  窄范围已经完成，后续应转向 priority scheduling 单主题任务。

不要把 Phase 4 accepted 误判成 production mission orchestration、真实 Nav2
route tracking against robot motion、真实 `nav2_route` operation plugin、真实楼梯
控制器调参、多楼层自主行为、elevation mapping 或 traversability。

也不要把 opt-in 真实模型基线误判成真实步态控制或楼梯动力学闭环；它只证明模型、
controller、传感器 topic、`flat -> wheeled` / `stair -> legged` 状态、controller
state 轮询、启动站立命令、短同层目标、phase-aware `/stair_exec` fixture 和 opt-in
regression wrapper 可重复验证。

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

真实 Go2W 模型与运动模式基线是独立 opt-in 路径：

```bash
./tools/verify_go2w_real_model_baseline.sh
```

该脚本会构建 `go2w_description`、`go2w_control`、`go2w_sim`，然后 headless
启动：

```bash
ros2 launch go2w_sim sim_go2w_real.launch.py use_gpu:=false headless:=true launch_rviz:=false
```

验证内容包括：

- 官方 Go2W 模型资产可加载
- `joint_state_broadcaster`、`leg_position_controller`、`diff_drive_controller`
  通过 controller-state 轮询进入 `active`
- `/joint_states` 包含腿部关节和 foot wheel 关节
- `/clock`、`/imu`、`/lidar_points` 可发布
- `diff_drive_controller.enable_odom_tf` 仍为 `False`
- `go2w_stand_initializer` 显式使用 `--motion-mode legged`，打印 profile 摘要，
  并可发布 12 关节站立命令
- `go2w_stair_executor` 复用 legged motion profile 作为保守 stair baseline，
  默认 stair 线速度来自 profile 元数据，并在 stair owner 激活时发布 12 关节
  leg hold command，但仍不是真实楼梯控制器
- `go2w_stair_executor` 现在也暴露显式 stair tuning 覆盖参数
  (`--stair-body-height-m`、`--stair-foot-raise-height-m`、
  `--stair-gait-type`、`--stair-speed-level`、`--stair-max-linear-velocity-mps`)，
  默认仍保持保守 baseline，不会改变当前 accepted 验证链

同层 real-model route-following verifier 可重复验证短 `NavigateToPose` 目标：

```bash
./tools/verify_go2w_real_model_route_following.sh
```

该脚本使用 `go2w_navigation/config/phase5_real_model_nav2_same_floor.yaml`，
以 real-model 参数文件保留 perception-owned `odom -> base_link`，验证短同层
目标到达，不是 production route tracking，也不是楼梯动力学。2026-05-02
dedicated hardening 已修复 DWB abort 路径并取得 3 次 clean-domain 连续 PASS；
它现在是 opt-in regression 候选，但尚未自动纳入稳定 control-chain wrapper。

Mission runtime real-model flat execution gate 可重复验证 `RunMission` flat-only
segment 调用真实 Nav2 `/navigate_to_pose`，并且不启动 Phase 4C 的
`go2w_flat_nav_executor`：

```bash
./tools/verify_go2w_mission_real_flat_execution.sh
```

该脚本启动 opt-in real model、perception、FAST-LIO、real-model Nav2 和 mission API，
动态生成 odom-frame flat-only route graph，reload `/route_server/set_route_graph`，
再发送 `RunMission` goal。它证明 mission flat segment 可接入真实 robot-motion flat
execution surface；它仍不是 production Mission Orchestrator、真实 `nav2_route`
robot-motion route tracking、跨楼层真实闭环或楼梯动力学。

稳定的 real-model control-chain 回归门禁可使用：

```bash
./tools/verify_go2w_control_chain_regression.sh
```

该 wrapper 只串联 real-model baseline、Phase 4E stair fixture、mission
recovery 和 stair tuning smoke test，不包含同层 route-following smoke。

Phase 4E real-model stair fixture 可重复验证 `/stair_exec` Action 闭环、command
gate `flat/wheeled -> stair/legged -> flat/wheeled`、阶段化 stair executor 状态和
leg hold/release 诊断：

```bash
./tools/verify_phase4e_stair_fixture.sh
```

Mission recovery checkpoint/resume gate 可重复验证 stair executor 不可用时的
`RECOVERABLE` checkpoint、重启后的同一 mission goal resume，以及最终
`MISSION_SUCCEEDED`：

```bash
./tools/verify_phase4e_mission_recovery.sh
```

real-model 更大范围回归保持 opt-in，不替换默认 placeholder 基线：

```bash
./tools/verify_go2w_real_model_regression.sh
```

stair tuning smoke test 可在不改变默认 baseline 的前提下复用同一闭环：

```bash
./tools/verify_phase4e_stair_tuning_overrides.sh
```

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

Phase 2D 新增自动化 no-TF runtime dry-run。Phase 3C 已将该外部依赖路径
硬化为 repo-local ignored cache，准备脚本会按 pinned lock 复用或拉取外部
FAST_LIO_ROS2，应用 Phase 2C patch，并在外部 workspace 构建：

```bash
./tools/prepare_phase2d_fastlio_external.sh
```

默认生成位置：

```text
.go2w_external/src/FAST_LIO_ROS2
.go2w_external/workspaces/fast_lio_ros2
```

锁定文件：

```text
go2w_perception/external/fast_lio_ros2.lock.env
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

Phase 3B 已新增最小 `nav2_route` / 手工 route graph 基线：

- `go2w_navigation` 声明 `nav2_route` runtime 依赖
- 安装 `odom` frame 的手工 GeoJSON route graph
- `route_server` lifecycle 可进入 `active`
- `/route_server/set_route_graph` 可重载已安装 graph
- `/compute_route` 可从 node `0` 到 node `3` 返回成功 route
- 返回的 `Route` 和 `Path` 均为 `odom`
- `/route_graph` 发布 `visualization_msgs/msg/MarkerArray`
- 不启动 mission、楼梯、多楼层、elevation、traversability、`map_server` 或
  `amcl` 节点

验证命令：

```bash
./tools/verify_phase3b_route_graph.sh
```

当前 Phase 3B 结果：运行时门禁通过。记录见：

```bash
docs/verification/phase3b_route_graph_baseline.md
```

Phase 3C 已新增 Phase 4 前置硬化基线：

- FAST-LIO 外部源码与 workspace 默认迁移到 `.go2w_external/`，不再默认使用
  `/tmp`，并用 `go2w_perception/external/fast_lio_ros2.lock.env` 锁定上游 ref
- 新增 `map` frame 的 floor-aware 医院多楼层 route graph：
  `go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson`
- 新增多层医院 Gazebo world：
  `go2w_sim/worlds/phase3c_hospital_multifloor_world.sdf`

验证命令：

```bash
GO2W_FASTLIO_SKIP_BUILD=1 ./tools/verify_phase3c_fastlio_dependency_baseline.sh
./tools/verify_phase3c_multifloor_route_graph.sh
./tools/verify_phase3c_hospital_world.sh
```

验收记录见：

```bash
docs/verification/phase3c_hardening_acceptance.md
```

该阶段只提供依赖、地图、route graph 和 world 资产；不启动 Mission
Orchestrator、stair executor runtime、elevation mapping、traversability、
automatic stair detection、`map_server` 或 AMCL。

当前 Phase 3 结果：Phase 3A 同层 Nav2 运动闭环 + Phase 3B route graph
可视化/计算基线 + Phase 3C 硬化资产均已通过，Phase 3 可关闭。

Phase 3 总体验收记录见：

```bash
docs/verification/phase3_runtime_acceptance.md
```

## 当前 Phase 4A 边界

Phase 4A 已新增最小楼梯状态机/控制权交接骨架：

- Phase 3C 医院多楼层 route graph 中的 staircase connector metadata 可被校验
- `route_server` 可计算从 node `100` 到 node `202` 且经过 connector edge `500`
  的 route
- `go2w_mission` 的 handoff demo 可检测楼梯边并触发 dedicated `/stair_exec`
  Action
- `go2w_control` 的 command gate 证明 flat/stair 控制权互斥：
  `/go2w/control/flat_cmd_vel` 与 `/go2w/control/stair_cmd_vel` 只有当前 owner
  对应的一路可进入 `/cmd_vel`
- `/stair_exec` skeleton 支持完成、失败、取消、超时等可诊断结果

验证命令：

```bash
./tools/verify_phase4a_stair_handoff.sh
```

验收记录见：

```bash
docs/verification/phase4a_stair_handoff_acceptance.md
```

该阶段只验证接口握手、状态诊断和控制权互斥；不验证真实楼梯动力学或跨楼层自主行为。

## 当前 Phase 4B-min 边界

Phase 4B-min 已新增最小 mission segment runtime：

- `go2w_mission` 可调用 `/compute_route` 获取 Phase 3C 手工 route graph 上的路线
- route edge 可分解为 flat/stair/flat mission segments
- staircase segment 通过 dedicated `/stair_exec` Action 执行
- runtime 可输出稳定 mission 结果：
  `MISSION_SUCCEEDED`、`MISSION_FAILED`、`MISSION_CANCELED`、`MISSION_TIMEOUT`、
  `ROUTE_UNAVAILABLE`、`CONNECTOR_UNAVAILABLE`
- `tools/verify_phase4b_mission_segments.sh` 可重复验证成功、失败、取消、超时、
  route unavailable 和 connector unavailable 路径

验证命令：

```bash
./tools/verify_phase4b_mission_segments.sh
```

验收记录见：

```bash
docs/verification/phase4b_mission_segment_runtime.md
```

该阶段只验证任务分段、楼梯 Action 调度和 mission 级诊断；flat segment 当前仍是
诊断占位，不运行真实 Nav2 route tracking，也不是 production Mission Orchestrator。

## 当前 Phase 4C-min 边界

Phase 4C-min 已新增最小 flat segment execution gate：

- `go2w_navigation` 提供 navigation-owned `go2w_flat_nav_executor`
- flat segment 通过标准 `nav2_msgs/action/NavigateToPose` Action 调度
- stair segment 仍通过 dedicated `/stair_exec` Action 调度
- mission runtime 可观测 `flat -> stair -> flat` 顺序
- runtime 可输出稳定 mission 结果：
  `MISSION_SUCCEEDED`、`FLAT_NAV_FAILED`、`MISSION_CANCELED`、
  `MISSION_TIMEOUT`、`FLAT_NAV_UNAVAILABLE`
- `tools/verify_phase4c_flat_segment_gate.sh` 可重复验证 success、flat failure、
  flat cancel、flat timeout 和 flat unavailable 路径

验证命令：

```bash
./tools/verify_phase4c_flat_segment_gate.sh
```

验收记录见：

```bash
docs/verification/phase4c_flat_segment_gate.md
```

该阶段只验证 flat/stair/flat 任务顺序和控制权路径；flat executor 仍是
navigation-owned verifier skeleton，不是真实 Nav2 route tracking，也不是
production Mission Orchestrator。

后续 mission-runtime real-model flat execution gate 已证明 mission API 可在
`launch_flat_nav_executor:=false` 时绕过该 verifier skeleton，并把 flat-only mission
segment 送到真实 Nav2 `/navigate_to_pose`。该新 gate 不删除 Phase 4C skeleton；
Phase 4C skeleton 仍用于 deterministic flat failure/cancel/timeout/unavailable 诊断。

## 当前 Phase 4D-min 边界

Phase 4D-min 已新增最小 route tracking feedback observation gate：

- `go2w_navigation` 提供 navigation-owned `ComputeAndTrackRoute` feedback verifier
  Action server
- `go2w_mission` 提供 mission-owned one-shot feedback observer
- observer 可接收 route edges `300, 301, 500, 400, 401`
- observer 可检测 staircase edge `500`
- observer 可检测 `operations_triggered` 中的 `stair_exec`
- `tools/verify_phase4d_route_tracking_feedback.sh` 可重复验证 success、missing
  operation trigger 和 unavailable action 路径

验证命令：

```bash
./tools/verify_phase4d_route_tracking_feedback.sh
```

验收记录见：

```bash
docs/verification/phase4d_route_tracking_feedback.md
```

该阶段只验证 mission 侧能消费 `ComputeAndTrackRoute` feedback 形态并观察 route
operation 触发信号；feedback source 仍是 verifier skeleton，不是真实机器人运动上的
route tracking，也没有执行真实 `nav2_route` operation plugin。

Phase 5A live route tracking observation gate 已将 route-feedback 验证接到真实
`nav2_route` route_server 和 `ComputeAndTrackRoute`，当前优先查看
`docs/verification/phase5a_live_route_tracking.md`。它仍然只是受控 TF trajectory
fixture 下的观察，不是物理楼梯动力学或 production Mission Orchestrator。

## 当前 Phase 4 accepted 总验收

Phase 4 accepted 已通过一键总验收 gate：

- `tools/verify_phase4_runtime_acceptance.sh` 串联 pre-handoff、Phase 4A/4B/4C/4D
  runtime verifiers、Phase 4 相关包构建与测试
- `docs/verification/phase4_runtime_acceptance.md` 记录最新总验收证据
- `colcon test-result --verbose` 在 Phase 4 相关包上保持 0 errors / 0 failures

验证命令：

```bash
./tools/verify_phase4_runtime_acceptance.sh
```

验收记录见：

```bash
docs/verification/phase4_runtime_acceptance.md
```

该总验收只确认 Phase 4 manual-connector runtime chain 已闭环，不引入 production
Mission Orchestrator、真实 Nav2 route tracking against robot motion、真实楼梯
控制器调参、多楼层自主行为或 automatic connector generation。

Phase 4 迁移前交接包一致性检查仍可用于检查历史交接包结构：

```bash
./tools/verify_phase4_pre_handoff.sh
```

后续任务禁止顺手推进：

- production mission orchestration
- production real Nav2 / nav2_route route tracking expansion beyond the accepted short real-model verifier
- real staircase traversal controller tuning
- multi-floor autonomous behavior
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
