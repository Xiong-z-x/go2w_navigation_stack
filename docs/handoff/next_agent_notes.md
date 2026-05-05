# 给下一个模型的注意事项与经验总结

## 审计硬规则
- 无证据不判完成。计划、TODO、注释、README 摘要和旧日志都不能单独当作完成证据。
- 阶段审计必须输出四种状态：`已完成`、`部分完成`、`未完成`、`无法确认`。
- 文档与代码冲突时，先验证当前行为，再更新文档，不要把历史叙述当成当前事实。
- `docs/architecture/architecture_state.md`、`docs/handoff/current_project_state.md`、`docs/handoff/project_state_audit.md`、`docs/handoff/risk_cleanup_log.md` 和相关 verification 文档必须保持同一口径。
- 历史计划和本地会话文件只作背景，不作当前事实源。

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
- 不要把 Phase 5A live route tracking observation gate 当成物理楼梯动力学或 production
  Mission Orchestrator。它已经直接接通真实 `nav2_route` route_server 和
  `ComputeAndTrackRoute`，并观察到 `500` 与 `AdjustSpeedLimit`，但仍只是在受控 TF
  trajectory fixture 上做观察，不是机器人实运动。
- 不要把 real-model same-floor route-following regression candidate 当成 production
  route tracking。它已完成 dedicated hardening 并三次 clean-domain 通过，但仍只是
  opt-in 短 `NavigateToPose` 运动链验证；稳定 control-chain regression 仍刻意把它拆出。
- 不要把 `go2w_mission` 的 `RunMission` skeleton 当成 production Mission
  Orchestrator。它只是把 route compute、flat/stair dispatch 和诊断结果码串起来，
  当前虽已新增 JSON checkpoint、同一 goal resume 和有限 retry，仍依赖现有
  route server、`NavigateToPose` verifier 和 `/stair_exec` skeleton，不是完整生产调度器。
- 不要把 `RunMission` 的并发入队误判成可并行执行。当前 mission API 已是 bounded
  FIFO queueing；并发 goal 可能 queue、`MISSION_BUSY` / `mission_queue_full` 或
  queued cancel，且现在还多了 operator-state snapshot、`MissionControl` 控制面和
  operator-triggered durable queue replay ledger、bounded terminal task-history ledger；
  现在还补齐了 non-preemptive queued priority scheduling 和只读 workflow policy snapshot。
  这仍不是 active preemption、fleet-level task assignment 或完整生产调度器。
- 不要把 mission runtime real-model flat execution gate 当成 production Mission
  Orchestrator。它已经把 flat segment 接到真实 Nav2 `/navigate_to_pose`，但仍只是
  opt-in flat-only gate，和完整生产调度器不是一回事。
- 不要让 `go2w_mission` 的 flat goal pose conversion 在 `mission_api` 和
  `phase4b_mission_runtime` 之间再次分叉；当前 canonical helper 是
  `go2w_mission.mission_pose.pose_stamped_from_xy_yaw()`。
- 不要把 Phase 4E real-model stair fixture 当成真实楼梯动力学。它只证明
  `/stair_exec` 在 opt-in real-model fixture 下能完成 phase-aware action 闭环、
  `flat/wheeled -> stair/legged -> flat/wheeled` 控制权交接、profile-limited
  stair velocity 和 leg hold/release 诊断。
- 不要把 real-model regression wrapper 当成默认基线切换。它只是把 real-model
  baseline、same-floor route-following 和 Phase 4E stair fixture 串成 opt-in 回归。
- 不要把 `nav2_route` 当成 3D 地形规划器。它不是自动楼梯识别或 traversability。
- 不要重新启用 `diff_drive_controller` 的 `odom -> base_link` TF。该边当前属于
  perception authority。
- 不要把 `stair_exec` 写成 Action or Service。契约已冻结为 dedicated Action。
- 不要把历史 `/tmp` FAST-LIO 证据路径误判成当前默认依赖策略。当前默认是
  `.go2w_external/`。
- 不要混入 Gazebo Garden/Harmonic，也不要默认 Gazebo GPU rendering。
- 不要在仓库根再创建嵌套 `src/`。本仓库自己就是 monorepo root。
- 不要把 Go2W real model / motion-mode baseline 当成默认仿真基线或真实步态控制。
  当前真实模型路径是 opt-in：`go2w_sim sim_go2w_real.launch.py`；旧
  `go2w_sim sim.launch.py` placeholder 路径仍是既有验证默认。

## 最容易产生误判的地方
- README 是操作摘要，不是架构事实源。
- `docs/superpowers/` 是历史任务记录，不一定代表最新默认。
- 早期验证文档中的 `/tmp/...` 是证据目录，不一定是当前工具默认。
- Phase 3A 的 `odom` frame Nav2 闭环不是长期 `map -> odom` 定位方案。
- Phase 3C 的 `map` frame route graph 不代表 AMCL/map_server 已启用。
- Hospital world 资产可启动，不代表真实楼梯运动学已验证。

