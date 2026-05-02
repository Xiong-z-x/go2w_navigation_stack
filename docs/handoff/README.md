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
- 当前补充状态日期：2026-05-02
- 当前阶段：已验收 `Phase 4 accepted`
- 当前主线：ROS 2 Humble + Gazebo Fortress-only + FAST-LIO external cache
- 当前最终封板：`docs/handoff/pre_migration_final_freeze_report.md`
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
7. `docs/handoff/phase4_migration_handoff_report.md`
8. `docs/handoff/current_project_state.md`
9. `docs/handoff/risk_cleanup_log.md`
10. `docs/handoff/reading_order_and_file_map.md`
11. `docs/handoff/next_agent_notes.md`
12. `docs/verification/phase4a_stair_handoff_acceptance.md`
13. `docs/verification/phase4b_mission_segment_runtime.md`
14. `docs/verification/phase4c_flat_segment_gate.md`
15. `docs/verification/phase4d_route_tracking_feedback.md`
16. `docs/verification/phase5a_live_route_tracking.md`
17. `docs/verification/go2w_real_model_motion_mode_baseline.md`
18. `docs/verification/go2w_control_chain_regression.md`
19. `docs/verification/go2w_real_model_route_following.md`
20. `docs/verification/go2w_mission_real_flat_execution.md`
21. `docs/verification/phase4e_stair_fixture.md`
22. `docs/verification/phase4e_mission_recovery.md`
23. `docs/verification/go2w_real_model_regression.md`
24. `docs/verification/phase4e_stair_tuning_overrides.md`
25. `docs/verification/phase4_runtime_acceptance.md`
26. `docs/handoff/new_model_initialization_prompt.md`

## 本目录文件职责
- `current_project_state.md`：当前真实状态总览。
- `risk_cleanup_log.md`：封板前风险识别、修复与剩余限制。
- `phase4_migration_handoff_report.md`：迁移前总报告。
- `pre_migration_final_freeze_report.md`：最终封板总自检、风险处理、后续路线和下一任务建议。
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

Mission runtime real-model flat execution gate 可用以下命令复现：

```bash
./tools/verify_go2w_mission_real_flat_execution.sh
```

该 verifier 启动 real-model、perception、FAST-LIO、real-model Nav2 和 mission API，
并在 `launch_flat_nav_executor:=false` 下证明 `RunMission` flat-only segment 可调用
真实 `/navigate_to_pose`。它仍不是 production Mission Orchestrator、真实 `nav2_route`
robot-motion route tracking 或跨楼层真实闭环。

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

Phase 4 总体验收可用以下命令复现：

```bash
./tools/verify_phase4_runtime_acceptance.sh
```
