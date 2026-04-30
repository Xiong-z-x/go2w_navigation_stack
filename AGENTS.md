# AGENTS.md

## Project Identity
This repository is the main monorepo for the **Go2W cross-floor autonomous navigation and inspection system**.

The project goal is:

> From zero, build a ROS 2 Humble based simulation-first navigation stack for Unitree Go2W that can:
> 1. receive a user navigation goal from RViz,
> 2. execute floor-level navigation in Gazebo Sim,
> 3. perform cross-floor traversal through staircase behavior handoff,
> 4. maintain localization / mapping through FAST_LIO_ROS2,
> 5. evolve later toward terrain-aware automatic stair discovery.

The only engineering principle is:

> **Close the loop first. Upgrade the intelligence later.**
> Never sacrifice a runnable closed loop for premature optimization.

---

## Source of Truth
When making implementation decisions, always obey the following priority:

1. `docs/architecture/system_blueprint.md`
2. `docs/architecture/interface_contracts.md`
3. Current task brief from the human operator
4. Existing code in this repository

If any conflict appears:
- do not silently “improve” the architecture,
- do not invent a new module boundary,
- do not rewrite stable interfaces,
- instead, report the conflict explicitly.

Before opening a new Phase 4A implementation conversation, also read the
pre-migration handoff index:

- `docs/handoff/README.md`

The handoff package summarizes state and risks. It does not override the
canonical architecture documents above.

---

## Runtime Baseline
- Until the human operator explicitly approves a re-baseline, this repository is **Fortress-only** on ROS 2 Humble.
- The accepted simulator stack is the ROS Humble default path: `ignition-gazebo6` / `ign gazebo`, `ros-humble-ros-gz-*`, and `ros-humble-gz-ros2-control`.
- Do not install, depend on, or validate this repository against Gazebo Harmonic (`gz-sim8`, `libgz-*`, `python3-gz-*`) or the mixed `packages.osrfoundation.org` Gazebo runtime path.
- Under WSLg, the accepted GUI runtime baseline is software rendering with `use_gpu:=false`. GPU-accelerated Gazebo GUI is not part of the current accepted project contract.

---

## Architecture Ground Rules
This project follows a strict layered architecture:

- `go2w_description`: robot model only
- `go2w_sim`: Gazebo Sim launch, sensor setup, bridge, simulation assets
- `go2w_control`: low-level locomotion control and mode switching only
- `go2w_perception`: FAST_LIO_ROS2 integration, odometry, point cloud, map persistence
- `go2w_navigation`: Nav2 + nav2_route integration and navigation configuration
- `go2w_mission`: top-level mission orchestration, floor semantics, route segmentation

### Hard boundary rules
- Navigation logic must not be implemented inside `go2w_control`.
- Stair detection / floor semantics must not be implemented inside `go2w_control`.
- FAST-LIO integration must not be mixed into `go2w_navigation`.
- Mission logic must not directly emit continuous motor commands.
- `nav2_route` must not be treated as a 3D terrain planner.
- Stair execution must remain a replaceable behavior module.

---

## Collaboration Rules
This repository is developed under a multi-model workflow.

### Roles
- **Human operator**: final authority, task dispatcher, merge decision maker
- **Cursor + Codex plugin**: the only allowed primary code writer
- **GPT**: architecture reviewer and GitHub-based code auditor
- **Gemini #1**: technical research and solution validation
- **Gemini #2**: counterexample reviewer, edge-case challenger, bug-risk critic

### Non-negotiable collaboration rules
1. Only **Cursor + Codex** may perform primary code implementation.
2. Parallelism is allowed only in:
   - research
   - review
3. Every implementation session must handle **one task only**.
4. Review and implementation must remain separate.
5. No agent may silently expand task scope.

---

## Required Task Prompt Contract
Every implementation task sent to the coding agent must include all 6 fields:

1. **Task Goal**
2. **Current Phase**
3. **Allowed Files**
4. **Forbidden Files**
5. **Required Commands**
6. **Definition of Done**

If any of these are missing, do not assume them. Ask for clarification or halt with a precise constraint report.

---

## Required Response Format
All agents should structure outputs using the same schema:

- **Conclusion**
- **Evidence**
- **Assumptions**
- **Risks**
- **Open Validation Items**
- **Recommended Next Step**

Do not return long unstructured prose when a task requires execution guidance.

---

## Phase Discipline
The system must evolve in this order:

- Phase 0: interface contracts and system boundaries
- Phase 1: simulation controllability
- Phase 2: localization and mapping foundation
- Phase 3: floor-level navigation + route graph baseline
- Phase 4: staircase state-machine closed loop
- Phase 5: terrain-aware automatic connector generation

### Phase protection rule
Do not pull a later-phase dependency into an earlier phase unless the human operator explicitly approves it.

Examples:
- Do not introduce elevation mapping into Phase 1–3 work.
- Do not redesign stair execution while Phase 4 is still proving manual connector workflow.
- Do not replace stable control interfaces during perception upgrades.

---

## Change Scope Rules
You may refactor aggressively **only if** all of the following are true:

- the current task explicitly authorizes structural change,
- the change stays inside the allowed file scope,
- the change does not break frozen interfaces,
- the change does not violate current phase boundaries.

Otherwise:
- keep the change minimal,
- preserve stable interfaces,
- prefer additive change over sweeping rewrite.

---

## Forbidden Behaviors
Never do the following unless explicitly instructed:

- rewrite multiple subsystems in one task
- move package responsibilities across layers
- rename stable interfaces casually
- mix mission logic into control logic
- hardcode one-off staircase geometry inside low-level control
- treat speculative ideas as approved architecture
- mark a task as “done” without checking the Definition of Done

---

## Expected Engineering Style
- Prefer explicit interfaces over hidden coupling.
- Prefer reproducible launch and test flows over convenience hacks.
- Prefer minimal closed-loop implementations over ambitious partially-working designs.
- Prefer diagnostics and observability over silent magic.
- Prefer stable contracts over frequent renaming.

---

## If Uncertain
If architecture, task scope, or interface ownership is unclear:
- stop,
- explain the ambiguity,
- point to the exact conflicting file or rule,
- propose the smallest safe next step.

Do not improvise across architectural boundaries.
