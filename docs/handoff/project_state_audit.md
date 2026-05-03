# 项目状态事实审计

## 审计结论
- 当前正式阶段仍是 `Phase 4 accepted`，但仓库已经补上多个 post-Phase-4 hardening gate。
- 当前最可信的事实源仍是 `docs/architecture/system_blueprint.md`、`docs/architecture/interface_contracts.md` 和 `docs/architecture/architecture_state.md`。
- 当前没有证据表明完整 production Mission Orchestrator、真实机器人运动上的稳定 `nav2_route` route tracking、真实楼梯动力学、`map_server` / AMCL / `map -> odom`、elevation mapping、traversability 或 automatic connector generation 已完成。
- production Mission Orchestrator 的当前窄范围已完成到 bounded FIFO queueing、operator control service 与 operator-triggered durable queue replay；共享 flat pose helper、bounded FIFO queueing、mission real-flat runtime gate、operator-state snapshot 和 queue replay ledger 均有 fresh evidence。它仍不等于完整 production Mission Orchestrator。
- 阶段结论必须由代码、配置、脚本、测试和 runtime evidence 交叉验证，不允许只看计划、注释或旧日志。

## 状态判定规则
本仓库统一使用四种状态：

| 状态 | 含义 |
| --- | --- |
| `已完成` | 有代码 / 配置 / 脚本 / 测试 / runtime evidence 交叉验证，且文档口径一致。 |
| `部分完成` | 已有可运行能力，但还没有覆盖最终目标所需的完整范围，或明确保留为 opt-in / candidate。 |
| `未完成` | 目标能力尚未落地，或只有骨架、占位、计划，没有可重复验证的闭环。 |
| `无法确认` | 证据不足，不能靠印象下结论；必须先补最小可信验证。 |

判定规则：
- 计划、TODO、注释、README 摘要和旧日志都不能单独当作完成证据。
- 文档与代码冲突时，以可运行验证和当前源码为准，并同步修正文档。
- 历史材料只允许作为背景，不允许覆盖当前事实源。

## 权威信息源映射
| 类别 | 权威文件 | 作用 |
| --- | --- | --- |
| 项目目标与边界 | `docs/architecture/system_blueprint.md` | 定义系统分层、阶段路线和验收方向。 |
| 冻结接口 | `docs/architecture/interface_contracts.md` | 冻结 TF、Action、route / mission / stair 契约。 |
| 当前状态事实源 | `docs/architecture/architecture_state.md` | 记录当前 active phase、已完成能力和未完成项。 |
| 当前状态总览 | `docs/handoff/current_project_state.md` | 面向接手者的状态摘要。 |
| 详细审计与差距分析 | `docs/handoff/project_state_audit.md` | 本文件，汇总阶段完成度、风险和下一步建议。 |
| 风险与剩余限制 | `docs/handoff/risk_cleanup_log.md` | 记录已修风险、残余风险和保留限制。 |
| 接手说明 | `docs/handoff/README.md`、`docs/handoff/next_agent_notes.md` | 说明阅读顺序、易错点和下一模型警示。 |
| 运行和验收证据 | `docs/verification/*` | 提供可复现的 runtime / test 证据。 |
| 操作摘要 | `README.md` | 便于人类快速浏览，但不是事实源。 |
| 历史计划与总结 | `docs/superpowers/*`、`task_plan.md`、`findings.md`、`progress.md` | 仅作历史或本地会话记忆，不覆盖当前事实。 |

