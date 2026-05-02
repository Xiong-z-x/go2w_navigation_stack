# Phase 4E Follow-up Hardening Design

## Task Goal
在不改变现有冻结接口的前提下，补齐四个后续工程点：
1. real-model stair fixture 中 `/stair_exec` 的可诊断动作闭环；
2. leg trajectory / wheel lock / body height transition 的楼梯控制策略骨架；
3. production mission recovery、状态持久化和长任务调度骨架；
4. real-model 路径是否扩展为更大范围 regression 的明确结论。

这次工作仍然不把真实楼梯动力学、SDK2 硬件控制、AMCL、`map_server`、elevation mapping、traversability 或自动楼梯连接器混进来。

## Current Phase
Phase 4 accepted 之后的后续硬化阶段，仍然以现有仓库中的 simulation-first / opt-in real-model 事实为准。

## Allowed Files
- `go2w_control/go2w_control_runtime/*`
- `go2w_control/test/*`
- `go2w_control/CMakeLists.txt`
- `go2w_control/package.xml`
- `go2w_control/scripts/*`
- `go2w_mission/go2w_mission/*`
- `go2w_mission/test/*`
- `go2w_mission/CMakeLists.txt`
- `go2w_mission/package.xml`
- `go2w_mission/scripts/*`
- `go2w_mission/launch/*`
- `tools/verify_*.sh`
- `docs/verification/*`
- `docs/architecture/architecture_state.md`
- `docs/handoff/current_project_state.md`
- `docs/handoff/next_agent_notes.md`
- `docs/handoff/risk_cleanup_log.md`
- `README.md`

## Forbidden Files
- `go2w_description/*`
- `go2w_sim/*` 除非 verifier 需要复用现有 real-model 启动入口
- `go2w_perception/*`
- `go2w_navigation/*`
- `go2w_control/action/StairExec.action`
- `go2w_mission/action/RunMission.action`
- `go2w_control` / `go2w_mission` 冻结接口之外的跨包 TF authority 改动

## Required Commands
- `PYTHONPATH=go2w_control python3 -m pytest go2w_control/test -q`
- `PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test -q`
- `bash -n tools/verify_go2w_real_model_regression.sh`
- `bash -n tools/verify_phase4e_stair_fixture.sh`
- `bash -n tools/verify_phase4e_mission_recovery.sh`
- `source /opt/ros/humble/setup.bash && colcon build --symlink-install --packages-select go2w_control go2w_mission`
- `source /opt/ros/humble/setup.bash && colcon test --packages-select go2w_control go2w_mission`
- `source /opt/ros/humble/setup.bash && colcon test-result --verbose`

## Definition of Done
- `/stair_exec` 仍然是 dedicated Action，但 stair executor 能输出可诊断的阶段序列和恢复友好的状态。
- stair 控制策略明确表达 wheel lock、body height transition、leg hold / trajectory 骨架，且其输出能被 verifier 观察。
- mission API 具备持久化 checkpoint、恢复同一 mission goal 的能力和可诊断的排队 / 忙碌 / 恢复路径。
- real-model 路径没有被提升成默认基线；它被纳入更大的 opt-in regression，而不是静默替换旧默认。
- 文档只记录已验证事实，不把 skeleton 夸大成真实楼梯动力学或 production autonomy。

## Design

### Stair Fixture and Control Strategy
`go2w_control` 保持最终 locomotion owner 和 `/stair_exec` 实现权，但把 stair executor 从“单一循环发布”提升为“阶段化闭环骨架”：
- `prepare`
- `wheel_lock`
- `body_height_transition_down`
- `execute_stairs`
- `body_height_transition_up`
- `release`

这些阶段不冒充真实硬件控制闭环；它们是可诊断的控制策略骨架。当前仓库里没有独立的 body-height 控制接口，因此 body height transition 通过阶段状态、日志和 profile 元数据表达，而不是伪造不存在的控制通道。`leg_position_controller` 仍然只接收保守 leg hold command，`stair_cmd_vel` 仍然只接收受 profile 限制的 stair 速度。

### Mission Recovery and Scheduling
`go2w_mission` 在现有 `RunMission` Action skeleton 上增加持久化 state journal：
- 记录 mission key、当前阶段、已完成 segment、下一 segment 索引、最近一次结果码和更新时间；
- 对同一 mission goal 的恢复请求，允许从 checkpoint 继续；
- 对 flat / stair 的瞬时不可用和超时路径做有限重试；
- 对 busy / cancel / terminal failure 做可诊断返回。

恢复不是“无限自动重放”。它只是把任务从一次性 skeleton 提升到可恢复的长任务状态机，并把恢复边界写到状态文件里。

### Real-Model Regression Policy
real-model 路径不改成默认基线。理由是当前证据只覆盖：
- 真实模型与 motion-mode baseline；
- 短同层 `NavigateToPose` route-following；
- stair skeleton 的控制权交接闭环。

这些证据不足以证明应当把 placeholder 仿真默认路径整体切换为 real-model default。更稳妥的做法是新增一个 opt-in regression wrapper，把 baseline 和 route-following 以及 stair fixture 一起纳入可重复回归，但保留旧默认路径不动。

## Self-Review
- 没有把真实楼梯动力学、SDK2 硬件接入或 AMCL/map_server 偷渡进来。
- stair / mission / regression 三个子问题边界清楚，且都能单独验证。
- 默认基线不翻转，和现有 accepted facts 保持一致。
