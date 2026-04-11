# Interface Contracts

## Purpose
This document freezes the first-generation system interface contracts for the Go2W cross-floor navigation stack.

Its purpose is to ensure that:
- algorithms may evolve,
- route graph generation may evolve,
- terrain understanding may evolve,
- but the cross-layer interfaces do not drift without explicit approval.

This file is the canonical boundary contract between:
- simulation
- control
- perception
- navigation
- mission orchestration

---

## 1. Package Ownership Contract

### `go2w_description`
Owns:
- URDF / Xacro
- meshes
- static robot frames
- robot_description publication inputs

Must not own:
- controllers
- navigation logic
- mission logic
- SLAM logic

### `go2w_sim`
Owns:
- Gazebo Sim worlds
- robot spawn
- sensor simulation setup
- ros_gz_bridge / gz_ros2_control connection assets
- simulation launch entrypoints

Must not own:
- planner logic
- route graph logic
- FAST-LIO algorithm logic
- mission orchestration

### `go2w_control`
Owns:
- locomotion mode abstraction
- low-level command arbitration
- wheel / stair mode switching
- staircase execution interface implementation
- safe command gating during behavior handoff

Must not own:
- route graph generation
- floor semantics reasoning
- global path planning
- map generation

### `go2w_perception`
Owns:
- FAST_LIO_ROS2 integration
- odometry publication contract
- point cloud publication contract
- map save / load support if introduced
- perception-side time sync / frame alignment policy

Must not own:
- navigation policy
- mission decisions
- locomotion mode switching policy
- route graph management

### `go2w_navigation`
Owns:
- Nav2 stack integration
- costmap configuration
- planner/controller configuration
- BT Navigator integration
- nav2_route integration
- route graph loading and route execution plumbing

Must not own:
- low-level control implementation
- mission-level floor reasoning
- automatic stair perception logic
- sensor fusion internals

### `go2w_mission`
Owns:
- mission goal semantics
- floor-aware task decomposition
- route segmentation into flat/stair sections
- top-level orchestration and recovery policy
- connector source selection policy

Must not own:
- continuous velocity control
- direct motor actuation
- low-level SLAM internals
- detailed controller tuning

---

## 2. Data Flow Contract

The system data flow is strictly one-way by default:

Simulation / Sensors
→ Perception
→ Navigation / Costmap / Route
→ Mission Interpretation
→ Control Mode Request
→ Low-level Execution

### Mandatory data-flow rule
Perception data may influence mission and navigation,
but raw perception outputs must not directly command locomotion.

### Examples
Allowed:
- point cloud updates costmap
- odometry updates route tracking
- connector generator updates route graph candidate set

Forbidden:
- point cloud directly switches stair mode
- raw elevation map directly commands wheel torque behavior
- mission node publishes motor-like commands continuously

---

## 3. Control Flow Contract

Control flow is explicitly stateful and must be mediated through mission / navigation / control handoff.

### Required top-level sequence
1. Goal intake
2. Mission interpretation
3. Route computation / tracking
4. Flat segment execution via navigation stack
5. Stair segment handoff via staircase executor
6. Return to navigation after staircase completion

### Hard rule
Only `go2w_control` may own the final locomotion mode switch execution.

Mission and navigation layers may request or trigger mode transitions,
but they must not embed low-level switching implementation.

---

## 4. TF Contract

### Canonical chain
The minimum stable TF chain is:

`map -> odom -> base_link`

Additional sensor frames hang below `base_link`.

### Interpretation
- `map`: global mission/navigation reference frame
- `odom`: locally continuous tracking frame
- `base_link`: robot body frame

### Freeze rule
No package may publish duplicate authority over the same TF edge without explicit approval.

### Implication
If FAST_LIO_ROS2 is introduced as odometry authority,
all competing publishers for the same odom-related transform must be identified and resolved.

---

## 5. Motion Command Contract

### Flat-ground command channel
Flat-ground navigation uses a normalized velocity-style interface.

Current contract:
- floor-level continuous motion requests enter through a navigation command channel equivalent in role to `cmd_vel`

### Stair execution command channel
Stair traversal must use a dedicated behavior-level interface.

Current contract:
- staircase traversal is requested through a dedicated staircase execution Action named `stair_exec`
- it must not be tunneled through generic `cmd_vel`

### Why this is frozen
This separation is required so that:
- navigation and staircase execution do not fight for control,
- Phase 4 manual connector workflow remains valid,
- Phase 5 connector automation can replace trigger source without changing execution API.

---

## 6. Route / Mission Contract

### `nav2_route` role
`nav2_route` is treated as:
- graph route computation
- route tracking
- route-linked operation triggering

It is **not** treated as:
- a 3D terrain traversal planner
- an automatic stair detector
- a direct low-level controller

### Multi-floor contract
Cross-floor traversal is represented through:
- floor-specific route graph structure
- staircase connector nodes / edges
- mission-layer floor semantics
- behavior trigger handoff at connector boundaries

### Freeze rule
From Phase 4 to Phase 5,
the staircase executor API must remain stable.
Only the connector source and route graph generation / update path may be replaced.

---

## 7. Phase Evolution Contract

### Stable across Phase 4 → Phase 5
The following interfaces are intended to remain stable:
- low-level locomotion mode request contract
- staircase executor request/response contract
- route-to-mission handoff semantics
- mission-to-control high-level behavior request boundary

### Allowed to evolve in Phase 5
The following may be replaced or upgraded:
- manual staircase connector source
- route graph generation pipeline
- traversability scoring source
- terrain-aware connector discovery logic

### Forbidden evolution pattern
Do not replace control interfaces when upgrading terrain perception.

The new terrain perception pipeline must adapt to existing stable execution contracts.

---

## 8. Error and Recovery Contract

### Recovery ownership
- local navigation recovery belongs to navigation layer
- staircase execution failure recovery belongs to mission + control handoff logic
- perception degradation reporting belongs to perception layer

### Mandatory rule
Each layer must emit diagnosable failure signals upward.
No layer may silently absorb a major execution failure.

### Minimum expectation
A failed cross-floor attempt should be classifiable as one of:
- perception unavailable
- route unavailable
- connector unavailable
- staircase execution failed
- control handoff failed
- localization unstable

---

## 9. Interface Change Policy

Any proposed interface change must explicitly state:
- why the current contract is insufficient,
- which phase requires the change,
- which packages are affected,
- whether backward compatibility is preserved,
- what new DoD justifies the break.

Without this justification, interfaces are considered frozen.

---

## 10. Initial Canonical Principles

1. Closed loop before sophistication.
2. Stable interfaces before algorithm swapping.
3. Mission decides “when”.
4. Navigation decides “where”.
5. Control decides “how”.
6. Perception informs but does not directly actuate.
7. Stair capability is a replaceable behavior, not a hidden side effect.
