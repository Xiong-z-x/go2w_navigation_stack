# Go2W Real Model and Motion Mode Baseline Design

## Status
实现已完成；当前验证与结论见 `docs/verification/go2w_real_model_motion_mode_baseline.md`。

已批准的实现方向：新增一个可选的真实 Go2W 模型与运动模式基线，保留现有 placeholder 默认路径，不破坏 Phase 4 / Phase 5 已验收链路。

## Problem
当前仓库里，`go2w_description` 仍以占位两轮模型为默认，`go2w_sim` 的控制链也仍围绕 placeholder / diff-drive 组织。这样能支撑既有验收，但不能代表真实 Go2W 的几何、关节结构、轮足混合控制和初始化站立姿态。

需要补上的不是“真实跨楼层自主导航”，而是一个可验证的模型与运动模式基线：
- 真实 Go2W 关节和外形资产
- wheeled / legged 两种运动模式的明确配置
- 启动时可重复的站立姿态
- 与当前控制权交接逻辑一致的模式状态输出

## Non-goals
- 不做 production Mission Orchestrator
- 不做真实楼梯动力学闭环
- 不做 elevation mapping / traversability
- 不做 automatic stair connector generation
- 不做 `map_server` / AMCL / `map -> odom`
- 不修改 perception-owned `odom -> base_link` 权限边界
- 不把 `stair_exec` 改成 service

## Chosen Approach
采用“opt-in 真实模型 + 保留旧默认路径”的路线。

1. `go2w_description` 增加真实 Go2W 模型资产，默认仍保留 placeholder 文件。
2. `go2w_sim` 新增一个真实模型专用 launch 路径和 controller profile。
3. `go2w_control` 增加纯数据化的 motion profile 与站立初始化辅助逻辑，并让当前 owner -> motion mode 的映射显式可观测。
4. 先把真实模型、轮式/足式模式、站立姿态做成可验证基线，再考虑后续是否切默认。

## Why This Route
- 风险最低：不会破坏已有 Phase 4 / 5 验收脚本。
- 与当前架构一致：模型、仿真、控制分层仍然清晰。
- 可验证：可先验证 URDF、controller YAML、站立命令与 launch 结果，再谈更高层运动学。
- 可回退：真实模型路径是独立的 opt-in 入口，不会污染 placeholder 主线。

## Implementation Boundaries

### `go2w_description`
- 引入官方 Go2W URDF / mesh 资产。
- 保留 placeholder 作为旧默认。
- 为真实模型补齐当前仿真需要的传感器和控制挂点。

### `go2w_sim`
- 新增真实模型专用 controller profile。
- 新增真实模型专用 launch 入口。
- 继续保持 Fortress-only、headless-first 的验证方式。

### `go2w_control`
- 把 wheeled / legged / stand 的运动参数明确成纯数据。
- 让 owner -> mode 的映射可观测。
- 提供启动站立的最小辅助节点或脚本。

## Verification Strategy
先做纯测试，再做构建，再做 headless launch 验证。

优先级：
1. Python/URDF/YAML 纯解析测试
2. `bash -n`
3. `colcon build --symlink-install --packages-select go2w_description go2w_sim go2w_control`
4. `colcon test --packages-select go2w_description go2w_sim go2w_control`
5. 新的 real-model headless verifier
6. `git diff --check`

## Risks
- 真实 Go2W URDF 体量比 placeholder 大很多，必须避免把旧验收链路带坏。
- 4 个 foot wheel 需要和 diff-drive controller 的 wheels-per-side 配置对齐，否则 `/cmd_vel` 不会按预期驱动。
- 站立姿态如果没有 controller 持续保持，Gazebo 中的姿态会漂。
- 真实模型的 sensor / frame 命名如果处理不好，会影响已有 perception 资产。
