#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE4A_EVIDENCE_DIR:-/tmp/go2w_phase4a_stair_handoff_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 80 ))}"
REBUILD_REPO="${GO2W_PHASE4A_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_PHASE4A_CLEAN_EVIDENCE:-0}"
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

process_group_alive() {
  local pid="$1"
  kill -0 "${pid}" 2>/dev/null || pgrep -g "${pid}" >/dev/null 2>&1
}

signal_process_group() {
  local signal_name="$1"
  local pid="$2"
  kill -"${signal_name}" -- "-${pid}" 2>/dev/null || kill -"${signal_name}" "${pid}" 2>/dev/null || true
}

cleanup() {
  terminate_pid "${LAUNCH_PID}" "phase4a_launch"
  if [ "${CLEAN_EVIDENCE}" = "1" ]; then
    rm -rf "${EVIDENCE_DIR}"
  fi
}

trap cleanup EXIT

maybe_build_repo() {
  if [ "${REBUILD_REPO}" = "1" ] || [ ! -f "${REPO_SETUP}" ]; then
    source_file_checked "${ROS_SETUP}" "ros_setup"
    (
      cd "${REPO_ROOT}"
      colcon build --symlink-install --packages-select go2w_control go2w_mission go2w_navigation
    )
  fi
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
    if [ -n "${LAUNCH_PID}" ] && ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
      print_kv "phase4a_launch" "exited_early"
      sed -n '1,260p' "${EVIDENCE_DIR}/phase4a_launch.log" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "node_${node_name}" "MISSING"
  timeout 5s ros2 node list >"${EVIDENCE_DIR}/nodes_timeout.txt" 2>&1 || true
  sed -n '1,260p' "${EVIDENCE_DIR}/phase4a_launch.log" || true
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
  sed -n '1,260p' "${EVIDENCE_DIR}/phase4a_launch.log" || true
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
  exit 2
}

run_handoff_mode() {
  local mode="$1"
  local result_timeout="$2"
  local output_file="${EVIDENCE_DIR}/handoff_${mode}.txt"
  local graph_file="$3"

  if ! timeout 30s ros2 run go2w_mission go2w_phase4a_handoff_demo \
    --graph-file "${graph_file}" \
    --mode "${mode}" \
    --expected-duration-sec 0.3 \
    --result-timeout-sec "${result_timeout}" >"${output_file}" 2>&1; then
    print_kv "handoff_${mode}" "FAIL"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  fi

  case "${mode}" in
    success|failure|cancel)
      if grep -qx "phase4a_handoff_result: PASS" "${output_file}"; then
        print_kv "handoff_${mode}" "PASS"
        return
      fi
      ;;
    timeout)
      if grep -qx "stair_exec_timeout: PASS" "${output_file}"; then
        print_kv "handoff_${mode}" "PASS"
        return
      fi
      ;;
  esac

  print_kv "handoff_${mode}" "FAIL_NO_PASS_KEY"
  sed -n '1,240p' "${output_file}" || true
  exit 2
}

