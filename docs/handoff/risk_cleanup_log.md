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
| Phase 4A handoff 缺少可重复 runtime 证据 | 仅有 Phase 3C connector 资产不能证明控制权交接 | 新增 `tools/verify_phase4a_stair_handoff.sh`，验证 route connector detection、`/stair_exec`、command gate 互斥、success/failure/cancel/timeout | 已修复 |
| Phase 4A 后缺少 mission-side 分段 runtime 证据 | Handoff skeleton 已能触发 `/stair_exec`，但还没有 mission 层 route segmentation 证据 | 新增 Phase 4B-min one-shot mission segment runtime 和 `tools/verify_phase4b_mission_segments.sh`，验证 success/failure/cancel/timeout/route unavailable/connector unavailable | 已修复 |
| Phase 4B-min flat segment 仍是打印占位 | Mission runtime 没有真实调用任何 navigation-owned flat execution surface | 新增 Phase 4C-min flat navigation executor skeleton 和 `tools/verify_phase4c_flat_segment_gate.sh`，验证 flat/stair/flat sequence 与 flat failure/cancel/timeout/unavailable | 已修复 |
| Python ROS entrypoint 拒绝 launch_ros 追加参数 | `go2w_flat_nav_executor` 初版使用严格 `argparse.parse_args()`，遇到 `--ros-args` 退出 | 改为 `parse_known_args()` 并将 ROS 参数交给 `rclpy.init(args=...)` | 已修复 |
| Route tracking feedback / Route Operation 缺少 mission-side observation gate | Phase 4C-min 只证明 `NavigateToPose` flat Action gate，未观察 `ComputeAndTrackRoute` feedback 的 staircase edge 和 operation trigger | 新增 Phase 4D-min feedback executor、mission observer 和 `tools/verify_phase4d_route_tracking_feedback.sh`，验证 success、missing operation、unavailable action | 已修复 |
| Phase 4 verifier domain id 可能越过 Fast-DDS 可用范围 | Phase 4D 初版曾生成过高 `ROS_DOMAIN_ID`；Phase 4C 旧公式理论上也可能超过 231 | Phase 4C/4D verifier 统一使用 `(($$ % 90) + 130)` 范围，避免 domain 范围型假失败 | 已修复 |

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
| 没有 production Mission Orchestrator | Phase 4B-min 只新增 one-shot mission segment runtime，不是长生命周期调度器 | 后续用独立完整任务单推进 production-grade mission API、恢复策略或状态持久化 |
| Phase 4C-min flat executor 仍是 verifier skeleton | 本阶段只证明 mission 到 navigation-owned `NavigateToPose` gate 的调度，不执行真实 Nav2 route tracking against robot motion | 后续 real route tracking observation gate 或真实 Nav2/Gazebo 联合验收任务处理 |
| Phase 4D-min route tracking feedback executor 仍是 verifier skeleton | 本阶段只证明 mission 能消费 `ComputeAndTrackRoute` feedback 和 `operations_triggered`，不执行真实 route tracking 或 operation plugin | 后续真实 route tracking、Route Operation plugin 或 Nav2/Gazebo 联合验收任务处理 |
| ROS discovery/lifecycle 偶发等待 | 曾有一次 Phase 4B 回归中 `route_server` 进程已启动但 lifecycle service 未被发现；换新 domain 复跑通过 | 先清理残留并换新 `ROS_DOMAIN_ID` 复跑；若复现，再单独加 discovery 诊断 |
| 没有真实楼梯执行控制器调参 | Phase 4 DoD 先验证接口握手与互斥，不追求动力学真实性 | 后续 dedicated stair executor/control tuning 任务处理 |
| 没有 `map -> odom` 定位融合链 | Phase 3A 有意运行在 `odom`，Phase 3C 只提供 `map` 资产 | 后续定位/地图服务任务单再引入 |
