# Go2W Real Model Same-Floor Route Following Design

## Status
设计方向已批准；实现尚未开始。

本任务的目标是补齐 opt-in 真实 Go2W 模型和现有同层 Nav2 闭环之间的运行证据。它不改变当前默认 placeholder 仿真入口，也不扩大为真实楼梯动力学或 production mission orchestration。

## Problem
当前仓库已经有两条相邻但尚未合并验证的证据链：

- Phase 3A：placeholder 模型上已经证明 Nav2 同层闭环可以通过 `/navigate_to_pose` 产生 `/cmd_vel`，并由 perception-owned `odom -> base_link` 支撑导航反馈。
- Go2W real model / motion-mode baseline：真实 Go2W 模型、foot-wheel `diff_drive_controller`、leg position controller、sensor topics、joint states 和 stand initializer 已经通过 opt-in headless verifier。

缺口是：尚未证明真实 Go2W 模型在相同感知 TF 权限边界下能被 Nav2 同层闭环驱动，并产生可诊断的真实模型运动反馈。

## Chosen Approach
采用独立 verifier 路线：新增一个 real-model same-floor route-following runtime gate，复用 Phase 3A 的系统组成，但把仿真入口切到 `go2w_sim sim_go2w_real.launch.py`。

该 verifier 应验证：

- 真实模型 headless launch 启动成功。
- `joint_state_broadcaster`、`leg_position_controller`、`diff_drive_controller` 均为 `active`。
- `go2w_stand_initializer` 完成启动站立命令发布。
- `/clock`、`/imu`、`/lidar_points` 有消息。
- `diff_drive_controller.enable_odom_tf` 保持 `False`，不抢占 `odom -> base_link`。
- `go2w_perception` 仍拥有 `odom -> base_link`。
- Nav2 lifecycle nodes 到达 `active`。
- `/navigate_to_pose` goal 成功，期间 `/cmd_vel` 出现非零命令。
- `/diff_drive_controller/odom` 和 `/go2w/perception/odom` 都显示超过阈值的运动量。
- 禁止引入 `map_server`、AMCL、`map -> odom`、mission、route-server、stair runtime、elevation 或 traversability 节点。

## Why This Route
- 风险最低：不触碰 Phase 3A placeholder 验收脚本，不切默认模型。
- 与架构一致：`go2w_description`、`go2w_sim`、`go2w_control`、`go2w_perception`、`go2w_navigation` 的职责边界不变。
- 直接处理当前最大风险：把“真实模型可启动”推进到“真实模型可被 Nav2 同层闭环驱动”。
- 可回退：新 verifier 是 opt-in gate，失败不会破坏已验收 Phase 4 / Phase 5A 证据链。

## Task Card

### 1. Task Goal
新增并验证真实 Go2W 模型同层 Nav2 route-following gate，证明 `sim_go2w_real.launch.py` 下的真实模型可以通过现有 Nav2 同层闭环接收 `/cmd_vel` 并产生可诊断运动反馈。

### 2. Current Phase
`Phase 4 accepted` 后的 post-Phase-4 hardening。该任务不改变 formal active phase，不声明真实跨楼层自主导航完成。

### 3. Allowed Files
- `tools/verify_go2w_real_model_route_following.sh`
- `docs/verification/go2w_real_model_route_following.md`
- `docs/architecture/architecture_state.md`
- `docs/handoff/current_project_state.md`
- `docs/handoff/next_agent_notes.md`
- `docs/handoff/risk_cleanup_log.md`
- `README.md`
- 必要时只允许最小补充：
  - `go2w_navigation/launch/*`
  - `go2w_navigation/config/*`
  - `go2w_navigation/test/*`
  - `go2w_control/go2w_control_runtime/motion_profiles.py`
  - `go2w_sim/config/controllers_go2w_real.yaml`
  - `go2w_sim/launch/sim_go2w_real.launch.py`
  - `tools/cleanup_sim_runtime.sh`

