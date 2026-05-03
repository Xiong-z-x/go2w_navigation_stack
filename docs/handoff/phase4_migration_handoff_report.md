# Phase 4 迁移前交接总报告

本报告最初记录 2026-04-30 的 Phase 4 迁移前快照。Phase 4A、Phase 4B-min、
Phase 4C-min、Phase 4D-min 和 Phase 4 accepted 已在 2026-05-01 补充验收；Phase 5A、
real-model baseline / route-following、Phase 4E stair fixture / mission recovery 和
real-model regression wrapper 已在 2026-05-02 前后补充验收。最新状态以 `docs/architecture/architecture_state.md`、
`docs/verification/phase4a_stair_handoff_acceptance.md` 和
`docs/verification/phase4b_mission_segment_runtime.md`、
`docs/verification/phase4c_flat_segment_gate.md`、
`docs/verification/phase4d_route_tracking_feedback.md`、
`docs/verification/phase4_runtime_acceptance.md`、
`docs/verification/phase5a_live_route_tracking.md`、
`docs/verification/go2w_real_model_motion_mode_baseline.md`、
`docs/verification/go2w_control_chain_regression.md`、
`docs/verification/go2w_real_model_route_following.md`、
`docs/verification/phase4e_stair_fixture.md`、
`docs/verification/phase4e_mission_recovery.md` 和
`docs/verification/go2w_real_model_regression.md` 为准。

2026-05-02 迁移前最终封板补充：real-model same-floor route-following 已完成
dedicated hardening，三次 clean-domain 复跑均 PASS。它现在是 opt-in regression
候选，但仍是 route-state-sensitive，不能替代稳定控制链门禁。因此当前迁移前稳定
控制链判断仍以 `docs/verification/go2w_control_chain_regression.md` 和
`tools/verify_go2w_control_chain_regression.sh` 为准；包含 route-following 的
`tools/verify_go2w_real_model_regression.sh` 继续保留为 opt-in 回归，不作为默认
封板门禁。

## 1. 项目总目标
构建 Go2W 跨楼层自主导航巡检系统的 ROS 2 Humble 主仓库。路线是
simulation-first：先在 Gazebo/RViz 中打通仿真、控制、FAST-LIO、Nav2、
route graph 和楼梯行为交接，再逐步升级到高程图、可通行性和自动楼梯连接器。

## 2. 当前阶段位置与整体路线
初始迁移快照时，正式阶段是 `Phase 3`，Phase 3 已验收，尚未进入 `Phase 4A`。
当前最新状态已推进到 `Phase 4 accepted` 验收：最小楼梯状态机/控制权交接骨架、
mission-side route segmentation / stair dispatch runtime、flat/stair/flat execution gate、
route tracking feedback observation gate，以及 Phase 4 总体验收 gate 均已通过仓库内 runtime verifier。
之后又补充了 Phase 5A live route tracking observation gate、opt-in 真实 Go2W 模型与
motion-mode baseline、real-model same-floor route-following、mission-runtime real-model
flat execution gate（已保留 route graph 目标 yaw）、Phase 4E real-model stair fixture、
Phase 4E mission recovery，以及 opt-in real-model regression wrapper。这些后续证据不改变
active phase 标签，也不等于真实楼梯动力学或完整 production Mission Orchestrator。

阶段路线：
- Phase 0：接口契约与系统边界。
- Phase 1：仿真可控、可观测。
- Phase 2：FAST-LIO 定位/建图基础。
- Phase 3：同层 Nav2 导航与 route graph 骨架。
- Phase 4：楼梯状态机与控制权交接闭环。
- Phase 5：高程/可通行性/自动连接器。

## 3. 核心环境与依赖条件
- Ubuntu 22.04 / WSL2。
- ROS 2 Humble。
- Gazebo Fortress-only：`ignition-gazebo6` / `ign gazebo-6`。
- `ros-humble-ros-gz-*` 与 `ros-humble-gz-ros2-control`。
- Gazebo 默认软件渲染：`use_gpu:=false`。
- FAST-LIO 源码不 vendor 入仓库，默认使用 ignored repo-local cache：
  `.go2w_external/`。

不要混入 Gazebo Harmonic/Garden，不要默认启用 Gazebo GPU rendering。

