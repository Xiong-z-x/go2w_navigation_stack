#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

print_kv() {
  printf '%s: %s\n' "$1" "$2"
}

fail() {
  print_kv "phase4_pre_handoff_result" "FAIL"
  print_kv "failure_reason" "$1"
  exit 2
}

require_file() {
  local file="$1"
  [ -f "${ROOT_DIR}/${file}" ] || fail "missing_file:${file}"
  print_kv "file_${file//\//_}" "PRESENT"
}

require_contains() {
  local file="$1"
  local pattern="$2"
  local key="$3"
  if grep -Eq "${pattern}" "${ROOT_DIR}/${file}"; then
    print_kv "${key}" "PASS"
    return
  fi
  fail "${key}_missing"
}

require_no_pattern() {
  local key="$1"
  local output_file
  local status
  shift
  output_file="$(mktemp)"
  set +e
  rg -n "$@" "${ROOT_DIR}" >"${output_file}" 2>&1
  status="$?"
  set -e
  if [ "${status}" -eq 0 ]; then
    print_kv "${key}" "FAIL"
    cat "${output_file}"
    rm -f "${output_file}"
    fail "${key}"
  fi
  if [ "${status}" -ne 1 ]; then
    print_kv "${key}" "RG_ERROR"
    cat "${output_file}"
    rm -f "${output_file}"
    fail "${key}_rg_error"
  fi
  rm -f "${output_file}"
  print_kv "${key}" "PASS"
}

require_python_parse() {
  local key="$1"
  local code="$2"
  if python3 -c "${code}"; then
    print_kv "${key}" "PASS"
    return
  fi
  fail "${key}"
}

printf '# Phase 4 Pre-Migration Handoff Verification\n'
print_kv "repo_root" "${ROOT_DIR}"

required_files=(
  "AGENTS.md"
  "README.md"
  "docs/architecture/system_blueprint.md"
  "docs/architecture/interface_contracts.md"
  "docs/architecture/architecture_state.md"
  "docs/handoff/README.md"
  "docs/handoff/current_project_state.md"
  "docs/handoff/risk_cleanup_log.md"
  "docs/handoff/phase4_migration_handoff_report.md"
  "docs/handoff/pre_migration_final_freeze_report.md"
  "docs/handoff/reading_order_and_file_map.md"
  "docs/handoff/next_agent_notes.md"
  "docs/handoff/new_model_initialization_prompt.md"
  "docs/verification/phase4a_stair_handoff_acceptance.md"
  "docs/verification/phase4b_mission_segment_runtime.md"
  "docs/verification/phase4c_flat_segment_gate.md"
  "docs/verification/phase4d_route_tracking_feedback.md"
  "docs/verification/phase5a_live_route_tracking.md"
  "docs/verification/go2w_real_model_motion_mode_baseline.md"
  "docs/verification/go2w_control_chain_regression.md"
  "docs/verification/go2w_real_model_route_following.md"
  "docs/verification/go2w_mission_real_flat_execution.md"
  "docs/verification/mission_api_scheduling_policy.md"
  "docs/verification/mission_api_priority_scheduling.md"
  "docs/verification/mission_api_orchestrator_control.md"
  "docs/verification/mission_api_queue_replay.md"
  "docs/verification/mission_api_task_history.md"
  "docs/verification/mission_api_workflow_policy.md"
  "docs/verification/go2w_real_model_regression.md"
  "docs/verification/phase4e_stair_fixture.md"
  "docs/verification/phase4e_mission_recovery.md"
  "docs/verification/phase4e_stair_tuning_overrides.md"
  "docs/verification/phase4_runtime_acceptance.md"
  "tools/verify_phase4a_stair_handoff.sh"
  "tools/verify_phase4b_mission_segments.sh"
  "tools/verify_phase4c_flat_segment_gate.sh"
  "tools/verify_phase4d_route_tracking_feedback.sh"
  "tools/verify_phase5a_live_route_tracking.sh"
  "tools/verify_go2w_real_model_baseline.sh"
  "tools/verify_go2w_control_chain_regression.sh"
  "tools/verify_go2w_real_model_route_following.sh"
  "tools/verify_go2w_mission_real_flat_execution.sh"
  "tools/verify_mission_api_scheduling_policy.sh"
  "tools/verify_mission_api_priority_scheduling.sh"
  "tools/verify_mission_api_orchestrator_control.sh"
  "tools/verify_mission_api_queue_replay.sh"
  "tools/verify_mission_api_task_history.sh"
  "tools/verify_mission_api_workflow_policy.sh"
  "tools/verify_go2w_real_model_regression.sh"
  "tools/verify_phase4e_stair_fixture.sh"
  "tools/verify_phase4e_mission_recovery.sh"
  "tools/verify_phase4e_stair_tuning_overrides.sh"
  "tools/verify_phase4_runtime_acceptance.sh"
  "go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson"
  "go2w_sim/worlds/phase3c_hospital_multifloor_world.sdf"
)

