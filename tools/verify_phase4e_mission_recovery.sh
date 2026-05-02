#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE4E_MISSION_EVIDENCE_DIR:-/tmp/go2w_phase4e_mission_recovery_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 80) + 120 ))}"
PARTITION="go2w_phase4e_mission_${$}"
LAUNCH_PID=""
MISSION_STATE_FILE="${GO2W_PHASE4E_MISSION_STATE_FILE:-${EVIDENCE_DIR}/mission_state.json}"

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
  terminate_pid "${LAUNCH_PID}" "mission_api_launch"
}

trap cleanup EXIT

wait_for_text() {
  local pattern="$1"
  local file="$2"
  local timeout_seconds="$3"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if grep -qE "${pattern}" "${file}" 2>/dev/null; then
      return 0
    fi
    if [ -n "${LAUNCH_PID}" ] && ! process_group_alive "${LAUNCH_PID}" 2>/dev/null; then
      print_kv "launch" "exited_early"
      sed -n '1,260p' "${file}" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "wait_for_text" "timeout:${pattern}"
  sed -n '1,260p' "${file}" || true
  exit 2
}

wait_for_node() {
  local node_name="$1"
  local timeout_seconds="$2"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 3s ros2 node list 2>/dev/null | grep -qx "${node_name}"; then
      print_kv "node_${node_name}" "PRESENT"
      return
    fi
    if [ -n "${LAUNCH_PID}" ] && ! process_group_alive "${LAUNCH_PID}" 2>/dev/null; then
      print_kv "launch" "exited_early"
      sed -n '1,260p' "${EVIDENCE_DIR}/mission_api_launch.log" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "node_${node_name}" "MISSING"
  sed -n '1,260p' "${EVIDENCE_DIR}/mission_api_launch.log" || true
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
  sed -n '1,260p' "${EVIDENCE_DIR}/mission_api_launch.log" || true
  exit 2
}

