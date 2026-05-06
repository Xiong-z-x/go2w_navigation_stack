# Phase 4 迁移前交接包索引

## 用途
本目录最初是进入 Phase 4A 新对话前的集中交接入口。Phase 4A 验收后，
它继续作为后续 Phase 4 工作的交接入口。它不替代架构事实源，只把当前仓库真实状态、
风险清理记录、阅读顺序和下一模型初始化信息集中起来。

2026-05-02 最终封板后，新对话应把
`docs/handoff/pre_migration_final_freeze_report.md` 作为 handoff 入口中的第一份
总览材料。该文件集中记录最终封板结论、可修风险处理结果、后续项目改进顺序和下一任务建议。

## 有效范围
- 初始迁移快照日期：2026-04-30
- 当前补充状态日期：2026-05-06
- 当前阶段：已验收 `Phase 4 accepted`
- 当前主线：ROS 2 Humble + Gazebo Fortress-only + FAST-LIO external cache
- 当前最终封板：`docs/handoff/pre_migration_final_freeze_report.md`
- 当前审计总览：`docs/handoff/project_state_audit.md`
- 下一任务边界：post-Phase-4 的最小单主题任务，必须另有完整任务单或当前自主审批模式下的自批准任务单

## 事实源优先级
实现或审计时按以下顺序判断事实：

1. `docs/architecture/system_blueprint.md`
2. `docs/architecture/interface_contracts.md`
3. `docs/architecture/architecture_state.md`
4. 当前完整任务单
5. 本目录下的交接材料
6. `README.md` 与历史验证记录

若这些文件冲突，先报告冲突，不要自行脑补。

## 推荐阅读顺序
1. `AGENTS.md`
2. `docs/handoff/README.md`
3. `docs/architecture/system_blueprint.md`
4. `docs/architecture/interface_contracts.md`
5. `docs/architecture/architecture_state.md`
6. `docs/handoff/pre_migration_final_freeze_report.md`
7. `docs/handoff/current_project_state.md`
8. `docs/handoff/project_state_audit.md`
9. `docs/handoff/phase4_migration_handoff_report.md`
10. `docs/handoff/risk_cleanup_log.md`
11. `docs/handoff/restart_lessons_for_next_model.md`
12. `docs/handoff/reading_order_and_file_map.md`
13. `docs/handoff/next_agent_notes.md`
14. `docs/verification/phase4a_stair_handoff_acceptance.md`
15. `docs/verification/phase4b_mission_segment_runtime.md`
16. `docs/verification/phase4c_flat_segment_gate.md`
17. `docs/verification/phase4d_route_tracking_feedback.md`
18. `docs/verification/phase5a_live_route_tracking.md`
19. `docs/verification/go2w_real_model_motion_mode_baseline.md`
20. `docs/verification/go2w_control_chain_regression.md`
21. `docs/verification/go2w_real_model_route_following.md`
22. `docs/verification/go2w_real_model_single_floor_hospital.md`
23. `docs/verification/go2w_real_model_route_tracking.md`
24. `docs/verification/go2w_mission_real_flat_execution.md`
25. `docs/verification/go2w_mission_real_flat_stair_flat.md`
26. `docs/verification/mission_api_scheduling_policy.md`
27. `docs/verification/mission_api_priority_scheduling.md`
28. `docs/verification/mission_api_assignment_policy.md`
29. `docs/verification/mission_api_orchestrator_control.md`
30. `docs/verification/mission_api_queue_replay.md`
31. `docs/verification/mission_api_task_history.md`
32. `docs/verification/mission_api_workflow_policy.md`
33. `docs/verification/mission_api_workflow_backend.md`
34. `docs/verification/phase4e_stair_fixture.md`
35. `docs/verification/phase4e_mission_recovery.md`
36. `docs/verification/go2w_real_model_regression.md`
37. `docs/verification/phase4e_stair_tuning_overrides.md`
38. `docs/verification/phase4e_stair_phase_targets.md`
39. `docs/verification/phase4e_stair_trajectory_outlet.md`
40. `docs/verification/phase4_runtime_acceptance.md`
41. `docs/handoff/new_model_initialization_prompt.md`

## 本目录文件职责
- `current_project_state.md`：当前真实状态总览。
- `project_state_audit.md`：阶段完成度审计、权威源映射、风险与差距分析。
- `risk_cleanup_log.md`：封板前风险识别、修复与剩余限制。
- `phase4_migration_handoff_report.md`：迁移前总报告。
- `pre_migration_final_freeze_report.md`：最终封板总自检、风险处理、后续路线和下一任务建议。
- `restart_lessons_for_next_model.md`：面向重新开新对话/新项目模型的易错点、误判来源和接手首检清单。
- `reading_order_and_file_map.md`：关键文件/目录阅读顺序与职责说明。
- `next_agent_notes.md`：给下一个模型的易错点和警示。
- `new_model_initialization_prompt.md`：可直接复制到新会话的初始化提示词。

