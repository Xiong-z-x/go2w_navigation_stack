# 面向新对话模型的重启经验总结

## 用途
本文面向下一个新对话模型，也面向准备重新开始机器狗项目开发时的第一轮审计。
它不替代架构事实源，也不证明任何新能力已经完成。它只记录本项目历史中最容易
导致误判、过度自信、文档脱节和验证不足的经验。

实现或审计仍按以下事实源顺序判断：

1. `docs/architecture/system_blueprint.md`
2. `docs/architecture/interface_contracts.md`
3. `docs/architecture/architecture_state.md`
4. 当前完整任务单或自批准任务单
5. `docs/handoff/*`
6. `README.md` 与历史验证记录

## 当前最后观察状态
- 最后观察日期：2026-05-06。
- 实际项目仓库根：`/home/xiongzx/go2w_ws/src/go2w_navigation_stack`。
- 外层 `/home/xiongzx/go2w_ws` 只是 ROS workspace，不能用它的 git 状态判断本项目历史。
- `./tools/verify_phase4_pre_handoff.sh` 在本次总结前通过。
- 本次总结前工作区已有未提交改动和新增文件，主要来自上一轮 single-floor hospital / RViz demo hardening。
  这些改动不能被下一个模型直接当成已封板主线；必须先看 `git status --short --branch`，
  再重新运行对应 build、pytest、runtime verifier 和可视化验证。

## 最容易犯错的地方
- 把阶段名当能力名。`Phase 4 accepted` 证明 manual-connector runtime chain 和对应 verifier
  通过，不等于完整跨楼层自主导航、真实楼梯动力学、production Mission Orchestrator、
  `map_server` / AMCL 或 Phase 5 自动连接器。
- 把 skeleton 当 production。`/stair_exec`、flat executor、mission runtime、route feedback
  observer、workflow backend 等很多模块当前是可验证骨架或窄范围 gate，不是完整生产系统。
- 把 opt-in 当 default。真实 Go2W 模型、real-model route following、hospital single-floor gate、
  real-model route tracking 和 real-model regression 都是 opt-in 或候选路径；默认 placeholder
  仿真基线未被正式替换。
- 把一次 GUI 演示当回归证据。RViz / Gazebo 演示能说明链路可视化，但不能代替 headless verifier、
  build/test、topic/TF/lifecycle/action 证据。
- 把规划成功当运动成功。`ComputePathToPose` 返回路径不等于 `NavigateToPose` 成功，也不等于机器人
  有足够 odom 位移；医院 world 中短目标曾被 planner tolerance 吞掉，必须检查 path length、
  `/cmd_vel` 非零计数、perception odom 和 diff-drive odom delta。
- 把点云输出当 2D 地图链。FAST-LIO 的 `/go2w/perception/cloud_registered` 和
  `/go2w/perception/laser_map` 是点云/建图基础，不是 `map_server` 占据栅格，也不是 AMCL
  的 `map -> odom` 定位链。
- 把 hand-authored route graph 当自动楼梯发现。Phase 3C/Phase 4 使用手工 route graph 与
  connector metadata；自动楼梯检测、elevation mapping、traversability 和 connector generation
  仍未完成。
- 把 `nav2_route` 当 3D 地形规划器。它用于 route graph / route tracking，不负责真实楼梯运动学、
  3D traversability 或自动地形语义。
- 把 `gait_type=3` 或 motion profile 元数据当硬件楼梯步态。当前只是保守元数据、phase target
  diagnostics 和 trajectory outlet skeleton，不是调好的 gait controller。
- 把历史文档当当前事实。README、历史验证记录、`docs/superpowers/*`、旧 `/tmp` 证据路径和
  本地 agent 计划文件都不能覆盖当前代码、脚本和 `architecture_state.md`。

## 最容易产生误判和过度自信的模块
- `go2w_navigation`：
  - Phase 3A 在 `odom` frame 下闭环，不代表长期 `map -> odom` 定位方案。
  - DWB abort 可能由目标过短、姿态 yaw 丢失、costmap 参数、stale process 或 controller patience
    引起；不要只看 global path 是否存在。
  - real-model route following 是 regression candidate，不是 production `nav2_route`。
- `go2w_perception`：
  - `odom -> base_link` 当前由 perception path 拥有；不要重新打开 diff-drive controller 的 TF。
  - FAST-LIO external cache 是 repo-local `.go2w_external/`，不是历史 `/tmp` 默认。
  - 点云话题存在不等于 map/localization production chain 完成。
- `go2w_control`：
  - `/stair_exec` 是 dedicated Action，不是 service，也不是 Action-or-Service 二选一。
  - stair executor 的 wheel lock、body-height、leg trajectory 当前是可诊断 skeleton，不是硬件 actuator backend。
  - real-model leg hold outlet 只是显式命令出口，不证明真实楼梯动力学。
- `go2w_mission`：
  - `RunMission` 已有 checkpoint、bounded queue、priority、assignment、operator control、queue replay、
    task history、workflow policy/backend 等窄范围能力，但仍不是完整 production Mission Orchestrator。
  - priority scheduling 当前非抢占 active mission，只影响 queued mission 的激活顺序。
  - assignment policy 当前只是本机 admission gate，不是多机器人调度优化或 cross-robot transfer。
  - flat goal 必须保留 route graph yaw；只传 x/y 会增加 DWB abort 风险。
