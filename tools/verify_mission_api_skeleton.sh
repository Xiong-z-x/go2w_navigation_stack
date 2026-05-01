#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_MISSION_API_EVIDENCE_DIR:-/tmp/go2w_mission_api_skeleton_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 140 ))}"
LAUNCH_PID=""
CLEAN_EVIDENCE="${GO2W_MISSION_API_CLEAN_EVIDENCE:-0}"
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
  terminate_pid "${LAUNCH_PID}" "mission_api_launch"
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
    if [ -n "${LAUNCH_PID}" ] && ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
      print_kv "launch" "exited_early"
      sed -n '1,240p' "${EVIDENCE_DIR}/mission_api_launch.log" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "node_${node_name}" "MISSING"
  sed -n '1,240p' "${EVIDENCE_DIR}/mission_api_launch.log" || true
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
  sed -n '1,240p' "${EVIDENCE_DIR}/mission_api_launch.log" || true
  exit 2
}

wait_for_lifecycle_active() {
  local node_name="$1"
  local timeout_seconds="$2"
  local elapsed=0
  local output_file="${EVIDENCE_DIR}/route_server_lifecycle.txt"

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 5s ros2 lifecycle get "${node_name}" >"${output_file}" 2>&1 \
      && grep -qx "active \\[3\\]" "${output_file}"; then
      print_kv "route_server_lifecycle" "active [3]"
      return
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "route_server_lifecycle" "FAIL"
  sed -n '1,160p' "${output_file}" || true
  sed -n '1,240p' "${EVIDENCE_DIR}/mission_api_launch.log" || true
  exit 2
}

