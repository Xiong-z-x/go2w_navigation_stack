# 当前项目状态总览

## 项目总目标
本仓库是 Go2W 跨楼层自主导航巡检系统主仓库。长期目标是在
Ubuntu 22.04 / WSL2 / ROS 2 Humble / Gazebo Fortress 环境中，从零构建一套
simulation-first 的自主导航栈，最终实现：

- RViz 下发目标。
- Gazebo 中完成同层导航。
- 通过楼梯行为交接完成跨楼层闭环。
- FAST-LIO 提供定位与建图基础。
- 远期升级到高程图、可通行性分析和自动楼梯连接器。

核心工程原则仍是：先闭环，再升级智能。

## 当前阶段
- 当前正式阶段：`Phase 4 accepted`
- 当前状态：Phase 3A、Phase 3B、Phase 3C、Phase 4 迁移前封板、Phase 4A、Phase 4B-min、Phase 4C-min、Phase 4D-min、Phase 4 总体验收、Phase 5A live route tracking observation gate、opt-in Go2W real model / motion-mode baseline、opt-in real-model same-floor route-following verifier、Phase 4E real-model stair fixture、Phase 4E mission recovery 和 opt-in real-model regression wrapper 均已有仓库内验收证据。
- 当前 Phase 4 accepted 范围：manual-connector runtime chain，覆盖楼梯 handoff、mission route segmentation、flat/stair/flat Action 调度、`ComputeAndTrackRoute` feedback observation，以及 pre-handoff、Phase 4A/4B/4C/4D runtime verifiers、构建和测试的聚合验收。
- 下一步：只能在新的完整任务单或当前自主审批模式下的自批准任务单中推进 post-Phase-4 的最小单主题任务。当前已完成的 Phase 4E 硬化仍不等于真实楼梯动力学、完整 production Mission Orchestrator 或默认 real-model re-baseline。

## 当前环境基线
- Ubuntu 22.04 / WSL2
- ROS 2 Humble
- Gazebo Fortress：`ignition-gazebo6` / `ign gazebo-6`
- ROS-Gazebo bridge：`ros-humble-ros-gz-*`
- 控制链：`ros-humble-gz-ros2-control`
- Gazebo 默认渲染：`use_gpu:=false`

Gazebo GPU rendering 不是当前验收合同。RViz 可单独使用 WSLg/NVIDIA OpenGL
环境，但这不改变 Gazebo 软件渲染基线。

## 当前核心模块状态
- `go2w_description`：占位机器人 URDF、opt-in 真实 Go2W URDF/mesh baseline、
  RViz 配置、robot_state_publisher launch。
- `go2w_sim`：Fortress-only Gazebo launch、empty world、Phase 3A feature world、
  Phase 3C hospital world、桥接与 controller orchestration、opt-in
  `sim_go2w_real.launch.py`。
- `go2w_control`：Phase 4A 已新增 `StairExec` Action、command gate、
  owner->motion-mode state、Go2W motion profiles、stand initializer、minimal
  stair executor skeleton；当前 stair executor policy 复用了 legged motion profile、钳制 stair 线速度，在 stair owner 激活时发布 12 关节 leg hold command，并输出
  `prepare -> wheel_lock -> body_height_transition_down -> execute_stairs ->
  body_height_transition_up -> release` 的可诊断阶段状态；当前还暴露了显式 stair tuning
  覆盖参数，但尚未实现真实楼梯运动控制器。
  当前 real-model baseline 还把 `go2w_stand_initializer` 显式切到 `--motion-mode legged`，
  并把 profile 摘要和 controller-state 轮询写进验收证据，避免再依赖单条 spawner 日志。
- `go2w_perception`：FAST-LIO 输入/输出 adapter、perception TF authority、
  `odom -> base_link` 发布链与测试。
- `go2w_navigation`：Phase 2H costmap gate、Phase 3A Nav2 同层闭环、
  Phase 3B/3C route graph baseline、Phase 4C-min flat navigation executor skeleton、
  Phase 4D-min route tracking feedback executor skeleton、Phase 5 real-model same-floor
  Nav2 params file 和 route-following verifier。
- `go2w_mission`：Phase 4A 已新增 handoff demo 和最小 launch 验证路径；
  Phase 4B-min 已新增 one-shot mission segment runtime；Phase 4C-min 已将 flat
  segment 接入 navigation-owned `NavigateToPose` gate；Phase 4D-min 已新增
  route tracking feedback observer；Phase 5A 已新增 live route tracking probe；
  现已额外提供 opt-in `RunMission` Action skeleton / mission API verifier，用于
  route segmentation、flat/stair dispatch 和诊断结果码；当前 mission API 又新增
  JSON checkpoint 持久化、同一 mission goal resume 和有限 retry，但尚未实现完整
  production Mission Orchestrator。

## 已完成闭环
- Phase 1：Gazebo + `gz_ros2_control` + `/cmd_vel` 底盘可控闭环。
- Phase 2：FAST-LIO input/output plumbing、perception-owned `odom -> base_link`、
  stability baseline、Nav2 costmap consumer gate。
- Phase 3A：最小同层 Nav2 planner/controller/BT 导航闭环。
- Phase 3B：最小 `nav2_route` + 手工 route graph baseline。
- Phase 3C：FAST-LIO repo-local external cache、floor-aware hospital route graph、
  hospital multi-floor world asset。
