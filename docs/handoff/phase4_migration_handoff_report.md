# Phase 4 迁移前交接总报告

## 1. 项目总目标
构建 Go2W 跨楼层自主导航巡检系统的 ROS 2 Humble 主仓库。路线是
simulation-first：先在 Gazebo/RViz 中打通仿真、控制、FAST-LIO、Nav2、
route graph 和楼梯行为交接，再逐步升级到高程图、可通行性和自动楼梯连接器。

## 2. 当前阶段位置与整体路线
当前正式阶段是 `Phase 3`，Phase 3 已验收。尚未进入 `Phase 4A`。

阶段路线：
- Phase 0：接口契约与系统边界。
- Phase 1：仿真可控、可观测。
- Phase 2：FAST-LIO 定位/建图基础。
- Phase 3：同层 Nav2 导航与 route graph 骨架。
- Phase 4：楼梯状态机与控制权交接闭环。
- Phase 5：高程/可通行性/自动连接器。

## 3. 核心环境与依赖条件
- Ubuntu 22.04 / WSL2。
- ROS 2 Humble。
- Gazebo Fortress-only：`ignition-gazebo6` / `ign gazebo-6`。
- `ros-humble-ros-gz-*` 与 `ros-humble-gz-ros2-control`。
- Gazebo 默认软件渲染：`use_gpu:=false`。
- FAST-LIO 源码不 vendor 入仓库，默认使用 ignored repo-local cache：
  `.go2w_external/`。

不要混入 Gazebo Harmonic/Garden，不要默认启用 Gazebo GPU rendering。

## 4. 当前技术路线和架构思路
系统严格分层：
- simulation 只负责 Gazebo 与传感器。
- perception 负责 FAST-LIO、里程计、点云、TF authority。
- navigation 负责 Nav2、costmap、planner/controller、route server。
- mission 未来负责目标语义、楼层语义和分段调度。
- control 未来负责最终 locomotion mode 与 stair execution。

冻结接口：
- TF 最小链：`map -> odom -> base_link`。
- `odom -> base_link` 当前由 perception path 声明。
- 平地连续运动入口：`cmd_vel`。
- 楼梯入口：dedicated `stair_exec` Action。
- `nav2_route` 只做 route graph/route tracking，不是 3D 地形规划器。

## 5. 关键模块与职责划分
- `go2w_description`：占位机器人模型与 RViz 配置。
- `go2w_sim`：Gazebo Fortress launch、worlds、bridge、controller orchestration。
- `go2w_perception`：FAST-LIO contract adapters 与 TF authority。
- `go2w_navigation`：Nav2/costmap/route graph 配置与 launch。
- `go2w_control`：未来 locomotion mode 与 stair executor 实现。
- `go2w_mission`：未来 floor-aware mission orchestration。

## 6. 到目前为止已完成的内容
- Phase 1 仿真底盘控制闭环。
- Phase 2 FAST-LIO 输入输出与 perception-owned `odom -> base_link`。
- Phase 2H 首个 Nav2 costmap consumer gate。
- Phase 3A 同层 Nav2 navigation closed loop。
- Phase 3B `nav2_route` same-floor manual graph baseline。
- Phase 3C repo-local FAST-LIO external cache、多楼层 route graph/map metadata、
  hospital world asset。

## 7. 当前真实状态
仓库已具备同层 SLAM/感知基础与 Nav2 同层闭环的可审计证据，也具备 Phase 4
所需的手工多楼层 route graph 与 hospital world 资产。但它还不是完整跨楼层
自主系统：mission runtime、stair executor runtime、真实楼梯控制、自动连接器
均未实现。

## 8. 本次已清理/已修复的问题
- 修复活动 FAST-LIO 验证脚本仍默认 `/tmp` 的路径漂移。
- 修复 Phase 2C patch/audit 工具默认路径落后于 Phase 3C 的问题。
- 清理源码侧 Python 缓存目录。
- 新增集中交接包，降低新对话上下文失真风险。
- 新增 Phase 4 迁移前静态验证脚本。

## 9. 仍然存在但暂不可修复的风险或限制
- Gazebo GPU rendering 在当前 WSLg/Fortress/Ogre2 路径下仍不稳定。
- Unitree Go2W 真实模型未导入，当前仍是 placeholder 模型。
- Phase 3C route graph 是手工 floor atlas，不是自动地图生成。
- 没有 production Mission Orchestrator。
- 没有 Stair Executor runtime。
- 没有 `map_server` / AMCL / `map -> odom` 闭环。
- 没有 elevation mapping、traversability 或 automatic stair detection。

## 10. Phase 4 的直接起点
Phase 4A 应从最小楼梯状态机/控制权交接骨架开始。建议边界：

- 输入：Phase 3C 手工 route graph 中的 staircase connector metadata。
- 行为：检测/模拟进入楼梯边时暂停或隔离 Nav2 控制权。
- 调用：触发 dedicated `stair_exec` Action 的最小 mock/skeleton。
- 输出：楼梯段完成后恢复平地导航控制权。
- 验收重点：状态机流转、控制权互斥、接口可观测、失败信号可诊断。

Phase 4A 不应包含真实楼梯运动控制调参、多楼层自主任务闭环、自动楼梯发现、
elevation mapping、traversability、Unitree model import 或 perception TF 改造。

## 11. 推荐先跑的验证
```bash
./tools/verify_phase4_pre_handoff.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select go2w_perception go2w_navigation go2w_description go2w_sim
colcon test --packages-select go2w_perception go2w_navigation go2w_description go2w_sim
colcon test-result --verbose
```
