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
  "docs/handoff/reading_order_and_file_map.md"
  "docs/handoff/next_agent_notes.md"
  "docs/handoff/new_model_initialization_prompt.md"
  "go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson"
  "go2w_sim/worlds/phase3c_hospital_multifloor_world.sdf"
)

for file in "${required_files[@]}"; do
  require_file "${file}"
done

require_contains "docs/architecture/architecture_state.md" "Active Phase: \`Phase 3\`" "active_phase_phase3"
require_contains "docs/architecture/architecture_state.md" 'Phase 4A only after an explicit complete task card' "phase4a_task_card_boundary"
require_contains "docs/handoff/phase4_migration_handoff_report.md" 'Phase 4A 应从最小楼梯状态机/控制权交接骨架开始' "handoff_phase4a_start"
require_contains "docs/handoff/current_project_state.md" '\.go2w_external/workspaces/fast_lio_ros2' "handoff_fastlio_repo_local_ws"
require_contains "docs/handoff/next_agent_notes.md" "不要把 \`nav2_route\` 当成 3D 地形规划器" "handoff_nav2_route_warning"
require_contains "docs/handoff/new_model_initialization_prompt.md" '可直接复制到新的对话中使用' "new_model_prompt_ready"
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
  "${ROOT_DIR}/tools/verify_phase4_pre_handoff.sh"
print_kv "bash_syntax" "PASS"

require_python_parse \
  "phase3c_route_graph_json_parse" \
  "import json, pathlib; json.loads(pathlib.Path('${ROOT_DIR}/go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson').read_text(encoding='utf-8'))"

require_python_parse \
  "phase3c_hospital_world_xml_parse" \
  "import xml.etree.ElementTree as ET; ET.parse('${ROOT_DIR}/go2w_sim/worlds/phase3c_hospital_multifloor_world.sdf')"

print_kv "phase4_pre_handoff_result" "PASS"
