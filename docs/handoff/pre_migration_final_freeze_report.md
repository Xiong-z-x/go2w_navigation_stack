# 迁移前最终封板与后续路线交接报告

## 用途
本文记录 2026-05-02 的迁移前最终封板审计结果。它面向下一个新对话模型，
用于快速判断当前项目真实状态、剩余风险、后续项目改进顺序和不可误判边界。

本文不替代架构事实源。实现决策仍按以下顺序判断：

1. `docs/architecture/system_blueprint.md`
2. `docs/architecture/interface_contracts.md`
3. `docs/architecture/architecture_state.md`
4. 当前完整任务单或自批准任务单
5. `docs/handoff/*`
6. `README.md` 与历史验证记录

## 后续状态更新
- 2026-05-04：production Mission Orchestrator 的当前窄范围已推进到 bounded FIFO
  queueing、operator control service 与 operator-triggered durable queue replay。已固化共享 `go2w_mission.mission_pose`
  flat pose conversion、bounded FIFO queueing、queue-full / queued-cancel diagnostics、
  operator-state snapshot、queue replay ledger 以及 mission real-model flat execution fresh runtime 复验。
- 本文下方的“下一任务建议自批准任务单”保留为历史执行入口。后续新的最小任务应转向
  production Mission Orchestrator remaining slice，例如 priority scheduling 或长期任务管理中的一个单主题闭环。

## 总自检结论
- 项目总目标未漂移：仍是 simulation-first 的 Go2W 跨楼层自主导航巡检系统。
- 当前正式状态可信：`Phase 4 accepted`，并已有 Phase 5A、real-model baseline、
  Phase 4E stair fixture、mission recovery、stair tuning smoke 和 stable
  control-chain regression 的后续硬化证据。
- 当前技术路线自洽：`nav2_route` 做 route graph / route tracking，Mission 层做楼层语义和调度，
  Control 层通过 dedicated `/stair_exec` Action 接管楼梯行为。
- 当前核心环境仍是 ROS 2 Humble + Gazebo Fortress-only + WSL2 软件渲染 baseline；
  Harmonic/Garden/Gazebo GPU rendering 仍不属于验收合同。
- 2026-05-02 后续执行已完成第一项项目改进：real-model same-floor Nav2
  route-following 的 DWB abort 风险已复现、修复并通过 3 次 clean-domain 连续验证。
  mission runtime real robot-motion flat execution gate 也已完成并接入真实 Nav2。
  2026-05-04 又完成了当前窄范围的 production Mission Orchestrator scheduling policy；
  后续最大项目改进入口转为 production Mission Orchestrator remaining slice，
  仍然必须保持单主题、小步推进。

## 关键风险清单与处理状态

| 风险 | 当前处理 | 后续要求 |
| --- | --- | --- |
| route-following 历史 PASS 被误读成稳定门禁 | 已完成 dedicated hardening：DWB abort 复现后修复，3 次 clean-domain 连续 PASS | 后续可视为 opt-in regression 候选，但不得误判为 production route tracking 或默认 baseline |
| real-model regression wrapper 被误读成默认封板门禁 | 已明确 stable control-chain wrapper 优先，real-model regression 因包含 route-following 更敏感 | 后续不得用该 wrapper 替代 `verify_go2w_control_chain_regression.sh` |
| Phase 4 accepted 被误读成完整跨楼层自主 | 已在 architecture_state、handoff、README 中标注未完成项 | 后续继续区分 skeleton / verifier / production |
| 历史 `docs/superpowers/*` 中存在旧 `/tmp` FAST-LIO 路径和阶段旧口径 | 已在阅读顺序中标为历史任务记录，不覆盖当前默认 | 如引用历史计划，必须同时核对当前脚本和 `architecture_state.md` |
| 本地规划文件可能误入提交 | `.gitignore` 已忽略 `/task_plan.md`、`/findings.md`、`/progress.md` | 本地会话可继续用，不作为仓库正式交接工件 |
| 源码缓存和构建日志混淆事实源 | `build/`、`install/`、`log/`、`.go2w_external/`、`.learnings/` 均保持 ignored | 后续验证证据写入 `docs/verification/*`，不要引用临时日志作唯一事实源 |
| 搜索命令中 Markdown 反引号触发 shell 命令替换 | 已在 `.learnings` 记录，正式注意事项补充防复发 | 后续含反引号检索用单引号或拆词 |