## 接手后最应该先确认
- 先进入实际项目仓库根：`/home/xiongzx/go2w_ws/src/go2w_navigation_stack`。外层
  `/home/xiongzx/go2w_ws` 是 workspace，不能用它的 git 状态判断项目历史或同步状态。
- `git status --short --branch` 是否干净并与远端 main 对齐。
- `docs/architecture/architecture_state.md` 当前 Active Phase。
- `docs/handoff/project_state_audit.md` 是否与当前代码、脚本和 verification 文档同一口径。
- `docs/handoff/pre_migration_final_freeze_report.md` 中的最终封板结论和下一任务建议。
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
- 将 real-model opt-in 路径切成默认基线。
- perception TF authority 重构。

## Phase 4 accepted 后续防漂移边界
Phase 4C-min 已完成 hand-authored staircase connector 上的最小 flat/stair/flat
执行门；Phase 4D-min 已完成 `ComputeAndTrackRoute` feedback / Route Operation
observation gate；Phase 5A 已补上 live route-server-backed route tracking 观察门；
Go2W real model / motion-mode baseline 已补上 opt-in 真实模型、四 foot wheel
controller profile、`flat -> wheeled` / `stair -> legged` 状态和启动站立验证；
Phase 4 accepted 已完成总验收；`RunMission` skeleton 也已完成并验证；Phase 4E
又补上 real-model stair fixture、mission recovery checkpoint/resume、operator control
service、operator-triggered durable queue replay、bounded terminal task history、queued priority scheduling、workflow policy snapshot 和
opt-in real-model regression wrapper。后续最小任务必须另有完整任务单或当前
自主审批模式下的自批准任务单；后续如继续 mission orchestration，只做另一个明确命名的
remaining slice，或转向
真实 stair trajectory / gait tuning、Phase 5 terrain-aware connector discovery 或未来
default real-model re-baseline。不要把下一步扩大为真实多楼层
自主、自动楼梯检测、traversability 或 `map -> odom` 定位链。

## Runtime 验证注意
- Phase 4B 回归曾出现一次非复现的 ROS discovery/lifecycle 等待失败：
  `route_server` 进程已启动，但 lifecycle manager 未发现 `route_server/get_state`。
  后续换新 ROS domain 复跑通过。遇到类似现象时，先清理残留并换新 domain 复跑，
  不要直接改 route graph 或 route server 配置。
- ROS 2 Fast-DDS domain id 必须保持在可用范围内；Phase 4C/4D verifier 使用
  `(($$ % 90) + 130)`，避免旧公式偶发生成过高 domain id 导致假失败。
- Real-model verifier 初版曾因 `joint_state_broadcaster` 默认 5 秒 switch timeout
  和 foot wheel mesh collision 过重而超时。当前修正是：real-model launch 给
  spawner 显式 `--switch-timeout` / `--service-call-timeout`，并将四个 foot wheel
  collision 简化为与 `wheel_radius=0.10` 一致的圆柱。后续不要把这改回 mesh
  collision，除非先有新的 headless runtime 证据。
- Real-model baseline verifier 现在不只看 spawner 文本日志，还轮询
  `ros2 control list_controllers`，把 `controller_states_ready: PASS` 作为 controller
  激活证据。以后遇到 spawner 重试或 `Configured and activated` 日志缺失，先看控制器
  state，不要直接把 launch 判死。
- Real-model same-floor route-following verifier 现在有 dedicated hardening 证据，但不是
  production route tracking。对应 Nav2 参数文件是
  `go2w_navigation/config/phase5_real_model_nav2_same_floor.yaml`，当前关键值是
  `robot_radius: 0.28`、`footprint_padding: 0.01`、`origin_z: -0.40`、`z_voxels: 16`、
  `xy_goal_tolerance: 0.08`。
  `voxel_grid` 在这个 runtime 里明确提示最多只支持 16 个 z values，所以不要把
  `z_voxels` 提到 16 以上。2026-05-02 dedicated hardening 曾复现
  `ComputePathToPose` 非空但 `NavigateToPose` DWB abort；当前修复是首个可达候选策略、
  `xy_goal_tolerance: 0.08` 和 stale-process cleanup，随后 3 次 clean-domain PASS。
- `go2w_control` 的 `stair_executor` 现在会读取 legged motion profile 并钳制 stair 线速度。
  这只是让 skeleton 和 motion baseline 对齐，不是已经调好的真实楼梯步态。
- `go2w_control` 的 `stair_executor` 现在还会在 stair owner 激活时发布 12 关节 leg hold command。
  这只是把姿态出口显式化，不代表真实楼梯行走调参完成。
- Mission runtime real-model flat execution gate 的关键 launch 参数是
  `flat_behavior_tree:=__empty__`；不要再尝试传空的 `flat_behavior_tree:=`，ROS 2 launch
  会直接拒绝。
