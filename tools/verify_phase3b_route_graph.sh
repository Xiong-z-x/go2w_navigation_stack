#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE3B_EVIDENCE_DIR:-/tmp/go2w_phase3b_route_graph_${$}}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 80 ))}"
REBUILD_REPO="${GO2W_PHASE3B_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_PHASE3B_CLEAN_EVIDENCE:-0}"
ROUTE_START_ID="${GO2W_PHASE3B_ROUTE_START_ID:-0}"
ROUTE_GOAL_ID="${GO2W_PHASE3B_ROUTE_GOAL_ID:-3}"
ROUTE_PID=""

set -u

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

terminate_pid() {
  local pid="$1"
  local label="$2"
  local attempts_remaining=5

  if [ -z "${pid}" ] || ! kill -0 "${pid}" 2>/dev/null; then
    return
  fi

  kill -INT "${pid}" 2>/dev/null || true
  while [ "${attempts_remaining}" -gt 0 ]; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      wait "${pid}" 2>/dev/null || true
      return
    fi
    sleep 1
    attempts_remaining=$((attempts_remaining - 1))
  done

  print_kv "cleanup_${label}" "forced_terminate"
  kill -TERM "${pid}" 2>/dev/null || true
  sleep 1
  if kill -0 "${pid}" 2>/dev/null; then
    kill -KILL "${pid}" 2>/dev/null || true
  fi
  wait "${pid}" 2>/dev/null || true
}

cleanup() {
  terminate_pid "${ROUTE_PID}" "route"
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
      colcon build --symlink-install --packages-select go2w_navigation
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
    if [ -n "${ROUTE_PID}" ] && ! kill -0 "${ROUTE_PID}" 2>/dev/null; then
      print_kv "route_process" "exited_early"
      sed -n '1,260p' "${EVIDENCE_DIR}/route_server.log" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "node_${node_name}" "MISSING"
  timeout 5s ros2 node list >"${EVIDENCE_DIR}/nodes_timeout.txt" 2>&1 || true
  sed -n '1,260p' "${EVIDENCE_DIR}/route_server.log" || true
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
    if [ -n "${ROUTE_PID}" ] && ! kill -0 "${ROUTE_PID}" 2>/dev/null; then
      print_kv "route_process" "exited_early"
      sed -n '1,260p' "${EVIDENCE_DIR}/route_server.log" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "route_server_lifecycle" "FAIL"
  sed -n '1,160p' "${output_file}" || true
  sed -n '1,260p' "${EVIDENCE_DIR}/route_server.log" || true
  exit 2
}

require_param_value() {
  local key="$1"
  local node="$2"
  local parameter="$3"
  local expected="$4"
  local output_file="${EVIDENCE_DIR}/${key}.txt"

  if ! timeout 10s ros2 param get "${node}" "${parameter}" >"${output_file}" 2>&1; then
    print_kv "${key}" "FAIL_NO_PARAM"
    sed -n '1,120p' "${output_file}" || true
    exit 2
  fi
  if grep -qx "String value is: ${expected}" "${output_file}"; then
    print_kv "${key}" "${expected}"
    return
  fi
  print_kv "${key}" "FAIL"
  sed -n '1,120p' "${output_file}" || true
  exit 2
}

require_service_reload() {
  local graph_file="$1"
  local output_file="${EVIDENCE_DIR}/set_route_graph.txt"

  if ! timeout 20s ros2 service call /route_server/set_route_graph nav2_msgs/srv/SetRouteGraph \
    "{graph_filepath: '${graph_file}'}" >"${output_file}" 2>&1; then
    print_kv "set_route_graph" "FAIL_CALL"
    sed -n '1,180p' "${output_file}" || true
    exit 2
  fi
  if grep -Eq "success[:=] true|success=True" "${output_file}"; then
    print_kv "set_route_graph" "PASS"
    return
  fi
  print_kv "set_route_graph" "FAIL"
  sed -n '1,180p' "${output_file}" || true
  exit 2
}

require_route_graph_marker() {
  local output_file="${EVIDENCE_DIR}/route_graph_marker.txt"

  if ! timeout 15s ros2 topic echo --once /route_graph >"${output_file}" 2>&1; then
    print_kv "route_graph_marker" "FAIL_NO_MESSAGE"
    sed -n '1,180p' "${output_file}" || true
    exit 2
  fi
  if grep -q "frame_id: odom" "${output_file}"; then
    print_kv "route_graph_marker_frame" "odom"
    return
  fi
  print_kv "route_graph_marker_frame" "FAIL"
  sed -n '1,220p' "${output_file}" || true
  exit 2
}