- Phase 4A：手工 staircase connector 检测、dedicated `/stair_exec` Action
  skeleton、flat/stair 控制权互斥、完成/失败/取消/超时诊断。
- Phase 4B-min：调用 `/compute_route`、分解 flat/stair/flat mission segments、
  通过 `/stair_exec` 调度楼梯段、诊断成功/失败/取消/超时/route unavailable/
  connector unavailable。
- Phase 4C-min：通过 `NavigateToPose` 调度 flat segments，通过 `/stair_exec`
  调度 stair segment，验证 `flat -> stair -> flat` 顺序以及 flat failure/cancel/
  timeout/unavailable 诊断。
- Phase 4D-min：通过 `ComputeAndTrackRoute` feedback verifier 和 mission observer
  验证 staircase edge `500` 可观测、`stair_exec` route operation trigger 可观测、
  missing operation 与 unavailable action 可诊断。
- Phase 4 accepted：通过 `tools/verify_phase4_runtime_acceptance.sh` 串联
  pre-handoff、Phase 4A/4B/4C/4D runtime verifiers、Phase 4 相关包 build/test 和
  `colcon test-result --verbose`。
- Phase 5A：通过 `tools/verify_phase5a_live_route_tracking.sh` 直接观察真实
  `nav2_route` route_server / `ComputeAndTrackRoute` feedback 中的 staircase edge
  `500` 和 `AdjustSpeedLimit` operation metadata。
- Go2W real model / motion-mode baseline：通过
  `tools/verify_go2w_real_model_baseline.sh` 验证 opt-in 真实模型、四 foot wheel
  `diff_drive_controller`、腿部 position controller、sensor topics、joint states
  和启动站立初始化；当前验收还要求 `go2w_stand_initializer_profile`、
  `controller_states_ready` 与 `go2w_stand_initializer_result` 这些可审计日志键。
- Go2W real model same-floor route-following verifier：通过
  `tools/verify_go2w_real_model_route_following.sh` 验证 opt-in 真实模型上的短
  `NavigateToPose` 同层目标、`phase5_real_model_nav2_same_floor.yaml` 参数文件、
  perception-owned `odom -> base_link`、`/cmd_vel` 运动和 Nav2 生命周期。
- Phase 4E real-model stair fixture：通过 `tools/verify_phase4e_stair_fixture.sh`
  验证 opt-in real-model fixture 中 `/stair_exec` Action 成功、command gate
  `flat/wheeled -> stair/legged -> flat/wheeled`、阶段化 stair executor 状态、
  profile-limited stair velocity 和 leg hold release。
- Phase 4E mission recovery：通过 `tools/verify_phase4e_mission_recovery.sh`
  验证 mission API 在 stair executor 不可用时写入 `RECOVERABLE` checkpoint，
  重启后从 segment index `1` 恢复，并在 stair executor 可用时完成到
  `MISSION_SUCCEEDED`。
- Phase 4E stair tuning smoke test：通过 `tools/verify_phase4e_stair_tuning_overrides.sh`
  验证 stair executor 可接受显式 body height / foot raise / gait / speed overrides，
  且默认 baseline 不变时仍能闭环成功。
- Go2W real-model regression wrapper：通过
  `tools/verify_go2w_real_model_regression.sh` 串联 real-model baseline、
  real-model same-floor route-following 和 Phase 4E stair fixture。该 wrapper 是
  opt-in regression，不改变默认 placeholder 仿真基线。

## 当前未完成内容
- 真实 Go2W 模型仍是 opt-in 路径，虽已有 broader regression wrapper，但尚未替换默认 placeholder 仿真基线。
- `go2w_mission` 的 `RunMission` 已有 checkpoint/retry/resume skeleton，但不是完整 production Mission Orchestrator。
- 未实现完整 production Mission Orchestrator 的多任务队列、操作员恢复策略、优先级调度和长期任务管理。
- Phase 4C-min 的 flat executor 仍是 verifier skeleton，尚未被 production Nav2/nav2_route route tracking 实现替换；但 opt-in real-model same-floor route-following verifier 已通过短目标验证。
- Phase 5A 已接入真实 `nav2_route` route_server feedback，但仍未验证真实机器人运动上的
  route tracking。
- 未实现真实楼梯运动控制器和控制参数调优；当前 Phase 4E 只把 wheel lock、body height transition、leg hold 和 release 做成可观察阶段骨架。
- 未实现真实跨楼层自主行为。
- 未实现 `map_server` / AMCL / `map -> odom` 定位链。
- 未实现 elevation mapping / traversability / automatic stair detection。

## 当前默认 FAST-LIO 外部依赖位置
Phase 3C 后，当前工具默认不再使用 `/tmp` 作为 FAST-LIO source/workspace：

```text
.go2w_external/src/FAST_LIO_ROS2
.go2w_external/workspaces/fast_lio_ros2
```

可通过以下环境变量覆盖：

```bash
GO2W_FASTLIO_CACHE_ROOT=/path/to/cache
GO2W_FASTLIO_SRC=/path/to/FAST_LIO_ROS2
GO2W_FASTLIO_WS=/path/to/fast_lio_ws
```

历史验证文档中的 `/tmp/...` 路径是当时证据路径，不代表当前默认策略。
