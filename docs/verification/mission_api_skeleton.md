# Mission API Skeleton 验收记录

## 目的
验证 `go2w_mission` 内新增的 `RunMission` Action skeleton 是否可以在 ROS 2 Humble 环境下稳定运行，并对成功、无效目标、取消、以及 flat action 不可用路径给出可诊断结果。

## 结论
- `RunMission` Action contract 已生成并可被 `go2w_mission_api` 使用。
- Mission API launch 能同时拉起 `route_server`、`go2w_command_gate`、`go2w_stair_executor`、`go2w_flat_nav_executor` 和 `go2w_mission_api`。
- 成功、无效目标、取消、flat action 不可用四条路径都已通过 verifier。
- mission API 和 Phase 4B runtime 的 flat goal 姿态转换现在共用 `mission_pose` helper，
  目标 yaw 不再在两条路径之间分叉。
- 这仍然是 skeleton，不是 production Mission Orchestrator，也不等于真实机器人运动上的 route tracking 或楼梯动力学。

## 额外硬化
- `MissionApiRuntime` 现在在进入执行前会争抢单飞 admission slot。
- 并发 `RunMission` goal 会返回 `MISSION_BUSY` / `mission_state_in_use`，而不是同时竞争单一 JSON state file。
- flat goal 现在通过共享 yaw-preserving helper 进入真实 Nav2 路径，避免 mission API 和
  Phase 4B runtime 的 orientation 语义不一致。
- 这仍然不是 multi-mission queueing，也不是 priority scheduling。

## 变更文件
- `go2w_mission/action/RunMission.action`
- `go2w_mission/go2w_mission/mission_api.py`
- `go2w_mission/launch/mission_api.launch.py`
- `go2w_mission/scripts/go2w_mission_api`
- `go2w_mission/CMakeLists.txt`
- `go2w_mission/package.xml`
- `go2w_mission/test/test_mission_api_skeleton.py`
- `tools/verify_mission_api_skeleton.sh`

## 验证命令
```bash
PYTHONPATH=go2w_mission python3 -m pytest go2w_mission/test/test_mission_api_skeleton.py -q
python3 -m py_compile go2w_mission/go2w_mission/mission_api.py go2w_mission/launch/mission_api.launch.py go2w_mission/test/test_mission_api_skeleton.py
bash -n tools/verify_mission_api_skeleton.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_control go2w_navigation go2w_mission
colcon test --packages-select go2w_mission
colcon test-result --verbose
source /opt/ros/humble/setup.bash && ./tools/verify_mission_api_skeleton.sh
```

## 结果摘要
- `pytest`: 3 passed
- `colcon build`: `go2w_control`、`go2w_navigation`、`go2w_mission` 成功
- `colcon test-result --verbose`: `75 tests, 0 errors, 0 failures, 0 skipped`
- `./tools/verify_mission_api_skeleton.sh`: `mission_api_success: PASS`、`mission_api_invalid_goal: PASS`、`mission_api_cancel: PASS`、`mission_api_unavailable_action: PASS`、`mission_api_skeleton_result: PASS`

## 关键约束
- Mission API 只编排现有 `ComputeRoute`、`NavigateToPose`、`/stair_exec` skeleton。
- `RunMission` 结果码用于诊断，不代表 production recovery strategy 已实现。
- flat action 不可用时的诊断必须保持可复现。
- 该 skeleton 不修改 `odom -> base_link` 归属，不引入 `map_server` / AMCL / elevation mapping / traversability。

## 后续风险
- 现在只验证了 skeleton 级路由分段和动作调度，不等于真实楼梯动力学。
- 生产级 Mission Orchestrator、恢复策略、状态持久化仍未实现。
- 并发 admission race 已被单飞 gate 收口，但真正的任务队列和优先级调度仍需独立任务单。
- 后续若扩展真实楼梯控制，必须先单独写完整任务单，不要顺手把本 skeleton 直接改成最终版。

## 追加验证
- Date: `2026-05-02`
- Command:

```bash
PYTHONPATH="$PWD/go2w_mission" python3 -m pytest go2w_mission/test/test_mission_api_skeleton.py -q
```

- Result:

```text
7 passed in 0.02s
```

- Key result:

```text
test_mission_api_single_flight_admission_gate_is_non_blocking: PASS
```

## 2026-05-04 硬化复验
- Command:

```bash
PYTHONPATH="$PWD/go2w_mission" python3 -m pytest go2w_mission/test/test_phase4b_mission_runtime.py go2w_mission/test/test_mission_api_skeleton.py -q
source /opt/ros/humble/setup.bash && ./tools/verify_mission_api_skeleton.sh
```

- Result:

```text
16 passed in 0.03s
mission_api_success: PASS
mission_api_invalid_goal: PASS
mission_api_cancel: PASS
mission_api_unavailable_action: PASS
mission_api_skeleton_result: PASS
```

- Verified facts:
  - `MissionApiRuntime` 的单飞 admission gate 仍是非阻塞锁。
  - 并发入口仍返回 `MISSION_BUSY` / `mission_state_in_use`，不是隐式 queue。
  - mission API 和 Phase 4B runtime 均通过共享 `mission_pose` helper 做 flat goal yaw conversion。