## 已清理或已固化的内容
- 补充本最终封板报告，集中说明项目状态、风险和后续路线。
- 更新 handoff 入口，让新模型先看到最终封板报告。
- 更新阅读顺序，明确 `docs/superpowers/*` 是历史记录。
- 更新注意事项，新增“项目改进起步顺序”和“工具/检索易错点”。
- 更新新模型初始化提示词，使其可直接复制到新对话中使用。
- 将 mission runtime real-model flat execution gate 作为已完成能力固化；当时把下一步起点改为 production Mission Orchestrator scheduling policy，而该项现在也已完成。
- mission runtime real-model flat execution gate 现在会从 route graph 保留目标 yaw 并写回
  `NavigateToPose`，避免 flat goal 退化成单位四元数后再被 DWB 误判失败。
- 继续硬化 mission API bounded FIFO scheduling policy、operator control service 和
  durable queue replay，避免并发 `RunMission` goal 竞争单一 JSON 状态文件；当前已经有
  one-active-plus-one-queued、operator control 和 replay ledger，但这仍不是 priority scheduling。
- 将本地规划文件加入 `.gitignore`，避免把会话工作记忆误提交为正式项目事实源。
- 扩展 `tools/verify_phase4_pre_handoff.sh`，把最终封板报告纳入交接一致性 gate。

## 当前已完成能力
- Phase 1：Gazebo + `gz_ros2_control` + `/cmd_vel` 底盘可控闭环。
- Phase 2：FAST-LIO 输入输出、perception-owned `odom -> base_link`、perception stability、
  Nav2 costmap consumer gate。
- Phase 3A：最小同层 Nav2 planner/controller/BT 导航闭环。
- Phase 3B：最小 `nav2_route` / 手工 route graph baseline。
- Phase 3C：FAST-LIO repo-local external cache、多楼层 route graph/map metadata、hospital world asset。
- Phase 4A：最小 staircase connector detection、dedicated `/stair_exec` Action、控制权互斥和诊断。
- Phase 4B-min：mission-side route segmentation 与 stair dispatch。
- Phase 4C-min：flat/stair/flat execution gate。
- Phase 4D-min：`ComputeAndTrackRoute` feedback observation gate。
- Phase 4 accepted：pre-handoff、Phase 4A/B/C/D runtime、build/test、test-result 聚合验收。
- Phase 5A：受控 TF trajectory fixture 下的 live `nav2_route` route tracking observation。
- Real-model baseline：opt-in 真实 Go2W 模型、四 foot wheel controller、leg controller、sensor topics、stand initializer。
- Phase 4E：real-model stair fixture、mission recovery checkpoint/resume、stair tuning smoke。
- Stable control-chain regression：real-model baseline + stair fixture + mission recovery + stair tuning smoke。
- Real-model same-floor route-following dedicated hardening：candidate selection、goal tolerance 和 stale-process cleanup 已修复，3 次 clean-domain PASS。

## 当前未完成能力
- Production Mission Orchestrator：当前只是 mission API / checkpoint / retry / resume
  skeleton 加上 bounded FIFO queueing、operator control service 与 operator-triggered durable
  queue replay，仍不是完整长生命周期调度器。
- 真实机器人运动上的稳定 `nav2_route` route tracking：尚未完成。
- Mission runtime real robot-motion flat execution gate 已完成；当前 flat executor 仍保留 verifier skeleton 作为 deterministic 诊断路径。
- 真实楼梯动力学、leg trajectory、wheel lock、body-height 控制和 gait tuning：尚未完成。
- 默认仿真基线切换到 real-model：尚未批准。
- `map_server` / AMCL / `map -> odom` 定位链：尚未实现。
- Elevation mapping、traversability、automatic stair detection / connector generation：尚未实现。

## 后续项目改进推荐顺序
1. 扩展 production Mission Orchestrator remaining slice：先补 priority scheduling 或长期任务管理中的一个最小闭环。
2. 做 dedicated stair trajectory / wheel lock / body-height / gait tuning；不得把当前 phase-aware skeleton 当成真实控制器。
3. 再评估 real-model path 是否可以扩大为默认 baseline。
4. 最后进入 Phase 5 terrain-aware connector discovery、elevation mapping、traversability 和 automatic connector generation。