## 验证入口
交接包一致性可用以下命令检查：

```bash
./tools/verify_phase4_pre_handoff.sh
```

Phase 4A runtime handoff 验收可用以下命令复现：

```bash
./tools/verify_phase4a_stair_handoff.sh
```

Phase 4B-min mission segment runtime 验收可用以下命令复现：

```bash
./tools/verify_phase4b_mission_segments.sh
```

Phase 4C-min flat segment execution gate 验收可用以下命令复现：

```bash
./tools/verify_phase4c_flat_segment_gate.sh
```

Phase 4D-min route tracking feedback observation gate 验收可用以下命令复现：

```bash
./tools/verify_phase4d_route_tracking_feedback.sh
```

Phase 5A live route tracking observation gate 验收可用以下命令复现：

```bash
./tools/verify_phase5a_live_route_tracking.sh
```

Go2W real model / motion-mode opt-in baseline 验收可用以下命令复现：

```bash
./tools/verify_go2w_real_model_baseline.sh
```

稳定 Go2W real-model control-chain regression 验收可用以下命令复现：

```bash
./tools/verify_go2w_control_chain_regression.sh
```

该 wrapper 是当前迁移前更稳健的 real-model 控制链门禁；它刻意不包含
same-floor route-following smoke。

Go2W real model same-floor route-following 独立 smoke 可用以下命令复现：

```bash
./tools/verify_go2w_real_model_route_following.sh
```

该 verifier 已完成 dedicated hardening，并取得 3 次 clean-domain 连续 PASS；
它是 opt-in regression 候选，但仍不是 production route tracking、不是默认
placeholder 基线替代，也尚未自动纳入稳定 control-chain wrapper。

Go2W real model single-floor hospital gate 可用以下命令复现：

```bash
./tools/verify_go2w_real_model_single_floor_hospital.sh
```

该 wrapper 使用 official Go2W-derived real model、Phase 3C hospital world、
FAST-LIO `laser_map` 合同、same-floor Nav2 motion chain 和最小规划路径长度门，
证明在更正常的医院场景里可以完成单层 planning/control 闭环。它仍不是
`map -> odom`、production `nav2_route` 或跨楼层自治。

Go2W real model `nav2_route` robot-motion route-tracking gate 可用以下命令复现：

```bash
./tools/verify_go2w_real_model_route_tracking.sh
```

该 verifier 启动 opt-in real-model、perception、FAST-LIO、real-model Nav2 和真实
`route_server`，从当前 perception odom 生成短 odom-frame route graph，并用
`NavigateToPose` 真实运动触发 `ComputeAndTrackRoute` feedback。它证明 real-model
motion 可以驱动 route tracking feedback；它仍不是跨楼层真实闭环、真实 stair route
operation plugin、Phase 5 自动连接器或默认 baseline 替代。

Mission runtime real-model flat execution + route-tracking observation gate 可用以下命令复现：

```bash
./tools/verify_go2w_mission_real_flat_execution.sh
```

该 verifier 启动 real-model、perception、FAST-LIO、real-model Nav2 和 mission API，
并在 `launch_flat_nav_executor:=false` 下证明 `RunMission` flat-only segment 可调用
真实 `/navigate_to_pose`，同时在显式
`route_tracking_action:=/compute_and_track_route` 下观察 mission-side route feedback
edge `10`。它仍不是 production Mission Orchestrator、真实 stair route operation
plugin、production cross-floor route tracking 或跨楼层真实闭环。

Mission runtime real-model flat/stair/flat integration gate 可用以下命令复现：

```bash
./tools/verify_go2w_mission_real_flat_stair_flat.sh
```

该 verifier 启动 real-model、perception、FAST-LIO、real-model Nav2 和 mission API，
并在 `launch_flat_nav_executor:=false` 下验证 `RunMission`
`flat:10;stair:500:stair_a:F1->F2;flat:20`。flat segments 调用真实
`/navigate_to_pose`，stair segment 调用 dedicated `/stair_exec` skeleton，同时观察
mission-side route feedback edges `10` / `20`、stair phase sequence、command gate
owner/mode 切换、Nav2 motion 和 TF 边界。它仍不是 production Mission
Orchestrator、真实 stair route operation plugin、真实楼梯动力学、production
cross-floor route tracking 或跨楼层真实闭环。

Mission API bounded FIFO scheduling policy 可用以下命令复现：

```bash
./tools/verify_mission_api_scheduling_policy.sh
```

