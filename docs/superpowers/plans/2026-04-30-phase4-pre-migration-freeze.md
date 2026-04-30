# Phase 4 Pre-Migration Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for
> tracking.

**Goal:** Freeze the accepted Phase 3 repository state, repair pre-Phase4
handoff risks, and generate the next-conversation handoff package.

**Architecture:** Keep Phase 4 runtime untouched. Add a centralized
`docs/handoff/` package, update only current-state entrypoints, and harden
verification script defaults so current tooling matches Phase 3C.

**Tech Stack:** ROS 2 Humble, Gazebo Fortress, Bash, Markdown, Python standard
library validation.

---

## Files
- Create: `docs/handoff/README.md`
- Create: `docs/handoff/current_project_state.md`
- Create: `docs/handoff/risk_cleanup_log.md`
- Create: `docs/handoff/phase4_migration_handoff_report.md`
- Create: `docs/handoff/reading_order_and_file_map.md`
- Create: `docs/handoff/next_agent_notes.md`
- Create: `docs/handoff/new_model_initialization_prompt.md`
- Create: `tools/verify_phase4_pre_handoff.sh`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/architecture/architecture_state.md`
- Modify: `tools/apply_phase2c_fastlio_patch.sh`
- Modify: `tools/check_phase2_fastlio_external.sh`
- Modify: `tools/verify_phase2e_fastlio_contract.sh`
- Modify: `tools/verify_phase2f_tf_authority.sh`
- Modify: `tools/verify_phase2g_perception_stability.sh`
- Modify: `tools/verify_phase2h_costmap_consumer.sh`
- Modify: `tools/verify_phase3a_nav2_same_floor.sh`

## Task 1: Repair FAST-LIO Default Path Drift

- [ ] Update all active FAST-LIO verification scripts to derive defaults from
  `GO2W_FASTLIO_CACHE_ROOT` and `.go2w_external/`.
- [ ] Preserve explicit environment variable and positional overrides.
- [ ] Run `rg` to confirm no active script still defaults FAST-LIO source or
  workspace to `/tmp`.

## Task 2: Add Handoff Package

- [ ] Create the `docs/handoff/` index and current-state summary.
- [ ] Create risk cleanup, reading order, and next-agent notes.
- [ ] Create the copy-ready new model initialization prompt.
- [ ] Keep facts aligned with `docs/architecture/architecture_state.md`.

## Task 3: Add Verification Gate

- [ ] Add `tools/verify_phase4_pre_handoff.sh`.
- [ ] Validate handoff files, route graph JSON, hospital world XML, active phase
  status, and FAST-LIO default path consistency.
- [ ] Make the script executable.

## Task 4: Update Discoverability

- [ ] Update `README.md`, `AGENTS.md`, and `architecture_state.md` with the
  handoff package location and Phase 4A boundary.
- [ ] Keep canonical architecture source priority unchanged.

## Task 5: Final Validation and Commit

- [ ] Run shell syntax checks on affected scripts.
- [ ] Run ShellCheck where available.
- [ ] Run the new handoff verification script.
- [ ] Run colcon build and tests for affected packages.
- [ ] Review `git diff` and commit the complete handoff package.