require_compute_route() {
  local output_file="${EVIDENCE_DIR}/compute_route_summary.txt"

  if ! timeout 30s python3 - "${ROUTE_START_ID}" "${ROUTE_GOAL_ID}" >"${output_file}" 2>&1 <<'PY'
import sys
import time

from action_msgs.msg import GoalStatus
import rclpy
from nav2_msgs.action import ComputeRoute
from rclpy.action import ActionClient
from rclpy.node import Node


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}")


def spin_until(node: Node, future, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    return future.done()


start_id = int(sys.argv[1])
goal_id = int(sys.argv[2])

rclpy.init()
node = Node("phase3b_compute_route_probe")
client = ActionClient(node, ComputeRoute, "/compute_route")

try:
    if not client.wait_for_server(timeout_sec=10.0):
        print_kv("compute_route_action_server", "FAIL_UNAVAILABLE")
        sys.exit(2)

    goal = ComputeRoute.Goal()
    goal.start_id = start_id
    goal.goal_id = goal_id
    goal.use_start = False
    goal.use_poses = False

    send_future = client.send_goal_async(goal)
    if not spin_until(node, send_future, 10.0):
        print_kv("compute_route_goal_response", "FAIL_TIMEOUT")
        sys.exit(2)

    goal_handle = send_future.result()
    if goal_handle is None or not goal_handle.accepted:
        print_kv("compute_route_goal_accepted", "False")
        sys.exit(2)
    print_kv("compute_route_goal_accepted", "True")

    result_future = goal_handle.get_result_async()
    if not spin_until(node, result_future, 10.0):
        print_kv("compute_route_result", "FAIL_TIMEOUT")
        sys.exit(2)

    wrapped = result_future.result()
    result = wrapped.result
    node_ids = ",".join(str(route_node.nodeid) for route_node in result.route.nodes)
    edge_ids = ",".join(str(edge.edgeid) for edge in result.route.edges)

    print_kv("compute_route_action_status", wrapped.status)
    print_kv("compute_route_path_frame", result.path.header.frame_id)
    print_kv("compute_route_route_frame", result.route.header.frame_id)
    print_kv("compute_route_path_poses", len(result.path.poses))
    print_kv("compute_route_route_nodes", len(result.route.nodes))
    print_kv("compute_route_route_edges", len(result.route.edges))
    print_kv("compute_route_node_ids", node_ids)
    print_kv("compute_route_edge_ids", edge_ids)
    print_kv("compute_route_route_cost", result.route.route_cost)

    if wrapped.status != GoalStatus.STATUS_SUCCEEDED:
        sys.exit(2)
    if result.path.header.frame_id != "odom" or result.route.header.frame_id != "odom":
        sys.exit(2)
    if len(result.route.nodes) < 2 or len(result.route.edges) < 1 or len(result.path.poses) < 2:
        sys.exit(2)
finally:
    node.destroy_node()
    rclpy.shutdown()
PY
  then
    print_kv "compute_route" "FAIL"
    sed -n '1,220p' "${output_file}" || true
    exit 2
  fi

  print_kv "compute_route" "PASS"
  sed -n '1,80p' "${output_file}"
}

require_forbidden_nodes_absent() {
  local output_file="${EVIDENCE_DIR}/nodes_final.txt"
  timeout 10s ros2 node list >"${output_file}" 2>&1 || true

  if grep -Eiq "mission|stair|multi.?floor|elevation|traversability|map_server|amcl" "${output_file}"; then
    print_kv "forbidden_later_phase_nodes" "PRESENT"
    sed -n '1,160p' "${output_file}" || true
    exit 2
  fi
  print_kv "forbidden_later_phase_nodes" "ABSENT"
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"

  print_kv "phase3b_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"

  maybe_build_repo
  source_file_checked "${REPO_SETUP}" "repo_setup"

  local graph_file
  graph_file="$(ros2 pkg prefix go2w_navigation)/share/go2w_navigation/graphs/phase3b_same_floor_route.geojson"
  if [ ! -f "${graph_file}" ]; then
    print_kv "phase3b_graph_file" "MISSING:${graph_file}"
    exit 2
  fi
  print_kv "phase3b_graph_file" "${graph_file}"

  ros2 launch go2w_navigation phase3b_route_graph.launch.py \
    use_sim_time:=false \
    graph_file:="${graph_file}" >"${EVIDENCE_DIR}/route_server.log" 2>&1 &
  ROUTE_PID="$!"

  wait_for_node "/route_server" 45
  wait_for_lifecycle_active "/route_server" 45
  require_param_value "route_frame" "/route_server" "route_frame" "odom"
  require_param_value "global_frame" "/route_server" "global_frame" "odom"
  require_param_value "base_frame" "/route_server" "base_frame" "base_link"
  require_service_reload "${graph_file}"
  require_compute_route
  require_route_graph_marker
  require_forbidden_nodes_absent

  print_kv "phase3b_result" "PASS"
}

main "$@"
