# 关键文件/目录阅读顺序与说明

实际项目仓库根是 `/home/xiongzx/go2w_ws/src/go2w_navigation_stack`。外层
`/home/xiongzx/go2w_ws` 是 ROS workspace；运行 git、colcon 或 verifier 前应先进入实际仓库根。

## 第一层：必须先读的事实源
1. `AGENTS.md`：项目身份、阶段纪律、协作规则、任务单格式。
2. `docs/architecture/system_blueprint.md`：全生命周期路线和阶段验收目标。
3. `docs/architecture/interface_contracts.md`：跨层接口、TF、Action、route/mission 契约。
4. `docs/architecture/architecture_state.md`：当前阶段、当前真实状态、唯一下一步边界。

## 第二层：迁移前状态与风险
1. `docs/handoff/pre_migration_final_freeze_report.md`：最终封板总自检、风险处理、后续路线和下一任务建议。
2. `docs/handoff/current_project_state.md`：当前状态总览。
3. `docs/handoff/project_state_audit.md`：阶段完成度审计、权威源映射、风险与最终目标差距分析。
4. `docs/handoff/phase4_migration_handoff_report.md`：迁移前总报告。
5. `docs/handoff/risk_cleanup_log.md`：已修风险与剩余限制。
6. `docs/handoff/next_agent_notes.md`：新模型最容易踩的坑。

## 第三层：运行和验收记录
- `README.md`：操作入口和当前状态摘要，不是架构事实源。
- `docs/verification/phase1_runtime_acceptance.md`：Phase 1 运行闭环证据。
- `docs/verification/phase2_runtime_acceptance.md`：Phase 2 总体验收。
- `docs/verification/phase3_runtime_acceptance.md`：Phase 3 总体验收。
- `docs/verification/phase3c_hardening_acceptance.md`：Phase 3C 硬化证据。
- `docs/verification/phase4a_stair_handoff_acceptance.md`：Phase 4A 最小楼梯 handoff 骨架验收。
- `docs/verification/phase4b_mission_segment_runtime.md`：Phase 4B-min 最小 mission segment runtime 验收。
- `docs/verification/phase4c_flat_segment_gate.md`：Phase 4C-min 最小 flat/stair/flat execution gate 验收。
- `docs/verification/phase4d_route_tracking_feedback.md`：Phase 4D-min 最小 route tracking feedback observation gate 验收。
- `docs/verification/phase4e_stair_fixture.md`：Phase 4E real-model `/stair_exec` phase-aware fixture 验收。
- `docs/verification/phase4e_mission_recovery.md`：Phase 4E mission checkpoint/recovery 验收。
- `docs/verification/go2w_control_chain_regression.md`：稳定 real-model control-chain regression wrapper 验收。
- `docs/verification/go2w_real_model_route_following.md`：Go2W real-model same-floor route-following dedicated hardening 证据；现在是 opt-in regression 候选，不是 production route tracking。
- `docs/verification/go2w_mission_real_flat_execution.md`：Mission runtime real-model flat execution gate 证据；证明 `RunMission` flat-only segment 可绕过 verifier-only flat executor 并调用真实 Nav2 `/navigate_to_pose`。
- `docs/verification/mission_api_scheduling_policy.md`：Mission API bounded FIFO scheduling policy 证据；证明 `RunMission` 可重复验证 queue-full reject 与 queued cancel。
- `docs/verification/mission_api_priority_scheduling.md`：Mission API non-preemptive priority scheduling 证据；证明 queued mission 按 `priority DESC, ticket ASC` 激活且同 priority 保持 FIFO。
- `docs/verification/mission_api_assignment_policy.md`：Mission API assignment policy 证据；证明 `RunMission` 显式 `assigned_robot_id`、本机 admission gate 和 assignment diagnostics。
- `docs/verification/mission_api_orchestrator_control.md`：Mission API operator control 证据；证明 pause/resume/status/cancel_active 与 operator-state snapshot backend。
- `docs/verification/mission_api_queue_replay.md`：Mission API durable queue replay 证据；证明 replay ledger、replay-pending admission gate 与 `MissionControl replay_queue`。
- `docs/verification/mission_api_task_history.md`：Mission API task-history 证据；证明 terminal mission history ledger、`MissionControl history/archive_history` 和 bounded retention。
- `docs/verification/mission_api_workflow_policy.md`：Mission API workflow policy 证据；证明 `MissionControl workflow` 只读查询和 workflow snapshot 摘要。
- `docs/verification/mission_api_workflow_backend.md`：Mission API workflow backend 证据；证明 bounded workflow event ledger 和 `MissionControl workflow_events` 查询。
- `docs/verification/go2w_real_model_regression.md`：Go2W real-model opt-in regression wrapper 验收；包含 route-following smoke，因此比 control-chain wrapper 更 route-state-sensitive。
- `docs/verification/phase4e_stair_tuning_overrides.md`：Phase 4E stair tuning smoke test 验收。
- `docs/verification/phase4_runtime_acceptance.md`：Phase 4 总体验收。
- `docs/verification/gazebo_gpu_rebaseline.md`：Gazebo GPU 降级原因。

## 第四层：历史任务记录
- `docs/superpowers/specs/`：历史设计记录。
- `docs/superpowers/plans/`：历史执行计划。

这些文件可用于追溯为什么这么做，但不应覆盖当前 `architecture_state.md`。
早期文件中的 `/tmp` FAST-LIO 路径可能只是历史证据，不代表当前默认。
如果历史计划与当前 handoff 或 verification 文档冲突，以当前架构事实源和当前脚本为准；
不要直接从历史计划复制路径、命令或阶段结论。