verify_command_gate() {
  local output_file="${EVIDENCE_DIR}/command_gate_probe.txt"

  if ! timeout 20s python3 >"${output_file}" 2>&1 <<'PY'
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def spin_for(node: Node, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while rclpy.ok() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)


def wait_until(node: Node, label: str, predicate, timeout_sec: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and time.monotonic() < deadline:
        if predicate():
            print_kv(label, "PASS")
            return
        rclpy.spin_once(node, timeout_sec=0.05)
    print_kv(label, "FAIL_TIMEOUT")
    raise SystemExit(2)


def publish_owner(node: Node, pub, owner: str, active_owner_values: list[str]) -> None:
    msg = String()
    msg.data = owner
    active_owner_values.clear()
    deadline = time.monotonic() + 2.0
    while rclpy.ok() and time.monotonic() < deadline:
        pub.publish(msg)
        spin_for(node, 0.05)
        if active_owner_values and active_owner_values[-1] == owner:
            print_kv(f"owner_{owner}_ack", "PASS")
            return
    print_kv(f"owner_{owner}_ack", "FAIL_TIMEOUT")
    raise SystemExit(2)


def publish_twist_until_forwarded(
    node: Node,
    pub,
    cmd_vel_messages: list[Twist],
    linear_x: float,
) -> bool:
    msg = Twist()
    msg.linear.x = linear_x
    deadline = time.monotonic() + 1.5
    while rclpy.ok() and time.monotonic() < deadline:
        pub.publish(msg)
        spin_for(node, 0.05)
        if cmd_vel_messages:
            return True
    return False


def publish_twist_for(node: Node, pub, linear_x: float, seconds: float = 0.5) -> None:
    msg = Twist()
    msg.linear.x = linear_x
    deadline = time.monotonic() + seconds
    while rclpy.ok() and time.monotonic() < deadline:
        pub.publish(msg)
        spin_for(node, 0.05)


rclpy.init()
node = Node("phase4a_command_gate_probe")
owner_pub = node.create_publisher(String, "/go2w/control/command_owner", 10)
flat_pub = node.create_publisher(Twist, "/go2w/control/flat_cmd_vel", 10)
stair_pub = node.create_publisher(Twist, "/go2w/control/stair_cmd_vel", 10)
cmd_vel_messages = []
active_owner_values = []
node.create_subscription(Twist, "/cmd_vel", lambda msg: cmd_vel_messages.append(msg), 10)
node.create_subscription(String, "/go2w/control/active_owner", lambda msg: active_owner_values.append(msg.data), 10)

try:
    wait_until(
        node,
        "command_gate_discovery",
        lambda: owner_pub.get_subscription_count() > 0
        and flat_pub.get_subscription_count() > 0
        and stair_pub.get_subscription_count() > 0
        and node.count_publishers("/cmd_vel") > 0,
    )
    publish_owner(node, owner_pub, "flat", active_owner_values)
    cmd_vel_messages.clear()
    if not publish_twist_until_forwarded(node, flat_pub, cmd_vel_messages, 0.11):
        print_kv("flat_owner_flat_cmd", "FAIL_NO_FORWARD")
        raise SystemExit(2)
    print_kv("flat_owner_flat_cmd", "PASS")

    publish_owner(node, owner_pub, "stair", active_owner_values)
    cmd_vel_messages.clear()
    publish_twist_for(node, flat_pub, 0.12)
    if cmd_vel_messages:
        print_kv("stair_owner_flat_cmd_muted", "FAIL_FORWARDED")
        raise SystemExit(2)
    print_kv("stair_owner_flat_cmd_muted", "PASS")

    cmd_vel_messages.clear()
    if not publish_twist_until_forwarded(node, stair_pub, cmd_vel_messages, 0.13):
        print_kv("stair_owner_stair_cmd", "FAIL_NO_FORWARD")
        raise SystemExit(2)
    print_kv("stair_owner_stair_cmd", "PASS")

    publish_owner(node, owner_pub, "flat", active_owner_values)
    cmd_vel_messages.clear()
    publish_twist_for(node, stair_pub, 0.14)
    if cmd_vel_messages:
        print_kv("flat_owner_stair_cmd_muted", "FAIL_FORWARDED")
        raise SystemExit(2)
    print_kv("flat_owner_stair_cmd_muted", "PASS")
finally:
    node.destroy_node()
    rclpy.shutdown()
PY
  then
    print_kv "command_gate_probe" "FAIL"
    sed -n '1,240p' "${output_file}" || true
    exit 2
  fi

  sed -n '1,120p' "${output_file}"
  print_kv "command_gate_probe" "PASS"
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"

  print_kv "phase4a_stair_handoff_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"

  maybe_build_repo
  source_file_checked "${REPO_SETUP}" "repo_setup"

  local nav_share
  local graph_file
  nav_share="$(ros2 pkg prefix go2w_navigation)/share/go2w_navigation"
  graph_file="${nav_share}/graphs/phase3c_hospital_multifloor_route.geojson"
  [ -f "${graph_file}" ] || { print_kv "phase4a_graph_file" "MISSING:${graph_file}"; exit 2; }
  print_kv "phase4a_graph_file" "${graph_file}"

  setsid ros2 launch go2w_mission phase4a_stair_handoff.launch.py \
    use_sim_time:=false >"${EVIDENCE_DIR}/phase4a_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_node "/route_server" 45
  wait_for_node "/go2w_command_gate" 45
  wait_for_node "/go2w_stair_executor" 45
  wait_for_lifecycle_active "/route_server" 45
  wait_for_action "/compute_route" 30
  wait_for_action "/stair_exec" 30

  verify_command_gate
  run_handoff_mode "success" "4.0" "${graph_file}"
  run_handoff_mode "failure" "4.0" "${graph_file}"
  run_handoff_mode "cancel" "4.0" "${graph_file}"
  run_handoff_mode "timeout" "0.5" "${graph_file}"

  print_kv "phase4a_stair_handoff_result" "PASS"
}

main "$@"