## 阶段完成度审计
| 范围 | 关键技术点 | 判定 | 证据链 | 备注 |
| --- | --- | --- | --- | --- |
| Phase 0 | 接口契约冻结、TF 最小链、包职责边界 | 已完成 | `docs/architecture/system_blueprint.md`、`docs/architecture/interface_contracts.md`、`docs/architecture/architecture_state.md` | 这是整个仓库的冻结边界。 |
| Phase 1 | Gazebo + `gz_ros2_control` + `/cmd_vel` 闭环 | 已完成 | `docs/verification/phase1_runtime_acceptance.md`、`tools/verify_phase1_runtime.sh`、`README.md` | 证明仿真可控、可观测。 |
| Phase 2 | FAST-LIO 输入输出、perception-owned `odom -> base_link`、Nav2 costmap consumer gate | 已完成 | `docs/verification/phase2_runtime_acceptance.md`、`docs/verification/phase2_*` | 这是后续 Nav2 和 mission 的定位基础。 |
| Phase 3A | 最小同层 Nav2 planner/controller/BT 闭环 | 已完成 | `docs/verification/phase3a_nav2_same_floor.md`、`docs/verification/phase3_runtime_acceptance.md` | 只证明同层导航，不等于跨楼层。 |
| Phase 3B | 手工 route graph baseline / `nav2_route` baseline | 已完成 | `docs/verification/phase3b_route_graph_baseline.md`、`docs/verification/phase3_runtime_acceptance.md` | 仍是二维手工图。 |
| Phase 3C | FAST-LIO repo-local cache、多楼层 route graph、hospital world asset | 已完成 | `docs/verification/phase3c_hardening_acceptance.md` | 是 Phase 4 的资产准备，不是跨楼层自治。 |
| Phase 4A | staircase connector detection、`/stair_exec` Action skeleton、控制权互斥 | 已完成 | `docs/verification/phase4a_stair_handoff_acceptance.md` | 这是行为交接骨架，不是物理爬楼控制器。 |
| Phase 4B-min | mission-side route segmentation 与 stair dispatch | 已完成 | `docs/verification/phase4b_mission_segment_runtime.md` | 证明 mission 层能分段和调度。 |
| Phase 4C-min | flat/stair/flat execution gate | 已完成 | `docs/verification/phase4c_flat_segment_gate.md` | flat 段经 `NavigateToPose` verifier gate，stair 段经 `/stair_exec`。 |
| Phase 4D-min | `ComputeAndTrackRoute` feedback observation gate | 已完成 | `docs/verification/phase4d_route_tracking_feedback.md` | 只是 observation gate，不是机器人实运动 tracking。 |
| Phase 4 accepted | 预交接、Phase 4A/4B/4C/4D、build/test、test-result 聚合验收 | 已完成 | `docs/verification/phase4_runtime_acceptance.md`、`tools/verify_phase4_runtime_acceptance.sh` | 当前正式阶段标签。 |
| Phase 5A | live route tracking observation gate | 已完成 | `docs/verification/phase5a_live_route_tracking.md`、`tools/verify_phase5a_live_route_tracking.sh` | 观察到真实 `nav2_route` route_server 和反馈，不等于实车 tracking。 |
| Post-Phase-4 real-model baseline | 真实 Go2W 模型、四 foot wheel controller、leg controller、站立初始化 | 已完成 | `docs/verification/go2w_real_model_motion_mode_baseline.md`、`tools/verify_go2w_real_model_baseline.sh` | 这是 opt-in 基线，不是默认仿真替换。 |
| Post-Phase-4 real-model route-following | 短 `NavigateToPose` 同层 smoke + dedicated hardening | 已完成 | `docs/verification/go2w_real_model_route_following.md`、`tools/verify_go2w_real_model_route_following.sh` | 这是 opt-in regression candidate，不是 production route tracking。 |
| Post-Phase-4 mission flat execution | `RunMission` flat-only segment 接真实 Nav2 `/navigate_to_pose` | 已完成 | `docs/verification/go2w_mission_real_flat_execution.md`、`tools/verify_go2w_mission_real_flat_execution.sh` | 证明 mission flat gate 可绕过 verifier-only flat executor。 |
| Post-Phase-4 mission scheduling policy | `RunMission` bounded FIFO queueing、queue-full reject、queued cancel | 已完成 | `docs/verification/mission_api_scheduling_policy.md`、`tools/verify_mission_api_scheduling_policy.sh` | 仍不是 priority scheduling。 |
| Post-Phase-4 mission operator control | `MissionControl` pause/resume/status/cancel_active、operator-state snapshot | 已完成 | `docs/verification/mission_api_orchestrator_control.md`、`tools/verify_mission_api_orchestrator_control.sh` | 仍不是 priority scheduling 或完整长期任务管理。 |
| Post-Phase-4 mission queue replay | outstanding queue record ledger、replay-pending admission gate、`MissionControl replay_queue` | 已完成 | `docs/verification/mission_api_queue_replay.md`、`tools/verify_mission_api_queue_replay.sh` | 是 operator-triggered queue replay，不是 action goal-handle resurrection 或 priority scheduling。 |
| Phase 4E stair fixture | phase-aware `/stair_exec` fixture、wheel lock、body height transition、leg hold/release | 已完成 | `docs/verification/phase4e_stair_fixture.md`、`tools/verify_phase4e_stair_fixture.sh` | 仍是 control skeleton，不是实机楼梯动力学。 |
| Phase 4E mission recovery | JSON checkpoint、same-goal resume、有限 retry | 已完成 | `docs/verification/phase4e_mission_recovery.md`、`tools/verify_phase4e_mission_recovery.sh` | 是 production-style recovery skeleton，不是完整调度器。 |
| Stable control-chain regression wrapper | real-model baseline + stair fixture + mission recovery + stair tuning smoke | 已完成 | `docs/verification/go2w_control_chain_regression.md`、`tools/verify_go2w_control_chain_regression.sh` | 保持 conservative 门禁，不包含 route-following smoke。 |
| Opt-in real-model regression wrapper | real-model baseline + route-following + stair fixture | 已完成 | `docs/verification/go2w_real_model_regression.md`、`tools/verify_go2w_real_model_regression.sh` | 比 control-chain wrapper 更 route-state-sensitive，不能替代默认基线。 |

