# Phase 4 迁移前交接包索引

## 用途
本目录是进入 Phase 4A 新对话前的集中交接入口。它不替代架构事实源，
只把当前仓库真实状态、风险清理记录、阅读顺序和下一模型初始化信息集中起来。

## 有效范围
- 快照日期：2026-04-30
- 当前阶段：已验收 `Phase 3`，尚未进入 `Phase 4A`
- 当前主线：ROS 2 Humble + Gazebo Fortress-only + FAST-LIO external cache
- 下一任务边界：最小楼梯状态机/控制权交接骨架

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
6. `docs/handoff/phase4_migration_handoff_report.md`
7. `docs/handoff/current_project_state.md`
8. `docs/handoff/risk_cleanup_log.md`
9. `docs/handoff/reading_order_and_file_map.md`
10. `docs/handoff/next_agent_notes.md`
11. `docs/handoff/new_model_initialization_prompt.md`

## 本目录文件职责
- `current_project_state.md`：当前真实状态总览。
- `risk_cleanup_log.md`：封板前风险识别、修复与剩余限制。
- `phase4_migration_handoff_report.md`：迁移前总报告。
- `reading_order_and_file_map.md`：关键文件/目录阅读顺序与职责说明。
- `next_agent_notes.md`：给下一个模型的易错点和警示。
- `new_model_initialization_prompt.md`：可直接复制到新会话的初始化提示词。

## 封板验证
交接包一致性可用以下命令检查：

```bash
./tools/verify_phase4_pre_handoff.sh
```
