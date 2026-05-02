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
| 真实 route tracking 仍停留在 verifier skeleton | Phase 4D-min 只在 mission-owned observer 内消费反馈，不能直接证明 live `nav2_route` route_server 行为 | 新增 Phase 5A live route tracking observation gate、`tools/verify_phase5a_live_route_tracking.sh` 与 `docs/verification/phase5a_live_route_tracking.md`，在受控 TF trajectory fixture 下直接观察真实 `nav2_route` `route_server`、`ComputeAndTrackRoute` feedback、`500` 连通边和 `AdjustSpeedLimit` | 已修复 |
| Unitree Go2W 真实模型未导入 | placeholder 两轮模型无法代表真实 Go2W 关节、foot wheel、传感器挂点和站立初始化 | 新增 opt-in `go2w_real.urdf`、官方 mesh 资产、`sim_go2w_real.launch.py`、四 foot wheel `diff_drive_controller`、腿部 position controller、`go2w_stand_initializer` 和 `tools/verify_go2w_real_model_baseline.sh` | 已部分修复 |
| 真实模型 headless controller 激活初版超时 | 首轮 real-model verifier 中 `joint_state_broadcaster` 使用默认 5 秒 switch timeout，且 foot wheel mesh collision 使 Gazebo 控制器激活变慢 | 将四个 foot wheel collision 简化为与控制半径一致的圆柱，并给 real-model spawner 设置显式 `--switch-timeout` / `--service-call-timeout` | 已修复 |
| Real-model baseline verifier 过度依赖 spawner 日志 | `joint_state_broadcaster` 偶发出现加载重试和已加载提示，但 controller 之后仍可进入 `active`，单看 `Configured and activated` 日志会误判失败 | 改为轮询 `ros2 control list_controllers` 的真实 controller state，记录 `controller_states_ready` 再做 active 断言 | 已修复 |
| 真实模型同层 route-following 初版失败 | real-model Nav2 目标开始后出现 costmap sensor origin 越过下边界的警告，随后一次修正又把 `z_voxels` 提到 22，触发 voxel grid 上限错误 | 新增 `go2w_navigation/config/phase5_real_model_nav2_same_floor.yaml` 和 `tools/verify_go2w_real_model_route_following.sh`，最终采用 `robot_radius: 0.28`、`footprint_padding: 0.01`、`origin_z: -0.40`、`z_voxels: 16` 并通过短同层 `NavigateToPose` 验证 | 已修复 |
| Stair executor 的 motion profile 基线仍是隐式的 | `go2w_stair_executor` skeleton 只发固定 stair cmd，没有明确复用 Go2W legged profile | `StairExecutionPolicy` 现在读取 legged motion profile、发布保守 stair 线速度上限，并补充 unit tests；Phase 4A runtime 重新验证未回归 | 已修复 |
| Stair executor 仍没有显式 leg hold 命令出口 | 仅有 `/go2w/control/stair_cmd_vel` 还不足以让 stair skeleton 对接 legged posture baseline | `go2w_stair_executor` 现在在 stair owner 激活时发布 12 关节 leg hold command 到 `/leg_position_controller/commands`，并通过单测与 Phase 4A runtime 复验 | 已修复 |
| Phase 4 verifier domain id 可能越过 Fast-DDS 可用范围 | Phase 4D 初版曾生成过高 `ROS_DOMAIN_ID`；Phase 4C 旧公式理论上也可能超过 231 | Phase 4C/4D verifier 统一使用 `(($$ % 90) + 130)` 范围，避免 domain 范围型假失败 | 已修复 |
| Mission API skeleton 包形态与 launch 参数不兼容 | `go2w_mission` 初版同时使用 `ament_python_install_package(${PROJECT_NAME})` 和 `rosidl_generate_interfaces`，且入口直接严格解析 `--ros-args` | 改为显式安装 Python 源码目录、保留 action 生成、并让入口使用 `parse_known_args()` + `rclpy.init(args=...)` 处理 launch 追加参数 | 已修复 |
| Phase 4 缺少总验收入口 | Phase 4A/4B/4C/4D 已有独立 verifier，但缺少一键串联的 Phase 4 完整验收证据 | 新增 `tools/verify_phase4_runtime_acceptance.sh` 和 `docs/verification/phase4_runtime_acceptance.md`，串联 pre-handoff、Phase 4A/4B/4C/4D、build/test 和 `colcon test-result` | 已修复 |
| real-model stair fixture 中 `/stair_exec` 缺少 phase-aware 闭环证据 | 旧证据只证明 `/stair_exec` skeleton 和 leg hold outlet，不足以观察 wheel lock/body-height/release 序列 | 新增 phase-aware stair executor plan/state、`/go2w/control/stair_execution_state` 诊断输出和 `tools/verify_phase4e_stair_fixture.sh`，验证 real-model fixture 下 action 成功、owner/mode 互斥和完整阶段序列 | 已修复 |
| 官方 Unitree 资料里的 motion-state 示例可能被误读为 stair tuning 已完成 | `unitree_ros2` README 同时展示了 gait enum（含 `3.climb stair`）和一个 `gait type: 1` 的示例输出，容易把“字段存在”误判成“楼梯步态已调好” | 在 `go2w_control/go2w_control_runtime/motion_profiles.py` 和风险文档中明确：当前 `body_height=0.32`、`foot_raise_height=0.09`、`gait_type=3` 只是保守元数据基线，不是硬件已调参结论 | 已修复 |
| stair executor 的楼梯参数缺少显式 tuning 入口 | 旧代码只允许 `stair_linear_velocity_mps` 覆盖，后续很难在不改默认基线的前提下做 stair tuning 试验 | 增加 `--stair-body-height-m`、`--stair-foot-raise-height-m`、`--stair-gait-type`、`--stair-speed-level`、`--stair-max-linear-velocity-mps`，默认仍保持保守 baseline | 已修复 |
| stair tuning override 的验证路径缺失 | 代码支持覆盖参数后，如果没有独立 smoke test，后续很容易把 tuning 误判成 baseline 漂移 | 新增 `tools/verify_phase4e_stair_tuning_overrides.sh`，使用同一 real-model fixture 复跑并确认默认 baseline 不变时仍能闭环 | 已修复 |
| leg trajectory / wheel lock / body height transition 没有最小可审计策略骨架 | 真实控制接口尚未引入，若直接宣称控制完成会越界 | 将 `prepare,wheel_lock,body_height_transition_down,execute_stairs,body_height_transition_up,release` 建成可诊断 phase plan；leg trajectory 当前明确为 12-joint conservative hold，不伪造不存在的 body-height 控制通道 | 已部分修复 |
| Mission API 缺少状态持久化和恢复路径 | 旧 `RunMission` skeleton 是单次 action 调度，失败后没有可恢复 checkpoint | 新增 `mission_recovery.py`、JSON state store、same-goal resume、有限 retry 和 `tools/verify_phase4e_mission_recovery.sh`，验证 stair-unavailable 后从 segment index `1` 恢复到成功 | 已部分修复 |
| real-model path 是否扩大为 regression 或默认基线缺少结论 | 真实模型已有 baseline 与短同层 route-following，但不足以安全替换默认 placeholder | 新增 opt-in `tools/verify_go2w_real_model_regression.sh` 串联 baseline、route-following、stair fixture；明确不切默认基线 | 已修复 |
| 迁移前交接材料容易把 route-following 历史 PASS 误读成稳定门禁 | 后续硬化运行显示 route-following 仍可能在 DWB 局部规划阶段 abort，而部分文档仍突出 real-model regression PASS | 新增并置顶稳定 `tools/verify_go2w_control_chain_regression.sh` 口径，更新 handoff 索引、总报告、当前状态、注意事项和 regression 文档，明确 route-following 只是独立 opt-in smoke | 已修复 |
| `verify_go2w_real_model_regression.sh` 使用未定义 `REPO_ROOT` | 脚本在 cleanup 阶段调用 `${REPO_ROOT}/tools/cleanup_sim_runtime.sh`，但文件顶部只定义了 `SCRIPT_DIR` | 补充 `REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"`，并纳入 bash/shellcheck 验证 | 已修复 |

