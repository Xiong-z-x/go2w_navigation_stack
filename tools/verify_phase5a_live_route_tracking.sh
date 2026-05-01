#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE5A_EVIDENCE_DIR:-/tmp/go2w_phase5a_live_route_tracking_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 90) + 130 ))}"
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
  terminate_pid "${LAUNCH_PID}" "phase5a_launch"
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
  sed -n '1,240p' "${EVIDENCE_DIR}/phase5a_launch.log" || true
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
  sed -n '1,240p' "${EVIDENCE_DIR}/phase5a_launch.log" || true
  exit 2
}

wait_for_action_type() {
  local action_name="$1"
  local timeout_seconds="$2"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 5s ros2 action list -t 2>/dev/null | grep -qx "${action_name} \\[nav2_msgs/action/ComputeAndTrackRoute\\]"; then
      print_kv "action_type_${action_name}" "nav2_msgs/action/ComputeAndTrackRoute"
      return
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "action_type_${action_name}" "MISSING"
  sed -n '1,240p' "${EVIDENCE_DIR}/phase5a_launch.log" || true
  exit 2
}

wait_for_result() {
  local timeout_seconds="$1"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if grep -q "phase5a_live_route_tracking_result: PASS" "${EVIDENCE_DIR}/phase5a_launch.log"; then
      return 0
    fi
    if grep -q "phase5a_live_route_tracking_result: FAIL" "${EVIDENCE_DIR}/phase5a_launch.log" \
      || grep -q "phase5a_final_result: ROUTE_TRACKING_UNAVAILABLE" "${EVIDENCE_DIR}/phase5a_launch.log" \
      || grep -q "phase5a_final_result: ROUTE_TRACKING_GOAL_TIMEOUT" "${EVIDENCE_DIR}/phase5a_launch.log" \
      || grep -q "phase5a_final_result: ROUTE_TRACKING_GOAL_REJECTED" "${EVIDENCE_DIR}/phase5a_launch.log" \
      || grep -q "phase5a_final_result: STAIR_EDGE_NOT_OBSERVED" "${EVIDENCE_DIR}/phase5a_launch.log"; then
      return 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "phase5a_launch" "TIMEOUT"
  sed -n '1,260p' "${EVIDENCE_DIR}/phase5a_launch.log" || true
  exit 2
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  print_kv "phase5a_live_route_tracking_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  (
    cd "${REPO_ROOT}"
    colcon build --symlink-install --packages-select go2w_mission go2w_navigation
  )
  source_file_checked "${REPO_SETUP}" "repo_setup"

  setsid ros2 launch go2w_mission phase5a_live_route_tracking.launch.py \
    trajectory_node_ids:=100,101,102,200,201,202 \
    sample_hold_sec:=0.45 \
    result_timeout_sec:=45.0 \
    >"${EVIDENCE_DIR}/phase5a_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_node "/route_server" 30
  wait_for_action "/compute_and_track_route" 30
  wait_for_action_type "/compute_and_track_route" 30
  wait_for_result 120
  terminate_pid "${LAUNCH_PID}" "phase5a_launch"

  if grep -q "phase5a_live_route_tracking_result: PASS" "${EVIDENCE_DIR}/phase5a_launch.log" \
    && grep -q "phase5a_stair_edge_detected: PASS" "${EVIDENCE_DIR}/phase5a_launch.log" \
    && grep -Eq "phase5a_feedback_edges: .*500" "${EVIDENCE_DIR}/phase5a_launch.log"; then
    print_kv "phase5a_live_route_tracking_result" "PASS"
    return 0
  fi

  print_kv "phase5a_live_route_tracking_result" "FAIL"
  sed -n '1,260p' "${EVIDENCE_DIR}/phase5a_launch.log" || true
  return 2
}

main "$@"