## 核心代码目录
- `go2w_description/`：URDF、RViz、robot state publisher launch。
- `go2w_sim/`：Gazebo worlds、simulation launch、controller config。
- `go2w_perception/`：FAST-LIO adapters、TF authority、patch、external lock。
- `go2w_navigation/`：Nav2 configs、BT、route graph、maps、Phase 4C-min flat navigation executor skeleton、Phase 4D-min route tracking feedback executor skeleton。
- `go2w_control/`：Phase 4A 起承载 `StairExec` Action、command gate 和最小 stair executor skeleton；Phase 4E 起输出 phase-aware stair execution plan/state。
- `go2w_mission/`：Phase 4A 起承载 handoff demo；Phase 4B-min 起承载 one-shot mission segment runtime；Phase 4C-min 起通过 `NavigateToPose` gate 调度 flat segments；Phase 4D-min 起承载 route tracking feedback observer；Phase 4E 起提供 mission checkpoint/recovery skeleton；当前已能在 opt-in flat-only gate 中调用真实 Nav2 `/navigate_to_pose`，并且现在还具备 bounded queueing、non-preemptive priority scheduling、local assignment policy、operator control、durable queue replay、bounded terminal task history、workflow policy snapshot 和 workflow event backend，但尚不是完整 production Mission Orchestrator。

## 关键工具
- `tools/prepare_phase2d_fastlio_external.sh`：准备 pinned FAST-LIO external cache。
- `tools/verify_phase2d_fastlio_no_tf_dryrun.sh`：FAST-LIO no-TF runtime gate。
- `tools/verify_phase2e_fastlio_contract.sh`：FAST-LIO input/output contract gate。
- `tools/verify_phase2f_tf_authority.sh`：perception TF authority gate。
- `tools/verify_phase2g_perception_stability.sh`：perception stability gate。
- `tools/verify_phase2h_costmap_consumer.sh`：Nav2 costmap consumer gate。
- `tools/verify_phase3a_nav2_same_floor.sh`：Nav2 同层闭环 gate。
- `tools/verify_phase3b_route_graph.sh`：same-floor route graph gate。
- `tools/verify_phase3c_multifloor_route_graph.sh`：multi-floor route graph asset gate。
- `tools/verify_phase3c_hospital_world.sh`：hospital world asset gate。
- `tools/verify_phase4_pre_handoff.sh`：迁移前交接一致性 gate。
- `tools/verify_phase4a_stair_handoff.sh`：Phase 4A staircase handoff runtime gate。
- `tools/verify_phase4b_mission_segments.sh`：Phase 4B-min mission segment runtime gate。
- `tools/verify_phase4c_flat_segment_gate.sh`：Phase 4C-min flat/stair/flat execution gate。
- `tools/verify_phase4d_route_tracking_feedback.sh`：Phase 4D-min route tracking feedback observation gate。
- `tools/verify_phase4e_stair_fixture.sh`：Phase 4E real-model stair fixture gate。
- `tools/verify_phase4e_mission_recovery.sh`：Phase 4E mission checkpoint/recovery gate。
- `tools/verify_go2w_control_chain_regression.sh`：稳定 real-model control-chain regression gate。
- `tools/verify_go2w_real_model_route_following.sh`：Go2W real-model same-floor route-following verifier；验证短 `NavigateToPose` 运动链。
- `tools/verify_go2w_mission_real_flat_execution.sh`：Mission runtime real-model flat execution gate；验证 `RunMission` flat-only segment 调用真实 Nav2 `/navigate_to_pose`，且不启动 `go2w_flat_nav_executor`。
- `tools/verify_mission_api_scheduling_policy.sh`：Mission API bounded FIFO scheduling policy gate；验证 `RunMission` queue-full reject 与 queued cancel。
- `tools/verify_mission_api_priority_scheduling.sh`：Mission API priority scheduling gate；验证 `RunMission` 显式 priority、queued priority order 和同 priority FIFO。
- `tools/verify_mission_api_assignment_policy.sh`：Mission API assignment policy gate；验证 `RunMission` 显式 assigned robot、本机 admission gate 和 assignment diagnostics。
- `tools/verify_mission_api_orchestrator_control.sh`：Mission API operator control gate；验证 operator-state snapshot、pause/resume/status/cancel_active。
- `tools/verify_mission_api_queue_replay.sh`：Mission API durable queue replay gate；验证 replay ledger 和 `MissionControl replay_queue`。
- `tools/verify_mission_api_task_history.sh`：Mission API task-history gate；验证 terminal history ledger、`MissionControl history/archive_history` 和 bounded retention。
- `tools/verify_mission_api_workflow_policy.sh`：Mission API workflow policy gate；验证 workflow snapshot 和 `MissionControl workflow`。
- `tools/verify_mission_api_workflow_backend.sh`：Mission API workflow backend gate；验证 workflow event ledger 和 `MissionControl workflow_events`。
- `tools/verify_go2w_real_model_regression.sh`：Go2W real-model opt-in regression gate。
- `tools/verify_phase4e_stair_tuning_overrides.sh`：Phase 4E stair tuning smoke test gate。
- `tools/verify_phase4_runtime_acceptance.sh`：Phase 4 总体验收 gate。

## 生成/缓存目录
- `.go2w_external/`：ignored FAST-LIO external source/workspace cache。
- `build/`、`install/`、`log/`：colcon 生成目录。
- `.pytest_cache/`、`__pycache__/`：本地缓存，不是项目事实源。
- `task_plan.md`、`findings.md`、`progress.md`：本地 agent 会话工作记忆，已在 `.gitignore`
  中忽略，不是正式交接事实源。