## 4. 当前技术路线和架构思路
系统严格分层：
- simulation 只负责 Gazebo 与传感器。
- perception 负责 FAST-LIO、里程计、点云、TF authority。
- navigation 负责 Nav2、costmap、planner/controller、route server；当前还承载
  Phase 4C-min `NavigateToPose` flat executor verifier skeleton 和 Phase 4D-min
  `ComputeAndTrackRoute` feedback verifier skeleton。
- mission 负责目标语义、楼层语义、分段调度和 mission recovery；当前已有 Phase 4A
  handoff demo、Phase 4B-min one-shot mission segment runtime、Phase 4D-min feedback
  observer、RunMission skeleton、bounded FIFO queueing 和 Phase 4E checkpoint/resume/retry skeleton。
- control 负责最终 locomotion mode 与 stair execution；当前已有 Phase 4A
  command gate、stair executor skeleton、motion profiles、leg hold outlet 和 Phase 4E
  phase-aware stair execution diagnostics。

冻结接口：
- TF 最小链：`map -> odom -> base_link`。
- `odom -> base_link` 当前由 perception path 声明。
- 平地连续运动入口：`cmd_vel`。
- 楼梯入口：dedicated `stair_exec` Action。
- `nav2_route` 只做 route graph/route tracking，不是 3D 地形规划器。

## 5. 关键模块与职责划分
- `go2w_description`：占位机器人模型、opt-in 真实 Go2W 模型资产与 RViz 配置。
- `go2w_sim`：Gazebo Fortress launch、worlds、bridge、controller orchestration。
- `go2w_perception`：FAST-LIO contract adapters 与 TF authority。
- `go2w_navigation`：Nav2/costmap/route graph 配置与 launch；Phase 4C-min 和
  Phase 4D-min verifier skeletons。
- `go2w_control`：Phase 4A 已有 `StairExec` Action、command gate 和最小 stair executor skeleton；Phase 4E 已补充 phase-aware stair execution diagnostics。
- `go2w_mission`：Phase 4A 已有 handoff demo 和最小验证 launch；Phase 4B-min
  已有 one-shot mission segment runtime；Phase 4E 已有 checkpoint/recovery skeleton；
  尚不是完整 production orchestrator。

## 6. 到目前为止已完成的内容
- Phase 1 仿真底盘控制闭环。
- Phase 2 FAST-LIO 输入输出与 perception-owned `odom -> base_link`。
- Phase 2H 首个 Nav2 costmap consumer gate。
- Phase 3A 同层 Nav2 navigation closed loop。
- Phase 3B `nav2_route` same-floor manual graph baseline。
- Phase 3C repo-local FAST-LIO external cache、多楼层 route graph/map metadata、
  hospital world asset。
- Phase 4A staircase connector detection、dedicated `/stair_exec` Action skeleton、
  command ownership handoff、success/failure/cancel/timeout diagnostics。
- Phase 4B-min mission segment runtime：`/compute_route`、flat/stair/flat 分段、
  `/stair_exec` 调度、success/failure/cancel/timeout/route unavailable/
  connector unavailable diagnostics。
- Phase 4C-min flat/stair/flat execution gate：flat segments 经 navigation-owned
  `NavigateToPose` Action gate，stair segment 经 `/stair_exec`，并验证 flat failure/
  cancel/timeout/unavailable diagnostics。
- Phase 4D-min route tracking feedback observation gate：mission observer 消费
  `ComputeAndTrackRoute` feedback，检测 staircase edge `500` 与 `stair_exec`
  `operations_triggered`，并验证 missing operation / unavailable action diagnostics。
- Phase 4 accepted aggregate acceptance gate：串联 pre-handoff、Phase 4A/4B/4C/4D
  runtime verifiers、Phase 4 相关包 build/test 与 `colcon test-result --verbose`。
- Phase 5A live route tracking observation gate：在受控 TF trajectory fixture 下直接观察
  installed `nav2_route` route server / `ComputeAndTrackRoute` feedback 中的 staircase
  edge `500` 和 operation metadata。
- Opt-in Go2W real model / motion-mode baseline：真实模型资产、四 foot wheel
  controller、leg position controller、传感器 topics、`flat -> wheeled` /
  `stair -> legged` mode state 和启动站立初始化。
- Opt-in real-model same-floor route-following：真实模型短 `NavigateToPose` 同层目标。
- Phase 4E real-model stair fixture：`/stair_exec` action 成功、command gate
  `flat/wheeled -> stair/legged -> flat/wheeled`、phase-aware stair executor plan/state。