## 已解决事项
- FAST-LIO 默认路径漂移到 `.go2w_external/`，不再依赖旧 `/tmp` 默认。
- Phase 4 迁移前交接包已集中化，新的接手入口不再散落在历史计划里。
- Phase 4A / 4B / 4C / 4D / 4 runtime gates 都已经形成可重复验证链。
- 真实 Go2W 模型、motion-mode baseline、route-following smoke、mission real flat gate、Phase 4E stair fixture 和 mission recovery 都已经补齐。
- Mission API 并发 goal 的 bounded FIFO scheduling policy 已经接入，one-active-plus-one-queued 时可返回 `MISSION_BUSY` / `mission_queue_full` 或 `MISSION_CANCELED` / `mission_queue_canceled`；控制面还额外提供 `MissionControl` pause/resume/status/cancel_active/replay_queue，避免两个 `RunMission` 同时竞争同一个 JSON state file，并新增 operator-triggered durable queue replay ledger。
- Mission flat goal 的姿态转换已统一到共享 `mission_pose` helper，mission API 和 Phase 4B runtime 不再在 yaw 处理上分叉。
- Mission real flat gate 之前的 yaw 丢失问题已经修复，并回写到 `docs/verification/go2w_mission_real_flat_execution.md`。
- Production Mission Orchestrator scheduling / control / queue replay 的当前窄范围已完成：`mission_api.py` 和 `phase4b_mission_runtime.py` 共用 `mission_pose`，bounded FIFO queueing 有 focused unit test，`MissionControl` 控制面有 focused unit test，queue replay ledger 有 focused unit test 和 `tools/verify_mission_api_queue_replay.sh`，`tools/verify_go2w_mission_real_flat_execution.sh` 在 clean-domain rerun 中通过。

