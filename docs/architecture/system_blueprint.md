# Go2W 跨楼层自主导航巡检系统全生命周期技术路线总蓝图

## 0. 核心架构共识 (Executive Summary)
本蓝图以**“先闭环再升维，严禁过早优化”**为唯一工程准则：先用可验证的接口把 仿真—控制—里程计—导航—多楼层拓扑调度 闭环跑起来，再逐步引入高程/可通行性与自动楼梯识别。
关键推演结论：
1. `nav2_route` 是原生可用的路线图路由基础设施，但其路由图本质是二维坐标（x,y），多楼层必须通过“楼梯终端节点 + 行为触发 + 上层任务编排”来完成，绝不能期待它直接做 3D 地形通行推理。
2. 从 Phase 4（拓扑图强行触发楼梯状态机）进化到 Phase 5（高程图自动识别楼梯）时，替换的必须是“连接器来源与路由图生成模块”，绝不替换楼梯执行器的动作接口。
3. `nav2_route` 的路线跟踪与“Route Operation”机制天然适合做“进入/退出楼梯边时触发底层控制器模式切换”。

---

## 1. 系统工程总体架构设计

### 1.1 分层架构概览
系统按“硬件/仿真—基础感知—导航执行—拓扑路由—地形升维”分层，严格区分**数据流**与**控制流**，并将“楼梯能力”限定为可插拔的行为模块。

### 1.2 数据流（Data Flow）
* **仿真与驱动数据源**：优先采用现代 Gazebo（Gazebo Sim）并使用 `gz_ros2_control` 连接 controller manager。绝不使用即将淘汰的 Gazebo Classic。
* **基础感知**：引入 `FAST_LIO_ROS2` (Humble wrapper) 作为高频里程计与建图前端。
* **导航环境表征**：早期采用“局部滚动 costmap + 拓扑路由图约束”。利用 `nav2_costmap_2d` 的体素层将 `PointCloud2` 数据压扁到 2D 用于平地避障。

### 1.3 控制流（Control Flow）
控制流由“任务编排器”主导，核心是把 RViz 里的“3D 巡检目标”转化为可执行的**分段任务**：
1. **目标输入层**：发布 3D goal（包含 Pose 与 floor 元数据）。
2. **顶层任务编排器 (Mission Orchestrator)**：向 `nav2_route` 发起路线请求，把 route 分解为楼层内段（flat）与楼梯连接段（stairs）。
3. **Nav2 执行层**：平地走 Nav2 标准“规划—跟踪”链；楼梯段触发楼梯执行器（Stair Executor），完成后返回 Nav2。
4. **底层控制层 (go2w_control)**：根据上层模式切换轮/足控制策略，保持接口绝对稳定。

---

## 2. 核心 Package 矩阵与职责划分
新仓库强制划分为 6 个核心 ROS 2 包，并设立**不可越界的职责边界**。

| Package | 责任边界一句话定义 | 关键接口形态 |
| :--- | :--- | :--- |
| `go2w_description` | 仅负责 Go2W 机器人模型描述，不包含控制算法。 | `/robot_description`、TF 静态树 |
| `go2w_sim` | 仅负责 Gazebo Sim 启动、传感器配置、与 `gz_ros2_control` 的连通。 | Gazebo world、传感器 topics |
| `go2w_control` | 仅负责底层控制与 locomotion mode 切换（轮/足），不包含导航。 | `cmd_vel` 接收、Mode 切换 Action/Service |
| `go2w_perception` | 仅负责 FAST-LIO2 集成与 TF/时间同步策略，不做规划。 | odom、点云、地图持久化 |
| `go2w_navigation` | 仅负责 Nav2 与 `nav2_route` 配置、BT 组合、costmap/planner 策略。| Nav2 actions、route actions |
| `go2w_mission` | 仅负责“3D 目标 → 分段任务 → 执行调度”的顶层编排（含楼层概念）。| Mission Action、RouteGraph 管理 |

---

## 3. 阶段性任务拆解与验收标准

### Phase 0：系统边界与接口契约冻结
* **核心目标**：冻结系统的 Topic/TF/Action/Service 命名规范与责任边界。
* **关键任务**：定义 TF 最小闭环（`map -> odom -> base_link`）；定义控制层入口（平地用 `cmd_vel`，楼梯用 dedicated staircase execution `stair_exec` Action）；初始化 `architecture_state.md`。

### Phase 1：仿真可控（平地可驱动、可观测）
* **核心目标**：在 Gazebo Sim + RViz 中让 Go2W 达到最低闭环，能用 `cmd_vel` 驱动轮式移动。
* **关键任务**：提取模型与世界资产；打通 `gz_ros2_control` 与 `ros_gz_bridge`。
* **验收标准**：给定 `cmd_vel`，Gazebo 中运动可平滑复现；RViz 能看到点云与正确的 TF。

### Phase 2：建图基石（FAST-LIO2 稳定输出）
* **核心目标**：跑通 `FAST_LIO_ROS2`，输出高频里程计与点云地图。
* **关键任务**：对齐 TF，确保 FAST-LIO 发布的里程计语义正确，解决多重发布冲突。
* **验收标准**：仿真中连续运行不发散；Nav2 costmap 能成功消费其输出的点云进行障碍更新。

### Phase 3：拓扑路由与楼层内导航
* **核心目标**：完成“同层导航 + 拓扑骨架”闭环。
* **关键任务**：启用 `nav2_route`；建立手工标注的最小路线图（GeoJSON）；组装 Route Server 与 BT Navigator。
* **验收标准**：在 RViz 发送同层目标点，机器人能规划、避障并到达；能可视化 Route Graph。

### Phase 4：楼梯状态机闭环
* **核心目标**：用人工标注的拓扑图强行触发楼梯执行器，跑通跨楼层逻辑。
* **关键任务**：利用 `ComputeAndTrackRoute` 的反馈与 Route Operation 机制，在进入楼梯边时拦截 Nav2 控制权，触发底层爬楼模式。
* **验收标准**：仿真中能跑完“平地导航 → 触发楼梯执行 → 恢复下一层导航”的完整闭环，且控制权交接互斥。

### Phase 5：高程地形感知引入 (远期)
* **核心目标**：基于高程表征自动发现楼梯，动态更新拓扑连接边。
* **关键任务**：引入 `grid_map` 与高程建图算法（如 `elevation_mapping_gpu_ros2`）；将通行性结果动态注入 `nav2_route` 的边代价中。
* **验收标准**：取消手工楼梯标注，系统能在新场景中自主发现楼梯并更新路由图。

---

## 4. 架构风险预警与技术债管理

1. **仿真物理真实性缺失**：Gazebo 很难完美复现真实的四足爬楼动力学。
   * *应对*：Phase 4 的 DoD 只验证“接口握手与状态机流转”，不纠结于爬楼动作是否完美，将动力学验证推迟到真机阶段。
2. **多楼层二维投影歧义**：二维路由图在同一 x/y 坐标可能对应多层节点。
   * *应对*：跨层任务必须由 Mission 层显式指定 `start_id` 和 `goal_id` 及楼层属性，避免 KD-tree 最近邻搜索引发的歧义。
3. **接口防腐**：任何感知“升维”算法（如高程图）只能作为 Mission 层的插件，绝不允许直接污染底层控制或 Nav2 的核心配置。
