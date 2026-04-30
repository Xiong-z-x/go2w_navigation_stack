#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE4D_EVIDENCE_DIR:-/tmp/go2w_phase4d_route_tracking_feedback_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 90) + 130 ))}"
CLEAN_EVIDENCE="${GO2W_PHASE4D_CLEAN_EVIDENCE:-0}"
LAUNCH_PID=""

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
  terminate_pid "${LAUNCH_PID}" "phase4d_launch"
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
  sed -n '1,240p' "${EVIDENCE_DIR}/phase4d_launch.log" || true
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
  sed -n '1,240p' "${EVIDENCE_DIR}/phase4d_launch.log" || true
  exit 2
}

start_feedback_server() {
  local drop_operation="$1"
  setsid ros2 launch go2w_mission phase4d_route_tracking_feedback.launch.py \
    drop_operation:="${drop_operation}" >"${EVIDENCE_DIR}/phase4d_launch.log" 2>&1 &
  LAUNCH_PID="$!"
  wait_for_node "/go2w_route_tracking_feedback_executor" 30
  wait_for_action "/compute_and_track_route" 30
}

stop_feedback_server() {
  terminate_pid "${LAUNCH_PID}" "phase4d_launch"
  LAUNCH_PID=""
}

run_observer() {
  local label="$1"
  local expected="$2"
  local output_file="${EVIDENCE_DIR}/observer_${label}.txt"
  shift 2

  set +e
  timeout 30s ros2 run go2w_mission go2w_phase4d_route_tracking_observer \
    "$@" >"${output_file}" 2>&1
  local status="$?"
  set -e

  if [ "${status}" -ne 0 ] && [ "${status}" -ne 2 ]; then
    print_kv "observer_${label}" "PROCESS_UNEXPECTED_STATUS_${status}"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  fi

  if grep -qx "phase4d_route_tracking_result: ${expected}" "${output_file}" \
    || grep -qx "phase4d_final_result: ${expected}" "${output_file}"; then
    print_kv "observer_${label}" "PASS"
    return
  fi

  print_kv "observer_${label}" "FAIL"
  sed -n '1,240p' "${output_file}" || true
  exit 2
}

require_success_keys() {
  local output_file="${EVIDENCE_DIR}/observer_success.txt"
  grep -qx "phase4d_route_feedback_seen: PASS" "${output_file}" || {
    print_kv "phase4d_route_feedback_seen" "FAIL"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  }
  grep -qx "phase4d_stair_edge_detected: PASS" "${output_file}" || {
    print_kv "phase4d_stair_edge_detected" "FAIL"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  }
  grep -qx "phase4d_operation_triggered: stair_exec" "${output_file}" || {
    print_kv "phase4d_operation_triggered" "FAIL"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  }
  print_kv "phase4d_success_keys" "PASS"
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  print_kv "phase4d_route_tracking_feedback_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  (
    cd "${REPO_ROOT}"
    colcon build --symlink-install --packages-select go2w_navigation go2w_mission
  )
  source_file_checked "${REPO_SETUP}" "repo_setup"

  start_feedback_server "false"
  run_observer "success" "PASS"
  require_success_keys
  stop_feedback_server

  start_feedback_server "true"
  run_observer "missing_operation" "ROUTE_OPERATION_NOT_OBSERVED"
  stop_feedback_server

  run_observer "unavailable" "ROUTE_TRACKING_UNAVAILABLE" \
    --action-name /missing_compute_and_track_route

  print_kv "phase4d_route_tracking_feedback_result" "PASS"
}

main "$@"