for file in "${required_files[@]}"; do
  require_file "${file}"
done

require_contains "docs/architecture/architecture_state.md" "Active Phase: \`Phase (3|4A|4B-min|4C-min|4D-min|4 accepted)\`" "active_phase_phase3_or_phase4"
require_contains "docs/architecture/architecture_state.md" 'Any next implementation still requires a separate complete task card' "next_task_card_boundary"
require_contains "docs/architecture/architecture_state.md" 'preserve the route-graph target yaw' "architecture_state_flat_goal_yaw"
require_contains "docs/architecture/architecture_state.md" '/home/xiongzx/go2w_ws/src/go2w_navigation_stack' "architecture_state_repo_root"
require_contains "docs/handoff/phase4_migration_handoff_report.md" 'Phase 4A 应从最小楼梯状态机/控制权交接骨架开始' "handoff_phase4a_start"
require_contains "docs/handoff/phase4_migration_handoff_report.md" 'route graph 目标 yaw' "handoff_phase4_flat_goal_yaw"
require_contains "docs/handoff/phase4_migration_handoff_report.md" 'Mission API scheduling / control / replay / history' "handoff_phase4_mission_history_latest"
require_contains "docs/handoff/pre_migration_final_freeze_report.md" '迁移前最终封板' "final_freeze_report_ready"
require_contains "docs/handoff/pre_migration_final_freeze_report.md" 'mission runtime real robot-motion flat execution' "final_freeze_next_task_mission_flat_execution"
require_contains "docs/handoff/pre_migration_final_freeze_report.md" 'production Mission Orchestrator (scheduling policy|skeleton hardening)' "final_freeze_next_task_production_mission"
require_contains "docs/handoff/pre_migration_final_freeze_report.md" 'priority scheduling' "final_freeze_next_task_priority_scheduling"
require_contains "docs/handoff/pre_migration_final_freeze_report.md" 'priority scheduling 最小闭环已完成' "final_freeze_priority_done"
require_contains "docs/handoff/pre_migration_final_freeze_report.md" '/home/xiongzx/go2w_ws/src/go2w_navigation_stack' "final_freeze_repo_root"
require_contains "docs/handoff/pre_migration_final_freeze_report.md" 'task-history ledger' "final_freeze_task_history"
require_contains "docs/handoff/pre_migration_final_freeze_report.md" 'route graph 保留目标 yaw' "final_freeze_flat_goal_yaw"
require_contains "docs/handoff/current_project_state.md" '\.go2w_external/workspaces/fast_lio_ros2' "handoff_fastlio_repo_local_ws"
require_contains "docs/handoff/current_project_state.md" "当前正式阶段：\`Phase 4 accepted\`" "handoff_current_phase4accepted"
require_contains "docs/handoff/current_project_state.md" '保留 route graph 目标 yaw' "handoff_flat_goal_yaw"
require_contains "docs/handoff/current_project_state.md" 'Mission API priority scheduling' "handoff_priority_scheduling"
require_contains "docs/handoff/current_project_state.md" 'Mission API workflow policy' "handoff_workflow_policy"
require_contains "docs/handoff/next_agent_notes.md" "不要把 \`nav2_route\` 当成 3D 地形规划器" "handoff_nav2_route_warning"
require_contains "docs/handoff/next_agent_notes.md" 'production Mission Orchestrator (scheduling policy|skeleton hardening)' "handoff_next_step_production_mission"
require_contains "docs/handoff/next_agent_notes.md" 'priority scheduling' "handoff_next_step_priority_scheduling"
require_contains "docs/handoff/next_agent_notes.md" '/home/xiongzx/go2w_ws/src/go2w_navigation_stack' "handoff_next_agent_repo_root"
require_contains "docs/handoff/next_agent_notes.md" 'bounded terminal task history' "handoff_task_history_warning"
require_contains "docs/handoff/next_agent_notes.md" 'Mission flat goal 不能只带 x/y' "handoff_next_step_flat_goal_yaw"
require_contains "docs/handoff/new_model_initialization_prompt.md" '可直接复制到新的对话中使用' "new_model_prompt_ready"
require_contains "docs/handoff/new_model_initialization_prompt.md" 'cd /home/xiongzx/go2w_ws/src/go2w_navigation_stack' "new_model_prompt_repo_root"
require_contains "docs/verification/phase4a_stair_handoff_acceptance.md" 'phase4a_stair_handoff_result: PASS' "phase4a_acceptance_evidence"
require_contains "docs/verification/phase4b_mission_segment_runtime.md" 'phase4b_mission_segments_result: PASS' "phase4b_acceptance_evidence"
require_contains "docs/verification/phase4c_flat_segment_gate.md" 'phase4c_flat_segment_gate_result: PASS' "phase4c_acceptance_evidence"
require_contains "docs/verification/phase4d_route_tracking_feedback.md" 'phase4d_route_tracking_feedback_result: PASS' "phase4d_acceptance_evidence"
require_contains "docs/verification/phase4_runtime_acceptance.md" 'phase4_runtime_acceptance_result: PASS' "phase4_runtime_acceptance_evidence"
require_contains "docs/verification/go2w_control_chain_regression.md" 'go2w_control_chain_regression_result: PASS' "control_chain_regression_evidence"
require_contains "docs/verification/go2w_real_model_route_following.md" 'three consecutive clean-domain PASS' "route_following_hardened_regression_candidate"
require_contains "docs/verification/mission_api_priority_scheduling.md" 'mission_priority_scheduling_result: PASS' "mission_priority_scheduling_evidence"
require_contains "docs/verification/mission_api_task_history.md" 'mission_task_history_result: PASS' "mission_task_history_evidence"
require_contains "docs/verification/mission_api_workflow_policy.md" 'mission_workflow_policy_result: PASS' "mission_workflow_policy_evidence"
require_contains "docs/verification/go2w_real_model_regression.md" 'not be treated as the stable control-chain migration gate' "real_model_regression_boundary"
require_contains "docs/handoff/README.md" 'verify_go2w_control_chain_regression.sh' "handoff_readme_control_chain_entry"
require_contains "docs/handoff/new_model_initialization_prompt.md" 'Real-model same-floor route-following 已完成 dedicated hardening' "new_model_prompt_route_following_hardened"
require_contains "docs/handoff/new_model_initialization_prompt.md" 'task history' "new_model_prompt_task_history"
require_contains "docs/handoff/new_model_initialization_prompt.md" 'workflow policy' "new_model_prompt_workflow_policy"
require_contains "README.md" "当前正式阶段：\`Phase 4 accepted\`" "readme_current_phase4accepted"
require_contains "README.md" 'production Mission Orchestrator (scheduling policy|skeleton hardening)' "readme_next_step_production_mission"
require_contains "README.md" 'priority scheduling' "readme_next_step_priority_scheduling"
require_contains "README.md" '/home/xiongzx/go2w_ws/src/go2w_navigation_stack' "readme_repo_root"
require_contains "README.md" 'task history' "readme_task_history"
require_contains "README.md" 'workflow policy' "readme_workflow_policy"
require_contains "README.md" '保留了目标 yaw' "readme_flat_goal_yaw"
require_contains "docs/handoff/README.md" "当前阶段：已验收 \`Phase 4 accepted\`" "handoff_readme_current_phase4accepted"
require_contains "docs/handoff/reading_order_and_file_map.md" '/home/xiongzx/go2w_ws/src/go2w_navigation_stack' "handoff_reading_order_repo_root"
require_contains "README.md" 'docs/handoff/README.md' "readme_handoff_entry"
require_contains "AGENTS.md" 'docs/handoff/README.md' "agents_handoff_entry"

