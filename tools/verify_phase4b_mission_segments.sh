#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE4B_EVIDENCE_DIR:-/tmp/go2w_phase4b_mission_segments_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 100 ))}"
CLEAN_EVIDENCE="${GO2W_PHASE4B_CLEAN_EVIDENCE:-0}"
LAUNCH_PID=""
GRAPH_FILE=""

print_kv() {
  printf '%s: %s\n' "$1" "$2"
}

source_file_checked() {
  local setup_file="$1"
  local key="$2"
  if [ ! -f "${setup_file}" ]; then
    print_kv "${key}" "missing:${setup_file}"
    exit 2
  fi
  set +u
  # shellcheck source=/dev/null
  source "${setup_file}"
  set -u
}

set -u

process_group_alive() {
  local pid="$1"
  kill -0 "${pid}" 2>/dev/null || pgrep -g "${pid}" >/dev/null 2>&1
}

signal_process_group() {
  local signal_name="$1"
  local pid="$2"
  kill -"${signal_name}" -- "-${pid}" 2>/dev/null || kill -"${signal_name}" "${pid}" 2>/dev/null || true
}

terminate_pid() {
  local pid="$1"
  local label="$2"
  local attempts_remaining=5

  if [ -z "${pid}" ] || ! process_group_alive "${pid}"; then
    return
  fi

  signal_process_group "INT" "${pid}"
  while [ "${attempts_remaining}" -gt 0 ]; do
    if ! process_group_alive "${pid}"; then
      wait "${pid}" 2>/dev/null || true
      return
    fi
    sleep 1
    attempts_remaining=$((attempts_remaining - 1))
  done

  print_kv "cleanup_${label}" "forced_terminate"
  signal_process_group "TERM" "${pid}"
  sleep 1
  if process_group_alive "${pid}"; then
    signal_process_group "KILL" "${pid}"
  fi
  wait "${pid}" 2>/dev/null || true
}

cleanup() {
  terminate_pid "${LAUNCH_PID}" "phase4b_launch"
  if [ "${CLEAN_EVIDENCE}" = "1" ]; then
    rm -rf "${EVIDENCE_DIR}"
  fi
}

trap cleanup EXIT

wait_for_node() {
  local node_name="$1"
  local timeout_seconds="$2"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 3s ros2 node list 2>/dev/null | grep -qx "${node_name}"; then
      print_kv "node_${node_name}" "PRESENT"
      return
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "node_${node_name}" "MISSING"
  sed -n '1,260p' "${EVIDENCE_DIR}/phase4b_launch.log" || true
  exit 2
}

wait_for_action() {
  local action_name="$1"
  local timeout_seconds="$2"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 5s ros2 action list 2>/dev/null | grep -qx "${action_name}"; then
      print_kv "action_${action_name}" "PRESENT"
      return
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "action_${action_name}" "MISSING"
  timeout 5s ros2 action list >"${EVIDENCE_DIR}/actions_timeout.txt" 2>&1 || true
  sed -n '1,260p' "${EVIDENCE_DIR}/phase4b_launch.log" || true
  exit 2
}

run_mode() {
  local mode="$1"
  local expected="$2"
  local output_file="${EVIDENCE_DIR}/mission_${mode}.txt"
  local result_timeout="4.0"

  if [ "${mode}" = "timeout" ]; then
    result_timeout="0.5"
  fi

  set +e
  timeout 45s ros2 run go2w_mission go2w_phase4b_mission_runtime \
    --graph-file "${GRAPH_FILE}" \
    --mode "${mode}" \
    --expected-duration-sec 0.3 \
    --result-timeout-sec "${result_timeout}" >"${output_file}" 2>&1
  local status="$?"
  set -e

  if [ "${status}" -ne 0 ] && [ "${status}" -ne 2 ]; then
    print_kv "mission_${mode}" "PROCESS_UNEXPECTED_STATUS_${status}"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  fi

  if grep -qx "phase4b_final_result: ${expected}" "${output_file}"; then
    print_kv "mission_${mode}" "PASS"
    return
  fi

  print_kv "mission_${mode}" "FAIL"
  sed -n '1,240p' "${output_file}" || true
  exit 2
}

run_expected_failure_mode() {
  local label="$1"
  local expected="$2"
  local output_file="${EVIDENCE_DIR}/mission_${label}.txt"
  shift 2

  set +e
  timeout 30s ros2 run go2w_mission go2w_phase4b_mission_runtime \
    --graph-file "${GRAPH_FILE}" \
    "$@" >"${output_file}" 2>&1
  local status="$?"
  set -e

  if [ "${status}" -ne 0 ] && [ "${status}" -ne 2 ]; then
    print_kv "mission_${label}" "PROCESS_UNEXPECTED_STATUS_${status}"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  fi

  if grep -qx "phase4b_final_result: ${expected}" "${output_file}"; then
    print_kv "mission_${label}" "PASS"
    return
  fi

  print_kv "mission_${label}" "FAIL"
  sed -n '1,240p' "${output_file}" || true
  exit 2
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  print_kv "phase4b_mission_segments_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  (
    cd "${REPO_ROOT}"
    colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
  )
  source_file_checked "${REPO_SETUP}" "repo_setup"

  local nav_share
  nav_share="$(ros2 pkg prefix go2w_navigation)/share/go2w_navigation"
  GRAPH_FILE="${nav_share}/graphs/phase3c_hospital_multifloor_route.geojson"
  [ -f "${GRAPH_FILE}" ] || { print_kv "phase4b_graph_file" "MISSING:${GRAPH_FILE}"; exit 2; }
  export GRAPH_FILE
  print_kv "phase4b_graph_file" "${GRAPH_FILE}"

  setsid ros2 launch go2w_mission phase4b_mission_runtime.launch.py \
    use_sim_time:=false >"${EVIDENCE_DIR}/phase4b_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_node "/route_server" 45
  wait_for_node "/go2w_command_gate" 45
  wait_for_node "/go2w_stair_executor" 45
  wait_for_action "/compute_route" 45
  wait_for_action "/stair_exec" 45

  run_mode "success" "MISSION_SUCCEEDED"
  run_mode "failure" "MISSION_FAILED"
  run_mode "cancel" "MISSION_CANCELED"
  run_mode "timeout" "MISSION_TIMEOUT"

  run_expected_failure_mode \
    "route_unavailable" \
    "ROUTE_UNAVAILABLE" \
    --compute-route-action /missing_compute_route

  run_expected_failure_mode \
    "connector_unavailable" \
    "CONNECTOR_UNAVAILABLE" \
    --start-id 100 \
    --goal-id 103

  print_kv "phase4b_mission_segments_result" "PASS"
}

main "$@"