## 保留但已标注的历史内容
- `docs/superpowers/` 中的早期 Phase 2/3 计划和设计文档保留为历史记录。
- `docs/verification/` 中早期 `/tmp` 证据路径保留为当时采证结果。
- 不重写历史证据，避免破坏审计链；当前默认策略以 `architecture_state.md`、
  `README.md`、本目录和当前脚本为准。

## 仍存在但暂不可在本任务修复

| 限制 | 原因 | 后续处理 |
| --- | --- | --- |
| Gazebo GPU rendering 仍不纳入默认基线 | WSLg + Gazebo Fortress/Ogre2 `use_gpu:=true` 已验证不稳定 | 保持 Gazebo `use_gpu:=false`，RViz/CUDA 链路单独验证 |
| 占位 URDF 耦合 geometry/control/sensors | 旧 `sim.launch.py` 默认路径仍保留 placeholder 以保护既有 Phase 1-5 验证链 | 后续独立任务决定是否切默认或拆分模型/仿真传感器职责 |
| 真实 Go2W 模型尚未成为默认仿真基线 | 当前 real-model 路径是 opt-in，已覆盖 baseline、最小同层 route-following 和 Phase 4E stair fixture regression，但尚未覆盖所有历史验收，也未证明真实楼梯动力学 | 后续 default re-baseline 任务再决定是否替换默认；当前结论是保留 opt-in wrapper |
| real-model same-floor route-following 仍有 spawn-state 相关 abort | `ComputePathToPose` preflight 可返回非空路径，但 `NavigateToPose` 在部分启动姿态下仍会进入 DWB `No valid trajectories` / `Controller patience exceeded` | 当前将 route-following 保留为独立 opt-in smoke，并从稳定 `verify_go2w_control_chain_regression.sh` 中拆出；后续用 dedicated Nav2 real-model tuning 任务处理 |
| Phase 3C route graph 是手工 floor atlas | 目的是给 Phase 4 手工连接器提供基线，不是自动建图结果 | Phase 4 先证明控制交接；Phase 5 再自动连接器 |
| 没有完整 production Mission Orchestrator | 当前已有 `RunMission` skeleton、JSON checkpoint、同一 goal resume 和有限 retry，但仍不是完整长生命周期调度器 | 后续用独立完整任务单推进多任务队列、操作员恢复策略、优先级调度和更持久的状态后端 |
| Phase 4C-min flat executor 仍是 verifier skeleton | 本阶段只证明 mission 到 navigation-owned `NavigateToPose` gate 的调度；当前 real-model short `NavigateToPose` verifier 尚未替换 mission runtime skeleton | 后续 production mission / real route-tracking integration 任务处理 |
| 真实楼梯执行控制器调参仍未覆盖 | Phase 4E 已补 phase-aware `/stair_exec` fixture、wheel lock/body-height/release 诊断和 leg hold outlet，但仍不覆盖物理楼梯运动学 | 后续 dedicated stair trajectory / gait tuning 任务处理 |
| ROS discovery/lifecycle 偶发等待 | 曾有一次 Phase 4B 回归中 `route_server` 进程已启动但 lifecycle service 未被发现；换新 domain 复跑通过 | 先清理残留并换新 `ROS_DOMAIN_ID` 复跑；若复现，再单独加 discovery 诊断 |
| 没有 `map -> odom` 定位融合链 | Phase 3A 有意运行在 `odom`，Phase 3C 只提供 `map` 资产 | 后续定位/地图服务任务单再引入 |