run_goal_case() {
  local case_name="$1"
  local result_key="${2:-${case_name}}"
  local output_file="${EVIDENCE_DIR}/mission_${case_name}.txt"

  set +e
  MISSION_API_CASE="${case_name}" \
  MISSION_API_GRAPH_FILE="${GRAPH_FILE}" \
  timeout 80s python3 - >"${output_file}" 2>&1 <<'PY'
import os
import sys
import time

import rclpy
from action_msgs.msg import GoalStatus
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


def make_goal(
    *,
    start_id: int,
    goal_id: int,
    graph_file: str,
    expected_stair_duration_sec: float,
    result_timeout_sec: float,
    flat_result_timeout_sec: float,
) -> RunMission.Goal:
    goal = RunMission.Goal()
    goal.start_id = start_id
    goal.goal_id = goal_id
    goal.graph_file = graph_file
    goal.route_frame_id = "map"
    goal.expected_stair_duration_sec = expected_stair_duration_sec
    goal.result_timeout_sec = result_timeout_sec
    goal.flat_result_timeout_sec = flat_result_timeout_sec
    return goal


def send_goal(node: Node, client: ActionClient, goal: RunMission.Goal):
    send_future = client.send_goal_async(goal)
    if not wait_future(node, send_future, 10.0):
        raise RuntimeError("goal_response_timeout")
    goal_handle = send_future.result()
    if goal_handle is None or not goal_handle.accepted:
        raise RuntimeError("goal_rejected")
    return goal_handle


def wait_result(node: Node, result_future, timeout_sec: float):
    if not wait_future(node, result_future, timeout_sec):
        raise RuntimeError("result_timeout")
    return result_future.result()


def assert_case(label: str, condition: bool, detail: str) -> None:
    if condition:
        print_kv(label, f"PASS {detail}")
        return
    print_kv(label, f"FAIL {detail}")
    raise SystemExit(2)


def main() -> int:
    case = os.environ["MISSION_API_CASE"]
    graph_file = os.environ["MISSION_API_GRAPH_FILE"]
    result_timeout_sec = float(os.environ.get("MISSION_API_RESULT_TIMEOUT_SEC", "10.0"))
    flat_result_timeout_sec = float(os.environ.get("MISSION_API_FLAT_TIMEOUT_SEC", "4.0"))
    expected_stair_duration_sec = float(os.environ.get("MISSION_API_STAIR_DURATION_SEC", "1.5"))
    cancel_delay_sec = float(os.environ.get("MISSION_API_CANCEL_DELAY_SEC", "0.2"))

    rclpy.init()
    node = Node(f"mission_api_{case}_probe")
    client = ActionClient(node, RunMission, "/go2w/mission/run")
    try:
        if not client.wait_for_server(timeout_sec=20.0):
            print_kv(f"mission_api_{case}_result", "FAIL action_server_unavailable")
            return 2

        if case == "success":
            goal = make_goal(
                start_id=100,
                goal_id=202,
                graph_file=graph_file,
                expected_stair_duration_sec=expected_stair_duration_sec,
                result_timeout_sec=result_timeout_sec,
                flat_result_timeout_sec=flat_result_timeout_sec,
            )
            goal_handle = send_goal(node, client, goal)
            result = wait_result(node, goal_handle.get_result_async(), 30.0).result
            assert_case(
                "mission_api_success_result",
                result.success and result.result_code == "MISSION_SUCCEEDED"
                and result.segment_count > 0,
                f"result_code={result.result_code} segments={result.segment_count}",
            )
            return 0

        if case == "invalid_goal":
            goal = make_goal(
                start_id=100,
                goal_id=100,
                graph_file=graph_file,
                expected_stair_duration_sec=expected_stair_duration_sec,
                result_timeout_sec=result_timeout_sec,
                flat_result_timeout_sec=flat_result_timeout_sec,
            )
            goal_handle = send_goal(node, client, goal)
            wrapped = wait_result(node, goal_handle.get_result_async(), 10.0)
            result = wrapped.result
            assert_case(
                "mission_api_invalid_goal_result",
                (wrapped.status == GoalStatus.STATUS_ABORTED)
                and (not result.success)
                and result.result_code == "MISSION_INVALID_GOAL",
                f"status={wrapped.status} result_code={result.result_code}",
            )
            return 0

        if case == "cancel":
            goal = make_goal(
                start_id=100,
                goal_id=202,
                graph_file=graph_file,
                expected_stair_duration_sec=2.0,
                result_timeout_sec=max(result_timeout_sec, 10.0),
                flat_result_timeout_sec=flat_result_timeout_sec,
            )
            goal_handle = send_goal(node, client, goal)
            time.sleep(cancel_delay_sec)
            cancel_future = goal_handle.cancel_goal_async()
            if not wait_future(node, cancel_future, 10.0):
                raise RuntimeError("cancel_timeout")
            wrapped = wait_result(node, goal_handle.get_result_async(), 20.0)
            result = wrapped.result
            assert_case(
                "mission_api_cancel_result",
                (wrapped.status == GoalStatus.STATUS_CANCELED)
                and (not result.success)
                and result.result_code == "MISSION_CANCELED",
                f"status={wrapped.status} result_code={result.result_code}",
            )
            return 0

        if case == "flat_unavailable":
            goal = make_goal(
                start_id=100,
                goal_id=202,
                graph_file=graph_file,
                expected_stair_duration_sec=expected_stair_duration_sec,
                result_timeout_sec=result_timeout_sec,
                flat_result_timeout_sec=flat_result_timeout_sec,
            )
            goal_handle = send_goal(node, client, goal)
            wrapped = wait_result(node, goal_handle.get_result_async(), 20.0)
            result = wrapped.result
            assert_case(
                "mission_api_unavailable_action_result",
                (wrapped.status == GoalStatus.STATUS_ABORTED)
                and (not result.success)
                and result.result_code == "MISSION_FLAT_NAV_UNAVAILABLE",
                f"status={wrapped.status} result_code={result.result_code}",
            )
            return 0

        print_kv(f"mission_api_{case}_result", "FAIL unknown_case")
        return 2
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
PY
  local status="$?"
  set -e

  if [ "${status}" -eq 0 ] && grep -q "^mission_api_${result_key}_result: PASS" "${output_file}"; then
    print_kv "mission_api_${result_key}" "PASS"
    return
  fi

  print_kv "mission_api_${result_key}" "FAIL"
  sed -n '1,260p' "${output_file}" || true
  exit 2
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  print_kv "mission_api_skeleton_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  (
    cd "${REPO_ROOT}"
    colcon build --symlink-install --packages-select go2w_control go2w_navigation go2w_mission
  )
  source_file_checked "${REPO_SETUP}" "repo_setup"

  ./tools/cleanup_sim_runtime.sh

  local nav_share
  nav_share="$(ros2 pkg prefix go2w_navigation)/share/go2w_navigation"
  GRAPH_FILE="${nav_share}/graphs/phase3c_hospital_multifloor_route.geojson"
  if [ ! -f "${GRAPH_FILE}" ]; then
    print_kv "mission_graph_file" "MISSING:${GRAPH_FILE}"
    exit 2
  fi
  print_kv "mission_graph_file" "${GRAPH_FILE}"

  setsid ros2 launch go2w_mission mission_api.launch.py \
    use_sim_time:=false \
    log_level:=info \
    >"${EVIDENCE_DIR}/mission_api_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_node "/route_server" 60
  wait_for_node "/go2w_command_gate" 60
  wait_for_node "/go2w_stair_executor" 60
  wait_for_node "/go2w_flat_nav_executor" 60
  wait_for_node "/go2w_mission_api" 60
  wait_for_lifecycle_active "route_server" 60
  wait_for_action "/compute_route" 60
  wait_for_action "/navigate_to_pose" 60
  wait_for_action "/stair_exec" 60
  wait_for_action "/go2w/mission/run" 60

  export MISSION_API_GRAPH_FILE="${GRAPH_FILE}"
  export MISSION_API_RESULT_TIMEOUT_SEC="10.0"
  export MISSION_API_FLAT_TIMEOUT_SEC="4.0"
  export MISSION_API_STAIR_DURATION_SEC="1.5"
  export MISSION_API_CANCEL_DELAY_SEC="0.2"

  run_goal_case "success" "success"
  run_goal_case "invalid_goal" "invalid_goal"
  run_goal_case "cancel" "cancel"

  terminate_pid "${LAUNCH_PID}" "mission_api_launch"
  LAUNCH_PID=""

  setsid ros2 launch go2w_mission mission_api.launch.py \
    use_sim_time:=false \
    launch_flat_nav_executor:=false \
    log_level:=info \
    >"${EVIDENCE_DIR}/mission_api_unavailable_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_node "/route_server" 60
  wait_for_node "/go2w_command_gate" 60
  wait_for_node "/go2w_stair_executor" 60
  wait_for_node "/go2w_mission_api" 60
  wait_for_lifecycle_active "route_server" 60
  wait_for_action "/compute_route" 60
  wait_for_action "/stair_exec" 60
  wait_for_action "/go2w/mission/run" 60

  run_goal_case "flat_unavailable" "unavailable_action"

  print_kv "mission_api_skeleton_result" "PASS"
}

main "$@"