## 已执行的自批准任务单

Task Goal: production Mission Orchestrator scheduling policy。

Current Phase: `Phase 4 accepted`, post-Phase-4 hardening。

Allowed Files:
- `go2w_mission` mission runtime / mission API 中 mission scheduling 或 recovery 相关文件
- `go2w_navigation` 中必要的 mission verifier 或 route adapter
- 对应 focused tests
- `docs/verification/*` 中新增或更新 mission scheduling / recovery 验证记录
- 必要时更新 `docs/handoff/*` 与 `README.md`

Forbidden Files:
- perception TF authority
- default placeholder launch baseline
- stair dynamics / stair trajectory control
- AMCL / `map_server` / `map -> odom`
- elevation / traversability / automatic connector generation

Required Commands:
- `bash -n` 相关 mission / navigation verifier
- shellcheck（若本机可用）
- Python/YAML 静态解析和相关 pytest
- 新增或更新的 mission scheduling / recovery verifier
- `./tools/verify_go2w_control_chain_regression.sh`
- `./tools/verify_go2w_control_chain_regression.sh`
- `./tools/verify_phase4_pre_handoff.sh`

Definition of Done:
- Mission API / runtime 的最小调度或恢复闭环可重复验证，并保持 success/failure/cancel/timeout/unavailable 诊断。
- 现有 Phase 4C verifier skeleton 不被无证据移除；必须保留 deterministic 诊断路径。
- 不改变 perception TF authority、默认 placeholder launch baseline、stair dynamics 或 map / localization 范围。

执行状态：当前窄范围已完成。后续如要继续进入 priority scheduling 或完整长期任务管理，
必须另开新的完整任务单。

## 最终封板验证入口
迁移前新模型接手前至少运行：

```bash
./tools/verify_phase4_pre_handoff.sh
```

需要更强 runtime 证据时运行：

```bash
./tools/verify_go2w_control_chain_regression.sh
./tools/verify_phase4_runtime_acceptance.sh
```

## 本次封板验证结果
本轮封板后已完成以下验证：

| 命令 | 结果 | 说明 |
| --- | --- | --- |
| `bash -n tools/verify_phase4_pre_handoff.sh tools/verify_go2w_control_chain_regression.sh tools/verify_phase4_runtime_acceptance.sh tools/verify_go2w_real_model_route_following.sh` | PASS | 核心 shell 入口语法通过 |
| `shellcheck tools/verify_phase4_pre_handoff.sh tools/verify_go2w_control_chain_regression.sh tools/verify_phase4_runtime_acceptance.sh tools/verify_go2w_real_model_route_following.sh` | PASS | 本机 `/usr/bin/shellcheck` 可用且无诊断输出 |
| `git diff --check` | PASS | 无尾随空白或 patch 格式问题 |
| `./tools/verify_phase4_pre_handoff.sh` | PASS | 已纳入本最终封板报告检查 |
| `colcon test --packages-select go2w_navigation go2w_control go2w_mission --event-handlers console_direct+` | PASS | 3 个包测试通过 |
| `colcon test-result --verbose` | PASS | `90 tests, 0 errors, 0 failures, 0 skipped` |
| `PYTHONPATH="$PWD/go2w_navigation:$PWD/go2w_mission:$PWD/go2w_control" python3 -m pytest ...` | PASS | focused pytest 8 项通过 |
| `./tools/verify_go2w_control_chain_regression.sh` | PASS | real-model baseline、stair fixture、mission recovery、stair tuning smoke 全通过 |
| `./tools/verify_phase4_runtime_acceptance.sh` | PASS | pre-handoff、Phase 4A/B/C/D、build/test/test-result 全通过 |

验证期间直接运行一次未设置 `PYTHONPATH` 的 focused pytest 曾失败，根因是命令环境缺少包源码路径；
使用显式 `PYTHONPATH` 后同一 focused pytest 通过。该工具层问题已记录到 `.learnings/ERRORS.md`，
不影响 colcon test 结果。
