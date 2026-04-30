# 给下一个模型的注意事项与经验总结

## 最容易犯错的地方
- 不要把 Phase 3C route graph 当成已实现跨楼层自主导航。它只是手工资产和
  route_server baseline。
- 不要把 Phase 4A handoff skeleton 当成真实楼梯运动控制或 production Mission
  Orchestrator。它只证明 connector detection、Action handoff、控制权互斥和诊断状态。
- 不要把 Phase 4B-min mission segment runtime 当成 production Mission Orchestrator
  或真实跨楼层自主导航。它只证明手工 route 分段、楼梯段 `/stair_exec` 调度和
  mission 级结果诊断；Phase 4C-min 已补上 flat Action gate，但仍不是真实 route tracking。
- 不要把 Phase 4C-min flat segment execution gate 当成真实 Nav2 route tracking。
  它只证明 mission runtime 会调用 navigation-owned `NavigateToPose` Action gate，
  并观察 `flat -> stair -> flat` 顺序；flat executor 仍是 verifier skeleton。
- 不要把 Phase 4D-min route tracking feedback observation gate 当成真实 Nav2 route
  tracking 或真实 `nav2_route` operation plugin。它只证明 mission observer 能消费
  `ComputeAndTrackRoute` feedback，检测 staircase edge `500`，并观察
  `operations_triggered` 中的 `stair_exec`。
- 不要把 `nav2_route` 当成 3D 地形规划器。它不是自动楼梯识别或 traversability。
- 不要重新启用 `diff_drive_controller` 的 `odom -> base_link` TF。该边当前属于
  perception authority。
- 不要把 `stair_exec` 写成 Action or Service。契约已冻结为 dedicated Action。
- 不要把历史 `/tmp` FAST-LIO 证据路径误判成当前默认依赖策略。当前默认是
  `.go2w_external/`。
- 不要混入 Gazebo Garden/Harmonic，也不要默认 Gazebo GPU rendering。
- 不要在仓库根再创建嵌套 `src/`。本仓库自己就是 monorepo root。
- 不要把 Unitree Go2W 真实模型加载视为已完成。当前仍是 placeholder。

## 最容易产生误判的地方
- README 是操作摘要，不是架构事实源。
- `docs/superpowers/` 是历史任务记录，不一定代表最新默认。
- 早期验证文档中的 `/tmp/...` 是证据目录，不一定是当前工具默认。
- Phase 3A 的 `odom` frame Nav2 闭环不是长期 `map -> odom` 定位方案。
- Phase 3C 的 `map` frame route graph 不代表 AMCL/map_server 已启用。
- Hospital world 资产可启动，不代表真实楼梯运动学已验证。

## 接手后最应该先确认
- `git status --short --branch` 是否干净并与远端 main 对齐。
- `docs/architecture/architecture_state.md` 当前 Active Phase。
- `tools/verify_phase4_pre_handoff.sh` 是否通过。
- `.go2w_external/` 是否存在；若不存在，先跑
  `./tools/prepare_phase2d_fastlio_external.sh`。
- 当前任务单是否完整包含 6 项：Task Goal、Current Phase、Allowed Files、
  Forbidden Files、Required Commands、Definition of Done。

## 出错后的处理原则
- 先定位数据流和进程状态，不要猜。
- 先看 topic、TF、lifecycle、launch log，再改代码。
- 先修当前层，不要把问题推给下一阶段大重构。
- 失败命令要留下可审计证据，不能口头说“应该可以”。
- 新踩坑必须写回本注意文档或后续专门风险文档。

## Phase 4A 当前已验收边界
Phase 4A 当前只证明了控制权交接骨架：

- 手工 route graph connector 触发。
- Nav2 平地控制与 stair executor 控制互斥。
- `stair_exec` Action skeleton 可观测。
- 失败/取消/完成状态向上暴露。
- 超时状态可通过 verifier 诊断。

不应同时做：

- production Mission Orchestrator。
- 真正爬楼控制器调参。
- 自动楼梯检测。
- elevation mapping / traversability。
- Unitree 模型导入。
- perception TF authority 重构。

## Phase 4D-min 后续防漂移边界
Phase 4C-min 已完成 hand-authored staircase connector 上的最小 flat/stair/flat
执行门；Phase 4D-min 已完成 `ComputeAndTrackRoute` feedback / Route Operation
observation gate。后续最小任务必须另有完整任务单或当前自主审批模式下的自批准任务单，
可以围绕 Phase 4 aggregate acceptance gate、mission recovery、或 production-grade
Mission API skeleton 做单主题推进。不要把下一步扩大为真实多楼层
自主、真实楼梯控制器调参、自动楼梯检测、traversability 或 `map -> odom` 定位链。

## Runtime 验证注意
- Phase 4B 回归曾出现一次非复现的 ROS discovery/lifecycle 等待失败：
  `route_server` 进程已启动，但 lifecycle manager 未发现 `route_server/get_state`。
  后续换新 ROS domain 复跑通过。遇到类似现象时，先清理残留并换新 domain 复跑，
  不要直接改 route graph 或 route server 配置。
- ROS 2 Fast-DDS domain id 必须保持在可用范围内；Phase 4C/4D verifier 使用
  `(($$ % 90) + 130)`，避免旧公式偶发生成过高 domain id 导致假失败。

## 上下文变长后的防失真做法
- 每完成一个阶段或关键任务，更新 `architecture_state.md`。
- 每次验收必须补 `docs/verification/` 证据或可重复脚本。
- 交接给新对话时先更新 `docs/handoff/`，不要只靠聊天记录。
- 把事实、推断、待验证项分开写。
- 如果文档和代码冲突，先报告并验证，不要选择性相信旧上下文。