run_mission_goal() {
  local label="$1"
  local output_file="${EVIDENCE_DIR}/mission_${label}.txt"

  if ! timeout 60s python3 - >"${output_file}" 2>&1 <<'PY'
import os
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from go2w_mission.action import RunMission


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def wait_future(node: Node, future, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    return future.done()


def main() -> int:
    graph_file = os.environ["MISSION_PHASE4E_GRAPH_FILE"]
    rclpy.init()
    node = Node("phase4e_mission_recovery_client")
    client = ActionClient(node, RunMission, "/go2w/mission/run")
    try:
        if not client.wait_for_server(timeout_sec=30.0):
            print_kv("mission_goal", "FAIL_SERVER_UNAVAILABLE")
            return 2

        goal = RunMission.Goal()
        goal.start_id = 100
        goal.goal_id = 202
        goal.graph_file = graph_file
        goal.route_frame_id = "map"
        goal.expected_stair_duration_sec = 0.8
        goal.result_timeout_sec = 12.0
        goal.flat_result_timeout_sec = 8.0

        send_future = client.send_goal_async(goal)
        if not wait_future(node, send_future, 10.0):
            print_kv("mission_goal", "FAIL_GOAL_RESPONSE_TIMEOUT")
            return 2
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print_kv("mission_goal", "REJECTED")
            return 2

        result_future = goal_handle.get_result_async()
        if not wait_future(node, result_future, 40.0):
            print_kv("mission_goal", "FAIL_RESULT_TIMEOUT")
            return 2
        wrapped = result_future.result()
        result = wrapped.result
        print_kv("mission_goal_status", wrapped.status)
        print_kv("mission_goal_success", result.success)
        print_kv("mission_goal_result_code", result.result_code)
        print_kv("mission_goal_message", result.message)
        print_kv("mission_goal_segment_count", result.segment_count)
        print_kv("mission_goal_segment_summary", result.segment_summary)
        return 0
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
PY
  then
    print_kv "mission_goal_${label}" "FAIL"
    sed -n '1,260p' "${output_file}" || true
    exit 2
  fi

  if grep -q "^mission_goal_result_code: " "${output_file}"; then
    print_kv "mission_goal_${label}" "PASS"
    return
  fi

  print_kv "mission_goal_${label}" "FAIL_NO_RESULT"
  sed -n '1,260p' "${output_file}" || true
  exit 2
}

verify_state_file() {
  local label="$1"
  local expected_state="$2"
  local expected_next_index="$3"
  local output_file="${EVIDENCE_DIR}/state_${label}.txt"

  if ! timeout 15s python3 - >"${output_file}" 2>&1 <<'PY'
import json
import os
from pathlib import Path

state_file = Path(os.environ["MISSION_PHASE4E_STATE_FILE"])
payload = json.loads(state_file.read_text(encoding="utf-8"))
print(f"mission_state_state: {payload['state']}")
print(f"mission_state_result_code: {payload['result_code']}")
print(f"mission_state_next_segment_index: {payload['next_segment_index']}")
print(f"mission_state_segment_summary: {payload['segment_summary']}")
print(f"mission_state_retry_count: {payload['retry_count']}")
PY
  then
    print_kv "mission_state_${label}" "FAIL"
    sed -n '1,260p' "${output_file}" || true
    exit 2
  fi

  if grep -qx "mission_state_state: ${expected_state}" "${output_file}" \
    && grep -qx "mission_state_next_segment_index: ${expected_next_index}" "${output_file}"; then
    print_kv "mission_state_${label}" "PASS"
    return
  fi

  print_kv "mission_state_${label}" "FAIL"
  sed -n '1,260p' "${output_file}" || true
  exit 2
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  export GZ_PARTITION="${PARTITION}"
  export MISSION_PHASE4E_STATE_FILE="${MISSION_STATE_FILE}"

  print_kv "phase4e_mission_recovery_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"
  print_kv "gz_partition" "${GZ_PARTITION}"
  print_kv "mission_state_file" "${MISSION_STATE_FILE}"

  source_file_checked "${ROS_SETUP}" "ros_setup"

  (
    cd "${REPO_ROOT}"
    colcon build --symlink-install --packages-select go2w_control go2w_navigation go2w_mission
  )
  source_file_checked "${REPO_SETUP}" "repo_setup"

  local nav_share
  nav_share="$(ros2 pkg prefix go2w_navigation)/share/go2w_navigation"
  export MISSION_PHASE4E_GRAPH_FILE="${nav_share}/graphs/phase3c_hospital_multifloor_route.geojson"
  [ -f "${MISSION_PHASE4E_GRAPH_FILE}" ] || {
    print_kv "mission_graph_file" "MISSING:${MISSION_PHASE4E_GRAPH_FILE}"
    exit 2
  }
  print_kv "mission_graph_file" "${MISSION_PHASE4E_GRAPH_FILE}"

  rm -f "${MISSION_STATE_FILE}"

  setsid ros2 launch go2w_mission mission_api.launch.py \
    use_sim_time:=false \
    launch_stair_executor:=false \
    mission_state_file:="${MISSION_STATE_FILE}" \
    log_level:=info \
    >"${EVIDENCE_DIR}/mission_api_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_node "/route_server" 60
  wait_for_node "/go2w_command_gate" 60
  wait_for_node "/go2w_flat_nav_executor" 60
  wait_for_node "/go2w_mission_api" 60
  wait_for_action "/compute_route" 60
  wait_for_action "/navigate_to_pose" 60
  wait_for_action "/go2w/mission/run" 60

  run_mission_goal "first_run"
  wait_for_text "mission_checkpoint: key=.* state=RECOVERABLE next_segment_index=1" "${EVIDENCE_DIR}/mission_api_launch.log" 90
  verify_state_file "first_run" "RECOVERABLE" "1"

  terminate_pid "${LAUNCH_PID}" "mission_api_launch"
  LAUNCH_PID=""

  setsid ros2 launch go2w_mission mission_api.launch.py \
    use_sim_time:=false \
    mission_state_file:="${MISSION_STATE_FILE}" \
    log_level:=info \
    >"${EVIDENCE_DIR}/mission_api_resume_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_node "/route_server" 60
  wait_for_node "/go2w_command_gate" 60
  wait_for_node "/go2w_flat_nav_executor" 60
  wait_for_node "/go2w_stair_executor" 60
  wait_for_node "/go2w_mission_api" 60
  wait_for_action "/compute_route" 60
  wait_for_action "/navigate_to_pose" 60
  wait_for_action "/stair_exec" 60
  wait_for_action "/go2w/mission/run" 60

  run_mission_goal "second_run"
  wait_for_text "mission_recovery_resume: key=.* resume_from=1" "${EVIDENCE_DIR}/mission_api_resume_launch.log" 90
  wait_for_text "mission_checkpoint: key=.* state=SUCCEEDED" "${EVIDENCE_DIR}/mission_api_resume_launch.log" 90
  verify_state_file "second_run" "SUCCEEDED" "3"

  if grep -q "mission_goal_result_code: MISSION_STAIR_UNAVAILABLE" "${EVIDENCE_DIR}/mission_first_run.txt" \
    && grep -q "mission_goal_result_code: MISSION_SUCCEEDED" "${EVIDENCE_DIR}/mission_second_run.txt"; then
    print_kv "phase4e_mission_recovery_result" "PASS"
    return
  fi

  print_kv "phase4e_mission_recovery_result" "FAIL"
  sed -n '1,260p' "${EVIDENCE_DIR}/mission_first_run.txt" || true
  sed -n '1,260p' "${EVIDENCE_DIR}/mission_second_run.txt" || true
  exit 2
}

main "$@"