- Phase 4E mission recovery：stair executor 不可用时写入 `RECOVERABLE` checkpoint，
  重启后从 segment index `1` 恢复并完成到 `MISSION_SUCCEEDED`。
- Opt-in real-model regression wrapper：串联 real-model baseline、same-floor
  route-following 和 Phase 4E stair fixture，不切换默认 placeholder launch。

## 7. 当前真实状态
仓库已具备同层 SLAM/感知基础、Nav2 同层闭环、Phase 4 所需的手工多楼层 route
graph / hospital world 资产、Phase 4A 最小楼梯控制权交接骨架、Phase 4B-min
mission segment runtime、Phase 4C-min flat/stair/flat execution gate、Phase 4D-min
route tracking feedback observation gate、Phase 4 accepted 总验收 gate，以及 Phase 4E
stair fixture / mission recovery / real-model regression 后续硬化。但它还不是完整跨楼层
自主系统：完整 production Mission Orchestrator、真实 Nav2 route tracking against robot
motion、真实楼梯控制、自动连接器均未实现。

## 8. 本次已清理/已修复的问题
- 修复活动 FAST-LIO 验证脚本仍默认 `/tmp` 的路径漂移。
- 修复 Phase 2C patch/audit 工具默认路径落后于 Phase 3C 的问题。
- 清理源码侧 Python 缓存目录。
- 新增集中交接包，降低新对话上下文失真风险。
- 新增 Phase 4 迁移前静态验证脚本。
- 新增 Phase 4A runtime 验证脚本，覆盖 route connector detection、`/stair_exec`、
  command gate 互斥和 success/failure/cancel/timeout 诊断。
- 新增 Phase 4B-min runtime 验证脚本，覆盖 route segmentation、`/stair_exec` dispatch
  和 success/failure/cancel/timeout/route unavailable/connector unavailable 诊断。
- 新增 Phase 4C-min runtime 验证脚本，覆盖 flat `NavigateToPose` dispatch、
  flat/stair/flat sequence 和 flat failure/cancel/timeout/unavailable 诊断。
- 新增 Phase 4D-min runtime 验证脚本，覆盖 `ComputeAndTrackRoute` feedback、
  staircase edge observation、`stair_exec` operation trigger observation、missing
  operation 和 unavailable action 诊断。
- 新增 Phase 4 总体验收脚本和验收文档，串联 pre-handoff、Phase 4A/4B/4C/4D、
  build/test 与 `colcon test-result --verbose`。
- 修正 Phase 4C/4D verifier 的 `ROS_DOMAIN_ID` 生成范围，避免超过 Fast-DDS 可用
  domain 范围导致假失败。
- 新增真实 Go2W opt-in 模型、motion-mode baseline、同层 route-following verifier、
  Phase 4E stair fixture、Phase 4E mission recovery 和 real-model regression wrapper。

## 9. 仍然存在但暂不可修复的风险或限制
- Gazebo GPU rendering 在当前 WSLg/Fortress/Ogre2 路径下仍不稳定。
- Unitree Go2W 真实模型已作为 opt-in 路径导入并验证，但尚未替换默认 placeholder launch。
- Phase 3C route graph 是手工 floor atlas，不是自动地图生成。
- 没有完整 production Mission Orchestrator；当前已有 RunMission skeleton、JSON checkpoint、
  同一 goal resume、bounded FIFO queueing、operator control service、operator-triggered
  durable queue replay、bounded terminal task history 和有限 retry，但还没有优先级调度
  或完整 fleet-level/operator workflow policy。
- Phase 4C-min flat executor 是 verifier skeleton，不执行真实 Nav2 route tracking against robot motion。
- Phase 4D-min feedback executor 是 verifier skeleton，不执行真实 `nav2_route`
  tracking against robot motion，也不执行真实 route operation plugin。
- 没有真实 Stair Executor 运动控制器；当前只有 dedicated Action skeleton、profile-aware
  phase plan 和 conservative leg hold outlet。
- 没有 `map_server` / AMCL / `map -> odom` 闭环。
- 没有 elevation mapping、traversability 或 automatic stair detection。

## 10. Phase 4 的直接起点
Phase 4A 应从最小楼梯状态机/控制权交接骨架开始。该起点已按以下边界实施并验收：

- 输入：Phase 3C 手工 route graph 中的 staircase connector metadata。
- 行为：检测/模拟进入楼梯边时暂停或隔离 Nav2 控制权。
- 调用：触发 dedicated `stair_exec` Action 的最小 mock/skeleton。
- 输出：楼梯段完成、失败、取消或超时后状态可诊断。
- 验收重点：状态机流转、控制权互斥、接口可观测、失败/取消/超时信号可诊断。