- Gazebo / runtime：
  - 当前稳定 baseline 是 ROS 2 Humble + Gazebo Fortress-only + `use_gpu:=false`。
  - 不要混入 Gazebo Harmonic / Garden，也不要把 WSLg GPU 渲染当默认合同。
  - 重型 ROS/Gazebo verifier 不要并发跑；并发会制造 lifecycle、discovery、controller 或资源假失败。

## 历史失败经验
- 固定超短目标会失败或产生假成功。Phase 3A 和 real-model hospital gate 都遇到过短目标问题：
  DWB 可报 `No valid trajectories`，planner tolerance 也可能把路径缩到几乎不需要运动。
  后续验证必须用候选目标探测、最小规划路径长度、odom delta 和 `/cmd_vel` 同时判断。
- stale runtime 会污染结果。中断后的 Gazebo、FAST-LIO、perception、Nav2、mission 进程可能留下，
  导致 lifecycle inactive、action timeout 或 TF/topic 假象。先清理残留、换新 `ROS_DOMAIN_ID`，
  再复跑失败命令。
- broad `pkill -f` 容易误杀当前 shell 或调试进程。清理进程要按脚本中已收窄的模式或 PID/进程组做，
  不要在未知环境里随手宽匹配。
- stale install space 会让修复看起来无效。改 Python entrypoint、launch、action 接口或 Nav2/mission
  参数后，必须重建相关包或确认 install space 已更新。
- route graph 生成时机错误会制造假失败。mission real-flat verifier 必须在 perception / mission API
  ready 后重新生成并 reload route graph；过早生成会被 odom 漂移污染。
- route_server sim time 改动有风险。real-model route-tracking gate 曾在把 route_server 切到
  `use_sim_time:=true` 后出现 lifecycle service timeout；没有新证据前不要把这个当默认改法。
- Python pytest 与 pre-handoff 并发会制造 `__pycache__` 假失败。`verify_phase4_pre_handoff.sh`
  会清理并检查源码树缓存，应串行运行。
- 外层 workspace git 状态会误导。曾在 `/home/xiongzx/go2w_ws` 看到与真实 repo 不一致的 git 状态；
  所有 git / verifier / colcon 判断都必须在实际仓库根执行。
- 文档半更新比不更新更危险。新增 verifier 或改能力边界时，必须同步 `architecture_state.md`、
  `current_project_state.md`、相关 `docs/verification/*`、`risk_cleanup_log.md`、
  `next_agent_notes.md` 和 README 摘要；否则下一模型会把旧边界当事实。

## 接手后最应该先确认
1. `cd /home/xiongzx/go2w_ws/src/go2w_navigation_stack && pwd`
2. `git status --short --branch`
3. `git log --oneline -5`
4. `./tools/verify_phase4_pre_handoff.sh`
5. 是否存在上一轮未提交改动；逐个判断哪些是已验证事实、哪些只是实验性改动。
6. 当前 `architecture_state.md` 的 Active Phase 和未完成能力。
7. 当前任务是否有完整 6 项任务单；若处于自主审批模式，也要先写自批准任务单。
8. `.go2w_external/workspaces/fast_lio_ros2/install/setup.bash` 是否存在；缺失时先跑 external prep。
9. ROS/Gazebo 残留进程是否清干净；重型 verifier 运行前优先用清理脚本和新 domain。
10. 目标能力需要的证据层级：静态解析、build、pytest、runtime topic/TF/lifecycle/action、docs evidence。

## 最不该直接假设
- 不要假设 README 最新。
- 不要假设旧日志目录仍存在或仍代表当前代码。
- 不要假设 GUI 里看见机器人就等于 navigation closed loop 成立。
- 不要假设 `/plan` 出现就等于 controller 成功执行。
- 不要假设 `NavigateToPose` 成功就等于路径长度和 odom 位移足够。
- 不要假设点云地图已经等于 2D SLAM / AMCL。
- 不要假设 real-model path 能直接替换 default baseline。
- 不要假设 Mission API 的 workflow/event/history 就是 fleet-level production orchestrator。
- 不要假设 `/stair_exec` skeleton 能爬真实楼梯。
- 不要假设外部官方模型或开源资料可以无缝替换当前接口；必须适配 ROS 2 Humble、
  Gazebo Fortress、Nav2、TF authority 和现有包边界。

## 新项目重启时的建议原则
- 先建立最小可重复闭环，再换更复杂模型或地图。
- 模型、仿真 world、SLAM、规划、控制和任务调度要分层验收；不要一次把所有失败混在一起调。
- 每个能力都要有“输入、输出、判断条件、失败日志、复跑命令”。
- 可视化演示和自动化验收分开做。演示用于人看，验收用于防止幻觉。
- 引入开源资产时先锁定来源、许可证、ROS/Gazebo 版本和接口差异，再写 adapter。
- 任何“完成”都必须能指向代码、配置、脚本、测试或 runtime evidence；否则只能写
  `部分完成`、`未完成` 或 `无法确认`。

## 给下一个模型的最低启动命令
```bash
cd /home/xiongzx/go2w_ws/src/go2w_navigation_stack
pwd
git status --short --branch
git log --oneline -5
./tools/verify_phase4_pre_handoff.sh
```

若继续做 GUI / RViz / Gazebo 演示，还必须额外确认：

```bash
source /opt/ros/humble/setup.bash
ros2 topic list
ros2 node list
ros2 action list
```

并把实际可见效果与自动化证据分开记录。