## 未解决事项
- 生产级 Mission Orchestrator 仍未完成，但 bounded FIFO queueing、operator control service 和 operator-triggered durable queue replay 已经落地。
- 真实机器人运动上的稳定 `nav2_route` route tracking 仍未完成。
- 真实楼梯动力学、gait tuning、wheel lock/body-height 的物理控制仍未完成。
- 默认仿真基线切换到 real-model 仍未批准。
- `map_server` / AMCL / `map -> odom` 定位链仍未实现。
- elevation mapping、traversability、automatic stair detection / connector generation 仍未实现。

## 风险
| 风险 | 影响范围 | 当前证据 | 修复状态 | 建议 |
| --- | --- | --- | --- | --- |
| 阶段完成度被误报 | 所有阶段结论 | 旧计划、README 摘要、TODO 和旧日志都容易被误读成 current fact | 已修复一部分：新增本审计文档并抽出四态规则 | 后续所有阶段审计都必须引用 code / script / test / runtime evidence。 |
| 文档与代码脱节 | 所有 handoff / README / verification 文档 | 当前已经存在大量摘要性文档，若不做权威源映射就容易互相覆盖 | 持续治理 | 继续以 `architecture_state.md` 为当前事实源，并把历史与当前明显分层。 |
| 旧日志或历史计划冒充当前事实 | 新对话接手 | `docs/superpowers/*`、`task_plan.md`、`findings.md`、`progress.md` 都会混入过时上下文 | 已控制 | 明确历史记录只作背景，不作完成证据。 |
| opt-in real-model gate 被误当默认基线 | 真实模型、Nav2、mission 路径 | `go2w_real_model_regression.sh` 和 `go2w_mission_real_flat_execution.sh` 都不是默认 placeholder 路径 | 已在文档中明确 | 不要把 opt-in 证据误写成默认验收合同。 |
| verifier skeleton 被误当 production | mission / navigation / control | 4C / 4D / 4E 都有明确 skeleton 或 observation 语义 | 持续存在 | 继续保留 deterministic verifier 路径，不要直接删骨架。 |

## 距离最终目标差距分析
当前最终目标仍清晰：Go2W 跨楼层自主导航巡检系统，simulation-first，先闭环再升维。

现有基础：
- 仿真可控闭环已经存在。
- FAST-LIO、perception TF authority、Nav2、route graph、楼梯 handoff、mission segmentation 和 mission recovery skeleton 都已经在仓库内闭环。
- 真实 Go2W 模型、real-model baseline、route-following smoke、mission real flat gate 和 Phase 4E stair fixture 都已经补齐。

仍缺的关键能力：
- production Mission Orchestrator。
- 真实机器人运动上的稳定 route tracking。
- 实际楼梯动力学 / gait tuning。
- 真实 `map_server` / AMCL / `map -> odom` 定位链。
- elevation / traversability / automatic connector generation。

缺口分类：
- 实现缺口：production Mission Orchestrator、真实楼梯控制、定位链、Phase 5 terrain-aware 自动连接器。
- 验证缺口：真实机器人运动上的稳定 route tracking、真实楼梯动力学。
- 文档 / 认知缺口：如果把 opt-in gate、verifier skeleton、observation gate 误当成 production，就会继续漂移。
- 环境 / 依赖缺口：real-model 仍是 opt-in，Gazebo GPU 也仍不是接受合同。

最值得优先推进的 3 个问题：
1. Production Mission Orchestrator remaining slice：只补 priority scheduling 或长期任务管理中的一个最小闭环。
2. 真实楼梯控制和 gait / body-height / wheel-lock 调参，但必须单独成题，不和 mission 调度混在一起。
3. 真实 `nav2_route` robot-motion route tracking 的独立验证和门禁化。

如果这三个问题不先收口，后续继续扩功能只会放大误判。

## 下一步建议
1. 下一步进入 production Mission Orchestrator remaining slice 的独立任务，仍然只做一个最小闭环，不要扩成完整长期调度系统。
2. 同步维持 current_project_state、risk_cleanup_log、next_agent_notes、architecture_state 和本审计文档的口径一致。
3. 后续每次阶段审计都先输出四态判定，再决定是否写代码。