该 verifier 证明 `RunMission` 在 one-active-plus-one-queued 模式下可重复验证
queue-full reject 与 queued cancel；它仍不是完整 production Mission Orchestrator
或 assignment policy。

Mission API non-preemptive priority scheduling 可用以下命令复现：

```bash
./tools/verify_mission_api_priority_scheduling.sh
```

该 verifier 证明 `RunMission` 显式 `priority` 字段、active mission 非抢占、
queued mission 按 `priority DESC, ticket ASC` 激活，以及 queue replay /
task history / operator summary 的 priority 诊断；它仍不是 fleet-level task
assignment 或完整 production Mission Orchestrator。

Mission API assignment policy 可用以下命令复现：

```bash
./tools/verify_mission_api_assignment_policy.sh
```

该 verifier 证明 `RunMission` 显式 `assigned_robot_id` 字段、本地
`mission_robot_id` admission gate、非本机任务在入队前拒绝，以及 queue replay /
task history / status summary 的 assignment 诊断；它仍不是多机器人调度优化、
cross-robot goal transfer 或完整 production Mission Orchestrator。

Mission API operator control 可用以下命令复现：

```bash
./tools/verify_mission_api_orchestrator_control.sh
```

该 verifier 证明 `MissionControl` pause/resume/status/cancel_active 与
operator-state snapshot backend 可重复验证。

Mission API durable queue replay 可用以下命令复现：

```bash
./tools/verify_mission_api_queue_replay.sh
```

该 verifier 证明 outstanding queue records 会持久化为 replay ledger，restart
pending 状态会阻止新 mission admission，operator 可通过 `MissionControl replay_queue`
恢复 scheduler ticket order；它仍不是完整 production Mission Orchestrator。

Mission API bounded task history 可用以下命令复现：

```bash
./tools/verify_mission_api_task_history.sh
```

该 verifier 证明 terminal `RunMission` history 会持久化到 bounded JSON ledger，
`MissionControl history` 可查询摘要，`MissionControl archive_history` 可裁剪旧记录；
它仍不是多机器人调度优化、cross-robot goal transfer 或完整 production Mission Orchestrator。

Mission API workflow policy 可用以下命令复现：

```bash
./tools/verify_mission_api_workflow_policy.sh
```

该 verifier 证明 `MissionControl workflow` 可返回只读 workflow snapshot，并且
control `state_summary` 暴露 mode、mission activity、queue state、history state
和 available operator commands；它仍不是多机器人调度优化、cross-robot goal
transfer、active preemption 或完整 production Mission Orchestrator。

Mission API workflow backend 可用以下命令复现：

```bash
./tools/verify_mission_api_workflow_backend.sh
```

该 verifier 证明 bounded JSON workflow event ledger、mission lifecycle
`ADMIT` / `ACTIVE` / `COMPLETE` events，以及 `MissionControl workflow_events`
只读查询；它仍不是 fleet-level workflow engine、active preemption 或完整
production Mission Orchestrator。

Phase 4E real-model stair fixture 验收可用以下命令复现：

```bash
./tools/verify_phase4e_stair_fixture.sh
```

Phase 4E mission recovery 验收可用以下命令复现：

```bash
./tools/verify_phase4e_mission_recovery.sh
```

Go2W real-model opt-in regression 可用以下命令复现：

```bash
./tools/verify_go2w_real_model_regression.sh
```

该 wrapper 包含 route-following smoke，因此比 control-chain wrapper 更接近端到端
真实模型动作链，但也更容易受 DWB 局部规划状态影响；默认交接判断应优先使用
`verify_go2w_control_chain_regression.sh`。

Phase 4E stair tuning smoke test 可用以下命令复现：

```bash
./tools/verify_phase4e_stair_tuning_overrides.sh
```

Phase 4E stair phase target focused gate 可用以下命令复现：

```bash
./tools/verify_phase4e_stair_phase_targets.sh
```

该 verifier 证明 stair phase plan 的 `wheel_lock_required` 诊断和 opt-in
execute/body-height transition target；它仍不是硬件 wheel-lock、body-height actuator
或真实 stair gait。

Phase 4E stair trajectory outlet focused gate 可用以下命令复现：

```bash
./tools/verify_phase4e_stair_trajectory_outlet.sh
```

该 verifier 证明每个 stair phase 都生成 12 关节目标，并暴露标准
`trajectory_msgs/msg/JointTrajectory` 诊断/未来对接口；它仍不是 tuned gait、
hardware wheel-lock、body-height actuator 或物理楼梯动力学。

Phase 4 总体验收可用以下命令复现：

```bash
./tools/verify_phase4_runtime_acceptance.sh
```