require_no_pattern \
  "active_fastlio_defaults_not_tmp" \
  'GO2W_FASTLIO_(WS|SRC):-/tmp|/tmp/(fast_lio_ros2_probe|go2w_phase2d_fastlio_ws)' \
  --glob 'tools/*.sh'

if git -C "${ROOT_DIR}" ls-files --error-unmatch .go2w_external >/dev/null 2>&1; then
  fail "external_cache_is_tracked"
fi
print_kv "external_cache_untracked" "PASS"

if find "${ROOT_DIR}"/go2w_* "${ROOT_DIR}/tools" -path '*/__pycache__' -type d -print -quit | grep -q .; then
  find "${ROOT_DIR}"/go2w_* "${ROOT_DIR}/tools" -path '*/__pycache__' -type d -prune -exec rm -rf {} +
  print_kv "source_pycache_cleaned" "PASS"
fi
if find "${ROOT_DIR}"/go2w_* "${ROOT_DIR}/tools" -path '*/__pycache__' -type d -print -quit | grep -q .; then
  fail "source_pycache_present"
fi
print_kv "source_pycache_absent" "PASS"

bash -n \
  "${ROOT_DIR}/tools/apply_phase2c_fastlio_patch.sh" \
  "${ROOT_DIR}/tools/check_phase2_fastlio_external.sh" \
  "${ROOT_DIR}/tools/verify_phase2e_fastlio_contract.sh" \
  "${ROOT_DIR}/tools/verify_phase2f_tf_authority.sh" \
  "${ROOT_DIR}/tools/verify_phase2g_perception_stability.sh" \
  "${ROOT_DIR}/tools/verify_phase2h_costmap_consumer.sh" \
  "${ROOT_DIR}/tools/verify_phase3a_nav2_same_floor.sh" \
  "${ROOT_DIR}/tools/verify_phase4_pre_handoff.sh" \
  "${ROOT_DIR}/tools/verify_phase4a_stair_handoff.sh" \
  "${ROOT_DIR}/tools/verify_phase4b_mission_segments.sh" \
  "${ROOT_DIR}/tools/verify_phase4c_flat_segment_gate.sh" \
  "${ROOT_DIR}/tools/verify_phase4d_route_tracking_feedback.sh" \
  "${ROOT_DIR}/tools/verify_go2w_control_chain_regression.sh" \
  "${ROOT_DIR}/tools/verify_go2w_mission_real_flat_execution.sh" \
  "${ROOT_DIR}/tools/verify_mission_api_scheduling_policy.sh" \
  "${ROOT_DIR}/tools/verify_mission_api_priority_scheduling.sh" \
  "${ROOT_DIR}/tools/verify_mission_api_orchestrator_control.sh" \
  "${ROOT_DIR}/tools/verify_mission_api_queue_replay.sh" \
  "${ROOT_DIR}/tools/verify_mission_api_task_history.sh" \
  "${ROOT_DIR}/tools/verify_mission_api_workflow_policy.sh" \
  "${ROOT_DIR}/tools/verify_go2w_real_model_regression.sh" \
  "${ROOT_DIR}/tools/verify_phase4_runtime_acceptance.sh"
print_kv "bash_syntax" "PASS"

require_python_parse \
  "phase3c_route_graph_json_parse" \
  "import json, pathlib; json.loads(pathlib.Path('${ROOT_DIR}/go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson').read_text(encoding='utf-8'))"

require_python_parse \
  "phase3c_hospital_world_xml_parse" \
  "import xml.etree.ElementTree as ET; ET.parse('${ROOT_DIR}/go2w_sim/worlds/phase3c_hospital_multifloor_world.sdf')"

print_kv "phase4_pre_handoff_result" "PASS"