### 4. Forbidden Files
- 不修改 `go2w_perception` TF authority 语义。
- 不修改 Phase 3C route graph 或 map metadata。
- 不修改 `stair_exec` Action 接口。
- 不切换 `go2w_sim sim.launch.py` 的默认 placeholder 路径。
- 不引入 `map_server`、AMCL、`map -> odom` 定位链。
- 不引入 elevation mapping、traversability、automatic stair detection 或 automatic connector generation。
- 不引入 Unitree SDK2 硬件控制路径。

### 5. Required Commands
至少执行：

```bash
bash -n tools/verify_go2w_real_model_route_following.sh
git diff --check
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_description go2w_sim go2w_control go2w_perception go2w_navigation
colcon test --packages-select go2w_description go2w_sim go2w_control go2w_perception go2w_navigation
colcon test-result --verbose
./tools/verify_go2w_real_model_route_following.sh
```

如 verifier 暴露旧默认路径风险，还必须复跑：

```bash
./tools/verify_go2w_sim_launch.sh
```

### 6. Definition of Done
- 新 verifier 以 headless Fortress-only 路径可重复运行。
- Verifier 输出稳定 result key，例如 `go2w_real_model_route_following_result: PASS`。
- 真实模型 controller、stand initializer、sensor topics、TF authority、Nav2 lifecycle 和 `/navigate_to_pose` goal 均有证据。
- `/cmd_vel` 非零命令、`/diff_drive_controller/odom` 运动量、`/go2w/perception/odom` 运动量均被记录并通过阈值检查。
- `diff_drive_controller.enable_odom_tf` 仍为 `False`。
- 未出现 `map -> odom`，未出现禁止节点。
- `docs/verification/go2w_real_model_route_following.md` 记录命令、证据目录、result keys、已验证事实和仍未覆盖项。
- `architecture_state.md`、handoff 文档和 `README.md` 只记录已验证事实，不把该任务夸大为真实楼梯控制或跨楼层自主导航。

## Implementation Notes
- 优先复用 Phase 3A 的 Nav2 参数和短距离 goal 策略。只有在真实模型运行证据显示必要时，才新增 real-model 专用参数文件。
- Verifier 应使用独立 `ROS_DOMAIN_ID` 和 `GZ_PARTITION`，并在退出时调用 `tools/cleanup_sim_runtime.sh`。
- 仿真 world 优先使用 Phase 3A feature world，避免 empty world 对 FAST-LIO / costmap 验证过于退化。
- 运动阈值应保守，目标是证明闭环存在，不做速度性能调参。
- 如果 `/go2w/perception/odom` 与 `/diff_drive_controller/odom` 差异明显，应记录为 odometry-scale follow-up，不在本任务内做大范围控制器调参。

## Non-Goals
- production Mission Orchestrator。
- 真实楼梯运动控制器和 leg trajectory tuning。
- 真实跨楼层自主行为。
- `nav2_route` real operation plugin。
- 默认模型切换。
- map-frame localization。
- elevation / traversability / automatic stair connector。

## Risks
- 真实模型碰撞、质量或轮式接触参数可能导致小目标运动量不足。
- FAST-LIO 在真实模型传感器布局下可能比 placeholder 更敏感，需要区分感知失败和控制失败。
- 如果为通过 verifier 直接放宽 Nav2 或控制器阈值，可能掩盖真实 route-following 问题；阈值变更必须记录原因和证据。
- 长 shell verifier 容易复制 Phase 3A 逻辑造成维护负担；本任务优先保持隔离，后续再考虑公共 probe 抽取。

## Open Validation Items After This Task
即使本任务通过，仍然不代表：

- 真实楼梯动力学已验证。
- 真实 Go2W 模型可以作为默认仿真基线。
- 多楼层自主导航已完成。
- `map_server` / AMCL / `map -> odom` 定位链已实现。
- 硬件 Unitree SDK2 控制链已接入。