- Mission real-flat verifier 依赖在 mission API ready 后重新生成并 reload route graph；
  不要删掉这一步，否则 perception odom 漂移后更容易把 stale graph 当成 Nav2 问题。
- Mission real-flat verifier 曾出现一次 Nav2 lifecycle configure 超时：`bt_navigator/change_state`
  response timeout 后外层看到 `controller_server_lifecycle: inactive [2]`。这类失败先看
  evidence dir 的 `nav2.log`，清理 orphaned sim/perception/FAST-LIO/Nav2 进程并换新
  ROS domain 复跑；2026-05-04 clean-domain rerun 已通过。不要把这个症状直接归因到
  mission API 或 route graph。
- Mission fixture 不要再使用 node id `0`；mission API 会正确拒绝它作为 `invalid_goal`。
- Mission flat goal 不能只带 x/y；必须从 route graph 读回目标 yaw 并转换成四元数，
  否则 real-model flat gate 会更容易在 DWB 局部规划阶段 abort。
- 修改 mission / Nav2 源码后，先确保 install space 已重建或至少不是旧 install；
  不要用 stale install 复跑，容易把 `behavior_tree=success` 之类的旧参数误投给真实 Nav2。
- 宽 `pkill -f` 需要格外小心；不要让它匹配当前 shell 或工作区内自己的调试进程。
- `go2w_stand_initializer` 现在支持 `--motion-mode wheeled|legged`，real-model launch
  显式传入 `--motion-mode legged` 并打印 profile 摘要；这只是启动姿态和诊断基线，
  不是自动切换步态控制器。
- Phase 4E stair fixture verifier 是 `tools/verify_phase4e_stair_fixture.sh`。它会启动
  opt-in real-model launch，拉起 `go2w_command_gate` 和 `go2w_stair_executor`，
  发送 `/stair_exec` goal，并检查 owner/mode 日志、phase plan、每个 phase 状态和
  action success。
- Phase 4E stair tuning smoke test 是 `tools/verify_phase4e_stair_tuning_overrides.sh`。
  它复用同一 real-model fixture，但用环境变量覆盖 stair body height、foot raise、
  gait、speed 和 velocity 上限，确认默认 baseline 不变时仍能成功闭环。
- Phase 4E mission recovery verifier 是 `tools/verify_phase4e_mission_recovery.sh`。
  它先故意不启动 stair executor，使 mission 写入 `RECOVERABLE` checkpoint，再用同一
  state file 重启并从 stair segment 恢复到 `MISSION_SUCCEEDED`。
- Real-model broad regression 入口是 `tools/verify_go2w_real_model_regression.sh`。
  如果隔离 worktree 缺少 `.go2w_external/workspaces/fast_lio_ros2/install/setup.bash`，
  先运行 `./tools/prepare_phase2d_fastlio_external.sh`，不要把缺依赖误判成 Nav2 或
  real-model 控制失败。该 wrapper 包含 route-following smoke，因此不应替代稳定的
  `tools/verify_go2w_control_chain_regression.sh`。

## 工具和检索易错点
- 在 Bash 里用 `rg` 搜索含 Markdown 反引号的字符串时，不要把未转义反引号放进双引号。
  Bash 会先做命令替换，导致 `unexpected EOF while looking for matching \`\`` 或更隐蔽的
  搜索结果失真。安全做法是拆分关键词、用单引号包裹 pattern，或逐个转义反引号。
- `task_plan.md`、`findings.md`、`progress.md` 是本地 agent 工作记忆，已被 `.gitignore`
  忽略。正式交接事实必须写入 `docs/handoff/*`、`docs/architecture/*` 或 `docs/verification/*`。
- `verify_go2w_control_chain_regression.sh` 与
  `verify_go2w_mission_real_flat_execution.sh` 不要并行跑；它们都是重型
  ROS/Gazebo verifier，并发时会放大资源争用，出现假 timeout / 假 NO_PARAM。
  先串行复验，除非明确要测并发鲁棒性。

## 后续项目改进起步顺序
1. 当前窄范围 production Mission Orchestrator scheduling policy、queued priority scheduling、
   operator control、durable queue replay、bounded terminal task history 和 workflow policy snapshot 已完成。下一步进入
   production Mission Orchestrator remaining slice 时，只做另一个明确命名的单主题
   orchestration gap，例如 fleet-level task assignment 或超出当前只读 snapshot 的 workflow backend。
2. 再做 dedicated stair trajectory / wheel lock / body-height / gait tuning。
3. 最后再进入 real-model default baseline 评估、Phase 5 elevation/traversability/
   automatic connector generation。

## 上下文变长后的防失真做法
- 每完成一个阶段或关键任务，更新 `architecture_state.md`。
- 每次验收必须补 `docs/verification/` 证据或可重复脚本。
- 交接给新对话时先更新 `docs/handoff/`，不要只靠聊天记录。
- 把事实、推断、待验证项分开写。
- 如果文档和代码冲突，先报告并验证，不要选择性相信旧上下文。