Phase 4A 不应包含真实楼梯运动控制调参、多楼层自主任务闭环、自动楼梯发现、
elevation mapping、traversability、Unitree model import 或 perception TF 改造。

## 10.1 Phase 4B-min 的直接补充
Phase 4B-min 已在 Phase 4A skeleton 上补充最小 mission-side runtime：

- 输入：同一份 Phase 3C 手工 hospital route graph。
- 路由：调用 `/compute_route` 获取 node `100` 到 node `202` 的 route。
- 分段：将 route edge 分解为 `flat:300|301;stair:500;flat:400|401`。
- 调用：仅 stair segment 触发 dedicated `/stair_exec` Action。
- 输出：成功、失败、取消、超时、route unavailable、connector unavailable 以稳定
  `phase4b_final_result` key 暴露。

Phase 4B-min 不应被解释为 production Mission Orchestrator、真实平地 Nav2 route
tracking、真实跨楼层自主导航或真实楼梯运动控制。

## 10.2 Phase 4C-min 的直接补充
Phase 4C-min 已在 Phase 4B-min runtime 上补充最小 flat execution gate：

- 输入：同一份 Phase 3C 手工 hospital route graph。
- 路由与分段：沿用 Phase 4B-min `/compute_route` 与 flat/stair/flat segmentation。
- Flat 调度：flat segments 通过 navigation-owned `NavigateToPose` verifier Action。
- Stair 调度：stair segment 继续通过 dedicated `/stair_exec` Action。
- 输出：验证 `flat -> stair -> flat` sequence，以及 flat failure、cancel、timeout、
  Action unavailable 以稳定 mission result key 暴露。

Phase 4C-min 不应被解释为 production Mission Orchestrator、真实 Nav2 route tracking
against robot motion、真实跨楼层自主导航或真实楼梯运动控制。

## 10.3 Phase 4D-min 的直接补充
Phase 4D-min 已在 Phase 4C-min execution gate 上补充最小 route tracking feedback
observation gate：

- 输入：标准 `nav2_msgs/action/ComputeAndTrackRoute` feedback 形态。
- Feedback：navigation-owned verifier Action server 发布 route edges
  `300, 301, 500, 400, 401`。
- Mission 观测：mission-owned observer 检测 staircase edge `500`。
- Operation 观测：observer 检测 `operations_triggered` 中的 `stair_exec`。
- 输出：success、missing operation trigger、unavailable route tracking action 均以稳定
  key 暴露。

Phase 4D-min 不应被解释为 production Mission Orchestrator、真实 Nav2 route tracking
against robot motion、真实 `nav2_route` operation plugin、真实跨楼层自主导航或真实楼梯
运动控制。

## 10.4 Phase 4 accepted 的直接补充
Phase 4 accepted 已在 Phase 4D-min 之上补充总验收 gate：

- 验证脚本：`tools/verify_phase4_runtime_acceptance.sh`
- 验收文档：`docs/verification/phase4_runtime_acceptance.md`
- 串联内容：`tools/verify_phase4_pre_handoff.sh`、Phase 4A/4B/4C/4D runtime verifiers、
  `colcon build --symlink-install --packages-select go2w_navigation go2w_control go2w_mission`、
  `colcon test --packages-select go2w_navigation go2w_control go2w_mission`、`colcon test-result --verbose`

Phase 4 accepted 不应被解释为 production Mission Orchestrator、真实 Nav2 route tracking
against robot motion、真实 `nav2_route` operation plugin、真实跨楼层自主导航或真实楼梯
运动控制。

## 11. 推荐先跑的验证
```bash
./tools/verify_phase4_pre_handoff.sh
./tools/verify_phase4a_stair_handoff.sh
./tools/verify_phase4b_mission_segments.sh
./tools/verify_phase4c_flat_segment_gate.sh
./tools/verify_phase4d_route_tracking_feedback.sh
./tools/verify_phase4e_stair_fixture.sh
./tools/verify_phase4e_mission_recovery.sh
./tools/verify_go2w_control_chain_regression.sh
./tools/verify_go2w_real_model_regression.sh
./tools/verify_phase4_runtime_acceptance.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
colcon test --packages-select go2w_control go2w_mission go2w_navigation
colcon test-result --verbose
```
