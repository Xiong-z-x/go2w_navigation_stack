# Go2W Real Model Motion-Mode Tuning Design

## Status
设计方向已自批准；实现和验证已完成。最终验收记录见
`docs/verification/go2w_real_model_motion_mode_baseline.md`。

本任务只处理 `go2w_control` 的 motion-mode baseline、real-model startup stand 和 stair 线速度基线。
它不改导航、mission、TF authority、route graph、map/server、AMCL 或楼梯拓扑逻辑。

## Problem
当前仓库已经有 opt-in 真实 Go2W 模型和最小 motion-mode baseline，但 motion-mode 的参数仍然过于隐式：

- `MotionModeProfile` 只有关节、轮子、速度上限和站立姿态，缺少更明确的运动模式元数据。
- `go2w_stand_initializer` 只发布站立姿态，没有显式说明当前 motion mode 和 profile。
- `go2w_stair_executor` 使用保守 stair 速度，但默认值没有和 profile 绑定，也没有显式的 tuning 入口。
- real-model launch 已经会启动站立初始化，但没有把 motion-mode 选择显式写入 launch 参数。

同时，当前已经能从官方 Unitree 资料中提取到可用参考：

- Unitree Go2 公开 ROS / SDK 示例显示了 `body_height = 0.32`、`foot_raise_height = 0.09` 一类的实时 motion-state 参考值。
- `Unitree-Go2-Robot/go2_robot` 的 Go2 资料页公开了 `BodyHeight`, `FootRaiseHeight`, `SpeedLevel`, `SwitchGait` 的有效范围，其中 `BodyHeight` 约在 `0.3 ~ 0.5`，`SpeedLevel` 约在 `-1 ~ 1`。

这说明 motion-mode baseline 可以做得更明确：把参数从“硬编码常量”提升成“可诊断的 profile”，并保持保守、可回退。

## Options Considered

### Option A: 只改注释和文档
最小风险，但不改变可执行基线。对“显式 motion mode 和参数”帮助有限。

### Option B: 推荐方案
扩展 `MotionModeProfile`，让 real-model startup 和 stair executor 都读取同一份 profile 元数据，并让 `go2w_stand_initializer` 支持显式 `--motion-mode`。同时把 stair 线速度默认值收敛到 profile 里。

优点：
- 保持边界在 `go2w_control` 和 opt-in real-model launch 内。
- 让 flat / stair 模式和启动站立参数显式可见。
- 仍然可以保留保守默认值和现有验收链。

### Option C: 直接接 SDK2 / 硬件控制链
这会越过当前 simulation-first 验收边界，也会把任务扩大成硬件接入和真实运动控制，不适合当前阶段。

## Chosen Approach
采用 Option B。

实现会以“保守、可诊断、可回退”为准则：

- `MotionModeProfile` 增加显式 motion metadata。
- `go2w_stand_initializer` 可以选择 motion mode，并打印 profile 摘要。
- `go2w_stair_executor` 默认 stair 线速度从 profile 读取，并保留显式 override。
- real-model launch 显式指定站立阶段使用 `legged` profile。
- verifier 和 docs 记录这些参数，而不把它们夸大成真实楼梯动力学。

## Task Card

### 1. Task Goal
把 `go2w_control` 的 motion-mode baseline 从隐式常量升级为显式 profile：支持 wheeled/legged profile 元数据、保守 stair 速度默认值、显式 startup stand motion mode，并把这些参数暴露给 real-model baseline verifier。

### 2. Current Phase
`Phase 4 accepted` 之后的 post-Phase-4 hardening。该任务不改变正式 phase label，也不声称真实楼梯动力学完成。

### 3. Allowed Files
- `go2w_control/go2w_control_runtime/motion_profiles.py`
- `go2w_control/go2w_control_runtime/stand_initializer.py`
- `go2w_control/go2w_control_runtime/stair_executor.py`
- `go2w_control/test/*`
- `go2w_control/CMakeLists.txt` 仅在新增测试时修改
- `go2w_control/scripts/*` 仅在入口参数变化时修改
- `go2w_sim/launch/sim_go2w_real.launch.py`
- `tools/verify_go2w_real_model_baseline.sh`
- `docs/verification/go2w_real_model_motion_mode_baseline.md`
- `docs/architecture/architecture_state.md`
- `docs/handoff/current_project_state.md`
- `docs/handoff/next_agent_notes.md`
- `docs/handoff/risk_cleanup_log.md`
- `README.md`

### 4. Forbidden Files
- `go2w_navigation/*`
- `go2w_mission/*`
- `go2w_perception/*`
- `go2w_description/*`
- `go2w_control/action/StairExec.action`
- `go2w_sim/config/controllers_go2w_real.yaml`，除非后续验证明确证明控制器限幅必须改

### 5. Required Commands
至少执行：

```bash
PYTHONPATH=go2w_control python3 -m pytest go2w_control/test/test_motion_profiles.py -q
PYTHONPATH=go2w_control python3 -m pytest go2w_control/test/test_stair_executor_policy.py -q
bash -n tools/verify_go2w_real_model_baseline.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_sim
colcon test --packages-select go2w_control go2w_sim
colcon test-result --verbose
./tools/verify_go2w_real_model_baseline.sh
```

### 6. Definition of Done
- `MotionModeProfile` 具备显式 motion metadata，并且有测试覆盖。
- `go2w_stand_initializer` 明确支持 motion-mode 选择并打印 profile 摘要。
- `go2w_stair_executor` 默认 stair 线速度来自 profile 的保守基线，可被显式 override。
- real-model launch 使用显式 motion mode，且 baseline verifier 记录了新的 motion-mode 事实。
- 文档只记录已验证事实，不把 motion-mode baseline 夸大成真实楼梯动力学。

## Design Notes
- 这里的 motion-mode tuning 只做“保守 baseline”而不是性能拉满。
- `body_height` / `foot_raise_height` / `gait_type` / `speed_level` 只作为 profile metadata 和启动诊断，不把它们冒充成硬件 SDK2 控制闭环。
- 若后续需要把这些值接入真正的 Unitree SDK2 或硬件控制链，必须单独拆任务。

## Self-Review
- 没有跨到 navigation 或 mission 层。
- 没有把 real-model baseline 改成默认路径。
- 没有承诺真实楼梯动力学。
- 任务范围足够小，可以单独验证、单独回退。
