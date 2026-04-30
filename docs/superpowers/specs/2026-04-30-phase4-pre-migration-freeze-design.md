# Phase 4 Pre-Migration Freeze Design

## Scope
This task freezes the repository state before opening Phase 4A in a new
conversation. It is a documentation, consistency, and verification hardening
task. It must not implement Phase 4 runtime behavior.

## Goals
- Record the current project state from Phase 0 through accepted Phase 3C.
- Identify and repair repository-local risks that can mislead the next model.
- Make the next valid Phase 4A entrypoint explicit and narrow.
- Provide a direct, copy-ready initialization prompt for the next conversation.
- Add a static handoff verification gate so the handoff package remains
  checkable from the repository.

## Current Findings
- `docs/architecture/architecture_state.md` and `README.md` agree that the
  repository is formally in accepted Phase 3 and has not entered Phase 4A.
- Phase 3C documents the FAST-LIO external dependency as repo-local
  `.go2w_external/`, but several older runtime verification scripts still
  default their FAST-LIO workspace to `/tmp/go2w_phase2d_fastlio_ws`.
- Existing historical verification records still contain `/tmp` evidence paths.
  Those records are historical evidence and should not be rewritten as current
  defaults.
- There is no centralized handoff index that tells the next model which files
  are canonical, which are summaries, and which are historical records.

## Selected Approach
Use an additive handoff package plus minimal consistency fixes:

- Add `docs/handoff/` as the centralized migration package.
- Update only operator-facing entrypoints and current-state documents to point
  at the handoff package.
- Update active verification scripts so FAST-LIO source/workspace defaults are
  consistent with the Phase 3C `.go2w_external/` baseline.
- Preserve historical docs that mention old `/tmp` workflows, but label the
  current default clearly in handoff material.
- Add `tools/verify_phase4_pre_handoff.sh` for static and lightweight
  consistency validation.

## Explicit Non-Goals
- Do not import or replace the placeholder Unitree Go2W model.
- Do not implement Mission Orchestrator runtime.
- Do not implement stair executor runtime.
- Do not add elevation mapping, traversability, or automatic connector
  generation.
- Do not change perception-owned `odom -> base_link` authority.
- Do not replace the Gazebo Fortress software-rendering baseline.

## Verification Strategy
- Shell syntax and ShellCheck for affected scripts.
- JSON validation for route graph assets.
- XML parse validation for the Phase 3C hospital world.
- Static checks that current FAST-LIO defaults no longer point at `/tmp`.
- Colcon build and tests for the affected ROS packages.

## Self-Review
- No placeholder sections remain.
- Scope is limited to pre-Phase4 handoff and consistency hardening.
- Phase 4A is described only as the next task boundary, not implemented here.
