# Phase 4 迁移前风险清理与修复记录

## 已识别并修复

| 风险 | 证据 | 处理 | 状态 |
| --- | --- | --- | --- |
| FAST-LIO 默认路径声明与脚本不一致 | Phase 3C 声称默认 `.go2w_external/`，但 Phase 2E/2F/2G/2H/3A 验证脚本仍默认 `/tmp/go2w_phase2d_fastlio_ws` | 统一改为 `GO2W_FASTLIO_CACHE_ROOT` 派生的 `.go2w_external/workspaces/fast_lio_ros2` | 已修复 |
| Phase 2C patch/audit 工具仍默认 `/tmp/fast_lio_ros2_probe` | `tools/apply_phase2c_fastlio_patch.sh` 与 `tools/check_phase2_fastlio_external.sh` 的默认值落后于 Phase 3C | 改为 `.go2w_external/src/FAST_LIO_ROS2`，仍保留显式参数覆盖 | 已修复 |
| 新对话缺少集中交接入口 | 仓库只有分散架构、验收、计划文档 | 新增 `docs/handoff/README.md` 与配套交接文件 | 已修复 |
| Phase 4A 起点容易被扩大 | README/状态文档虽有边界，但缺少迁移前专门警示 | 在交接报告、注意事项和初始化提示词中重复固定 Phase 4A 最小边界 | 已修复 |
| 交接资料缺少一键静态验收 | 迁移包新增后需要可重复检查 | 新增 `tools/verify_phase4_pre_handoff.sh` | 已修复 |
| 源码目录存在无价值 Python 缓存 | `go2w_*` 与 `tools` 下存在 ignored `__pycache__` | 清理源码侧 `__pycache__`，不把缓存纳入交接 | 已清理 |

## 保留但已标注的历史内容
- `docs/superpowers/` 中的早期 Phase 2/3 计划和设计文档保留为历史记录。
- `docs/verification/` 中早期 `/tmp` 证据路径保留为当时采证结果。
- 不重写历史证据，避免破坏审计链；当前默认策略以 `architecture_state.md`、
  `README.md`、本目录和当前脚本为准。

## 仍存在但暂不可在本任务修复

| 限制 | 原因 | 后续处理 |
| --- | --- | --- |
| Gazebo GPU rendering 仍不纳入默认基线 | WSLg + Gazebo Fortress/Ogre2 `use_gpu:=true` 已验证不稳定 | 保持 Gazebo `use_gpu:=false`，RViz/CUDA 链路单独验证 |
| 占位 URDF 耦合 geometry/control/sensors | 当前可运行闭环依赖该过渡模型 | 未来 Unitree model import 或模型重构任务单中处理 |
| Unitree Go2W 真实模型未导入 | 会影响控制、碰撞、传感器布局和运动学假设 | Phase 4 或后续独立模型基线任务处理 |
| Phase 3C route graph 是手工 floor atlas | 目的是给 Phase 4 手工连接器提供基线，不是自动建图结果 | Phase 4 先证明控制交接；Phase 5 再自动连接器 |
| 没有 production Mission Orchestrator | 当前还未进入 Phase 4A runtime | Phase 4A 从最小状态机/控制权交接骨架开始 |
| 没有真实楼梯执行控制器调参 | Phase 4 DoD 先验证接口握手与互斥，不追求动力学真实性 | 后续 dedicated stair executor/control tuning 任务处理 |
| 没有 `map -> odom` 定位融合链 | Phase 3A 有意运行在 `odom`，Phase 3C 只提供 `map` 资产 | 后续定位/地图服务任务单再引入 |
