# 关键文件/目录阅读顺序与说明

## 第一层：必须先读的事实源
1. `AGENTS.md`：项目身份、阶段纪律、协作规则、任务单格式。
2. `docs/architecture/system_blueprint.md`：全生命周期路线和阶段验收目标。
3. `docs/architecture/interface_contracts.md`：跨层接口、TF、Action、route/mission 契约。
4. `docs/architecture/architecture_state.md`：当前阶段、当前真实状态、唯一下一步边界。

## 第二层：迁移前状态与风险
1. `docs/handoff/phase4_migration_handoff_report.md`：迁移前总报告。
2. `docs/handoff/current_project_state.md`：当前状态总览。
3. `docs/handoff/risk_cleanup_log.md`：已修风险与剩余限制。
4. `docs/handoff/next_agent_notes.md`：新模型最容易踩的坑。

## 第三层：运行和验收记录
- `README.md`：操作入口和当前状态摘要，不是架构事实源。
- `docs/verification/phase1_runtime_acceptance.md`：Phase 1 运行闭环证据。
- `docs/verification/phase2_runtime_acceptance.md`：Phase 2 总体验收。
- `docs/verification/phase3_runtime_acceptance.md`：Phase 3 总体验收。
- `docs/verification/phase3c_hardening_acceptance.md`：Phase 3C 硬化证据。
- `docs/verification/gazebo_gpu_rebaseline.md`：Gazebo GPU 降级原因。

## 第四层：历史任务记录
- `docs/superpowers/specs/`：历史设计记录。
- `docs/superpowers/plans/`：历史执行计划。

这些文件可用于追溯为什么这么做，但不应覆盖当前 `architecture_state.md`。
早期文件中的 `/tmp` FAST-LIO 路径可能只是历史证据，不代表当前默认。

## 核心代码目录
- `go2w_description/`：URDF、RViz、robot state publisher launch。
- `go2w_sim/`：Gazebo worlds、simulation launch、controller config。
- `go2w_perception/`：FAST-LIO adapters、TF authority、patch、external lock。
- `go2w_navigation/`：Nav2 configs、BT、route graph、maps。
- `go2w_control/`：当前 scaffold，Phase 4 后可能开始承载 stair execution。
- `go2w_mission/`：当前 scaffold，Phase 4 后可能开始承载 mission orchestration。

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

## 生成/缓存目录
- `.go2w_external/`：ignored FAST-LIO external source/workspace cache。
- `build/`、`install/`、`log/`：colcon 生成目录。
- `.pytest_cache/`、`__pycache__/`：本地缓存，不是项目事实源。
