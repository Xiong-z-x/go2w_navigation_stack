#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_CACHE_ROOT="${GO2W_FASTLIO_CACHE_ROOT:-${REPO_ROOT}/.go2w_external}"
FASTLIO_WS="${GO2W_FASTLIO_WS:-${FASTLIO_CACHE_ROOT}/workspaces/fast_lio_ros2}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
FASTLIO_SETUP="${FASTLIO_WS}/install/setup.bash"
EVIDENCE_DIR="${GO2W_MISSION_REAL_FSF_EVIDENCE_DIR:-/tmp/go2w_mission_real_flat_stair_flat_$$}"
ROUTE_WORLD="${GO2W_MISSION_REAL_FSF_WORLD:-${REPO_ROOT}/install/go2w_sim/share/go2w_sim/worlds/phase3a_feature_world.sdf}"
ROUTE_WORLD_NAME="${GO2W_MISSION_REAL_FSF_WORLD_NAME:-go2w_phase3a_feature_world}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 90) + 130 ))}"
PARTITION="go2w_mission_real_fsf_$$"
REBUILD_REPO="${GO2W_MISSION_REAL_FSF_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_MISSION_REAL_FSF_CLEAN_EVIDENCE:-0}"
CLEAN_STALE_PROCESSES="${GO2W_MISSION_REAL_FSF_CLEAN_STALE_PROCESSES:-1}"
NAV_TIMEOUT_SECONDS="${GO2W_MISSION_REAL_FSF_NAV_TIMEOUT_SECONDS:-140}"
STAIR_TIMEOUT_SECONDS="${GO2W_MISSION_REAL_FSF_STAIR_TIMEOUT_SECONDS:-8.0}"
STAIR_EXPECTED_SECONDS="${GO2W_MISSION_REAL_FSF_STAIR_EXPECTED_SECONDS:-0.8}"
FIRST_FLAT_OFFSET_X="${GO2W_MISSION_REAL_FSF_FIRST_FLAT_OFFSET_X:-0.120}"
STAIR_HANDOFF_OFFSET_X="${GO2W_MISSION_REAL_FSF_STAIR_HANDOFF_OFFSET_X:-0.030}"
SECOND_FLAT_OFFSET_X="${GO2W_MISSION_REAL_FSF_SECOND_FLAT_OFFSET_X:-0.120}"
MIN_PERCEPTION_ODOM_DELTA="${GO2W_MISSION_REAL_FSF_MIN_PERCEPTION_ODOM_DELTA:-0.006}"
MIN_DIFF_DRIVE_ODOM_DELTA="${GO2W_MISSION_REAL_FSF_MIN_DIFF_DRIVE_ODOM_DELTA:-0.006}"
NAV2_PARAMS_FILE="${GO2W_MISSION_REAL_FSF_NAV2_PARAMS_FILE:-${REPO_ROOT}/go2w_navigation/config/phase5_real_model_nav2_same_floor.yaml}"
ROUTE_PARAMS_FILE="${GO2W_MISSION_REAL_FSF_ROUTE_PARAMS_FILE:-${REPO_ROOT}/go2w_navigation/config/phase3b_route_server.yaml}"
MISSION_STATE_FILE="${GO2W_MISSION_REAL_FSF_STATE_FILE:-${EVIDENCE_DIR}/mission_state.json}"

FASTLIO_PID=""
PERCEPTION_PID=""
SIM_PID=""
NAV2_PID=""
MISSION_PID=""

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

collect_matching_pgids() {
  local current_pgid
  current_pgid="$(ps -o pgid= -p "$$" | tr -d '[:space:]')"

  ps -eo pid=,pgid=,args= | while read -r pid pgid args; do
    if [ -z "${pid}" ] || [ -z "${pgid}" ] || [ "${pgid}" = "${current_pgid}" ]; then
      continue
    fi

    local matched=1
    local needle
    for needle in "$@"; do
      if [[ "${args}" != *"${needle}"* ]]; then
        matched=0
        break
      fi
    done
    if [ "${matched}" = "1" ]; then
      printf '%s\n' "${pgid}"
    fi
  done | sort -u
}

terminate_matching_processes() {
  local label="$1"
  shift
  local pgids=()
  local remaining=()

  mapfile -t pgids < <(collect_matching_pgids "$@" || true)
  if [ "${#pgids[@]}" -eq 0 ]; then
    return
  fi

  print_kv "cleanup_stale_${label}" "${pgids[*]}"
  local pgid
  for pgid in "${pgids[@]}"; do
    signal_process_group "TERM" "${pgid}"
  done
  sleep 1

  mapfile -t remaining < <(collect_matching_pgids "$@" || true)
  for pgid in "${remaining[@]}"; do
    signal_process_group "KILL" "${pgid}"
  done
}

cleanup_stale_processes() {
  if [ "${CLEAN_STALE_PROCESSES}" != "1" ]; then
    return
  fi

  terminate_matching_processes "mission_real_fsf_client" "/tmp/go2w_mission_real_flat_stair_flat_" "mission_real_flat_stair_flat_client.py"
  terminate_matching_processes "fastlio" "fast_lio" "fastlio_mapping" "go2w_mission_real_fsf"
  terminate_matching_processes "perception" "ros2 launch go2w_perception phase2f_tf_authority.launch.py"
  terminate_matching_processes "mission_api" "ros2 launch go2w_mission mission_api.launch.py"
  terminate_matching_processes "nav2" "ros2 launch go2w_navigation phase3a_nav2_same_floor.launch.py"
  terminate_matching_processes "sim" "ros2 launch go2w_sim sim_go2w_real.launch.py"
  terminate_matching_processes "ign_gazebo" "ign gazebo" "phase3a_feature_world.sdf"
  "${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true
}

cleanup() {
  terminate_pid "${MISSION_PID}" "mission_api"
  terminate_pid "${NAV2_PID}" "nav2"
  terminate_pid "${FASTLIO_PID}" "fastlio"
  terminate_matching_processes "fastlio_binary" "${FASTLIO_WS}/install/fast_lio/lib/fast_lio/fastlio_mapping"
  terminate_pid "${PERCEPTION_PID}" "perception"
  terminate_pid "${SIM_PID}" "sim"
  cleanup_stale_processes
  "${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true
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
      colcon build --symlink-install --packages-select \
        go2w_navigation go2w_perception go2w_description go2w_sim go2w_control go2w_mission
    )
  fi
}

wait_for_log() {
  local pattern="$1"
  local file="$2"
  local timeout_seconds="$3"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if grep -qE "${pattern}" "${file}" 2>/dev/null; then
      return 0
    fi
    if [ -n "${SIM_PID}" ] && ! process_group_alive "${SIM_PID}" 2>/dev/null; then
      print_kv "sim_process" "exited_early"
      sed -n '1,260p' "${file}" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  print_kv "wait_for_log" "timeout:${pattern}"
  sed -n '1,260p' "${file}" || true
  exit 2
}

wait_for_text() {
  local pattern="$1"
  local file="$2"
  local timeout_seconds="$3"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if grep -qE "${pattern}" "${file}" 2>/dev/null; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  print_kv "wait_for_text" "timeout:${pattern}"
  sed -n '1,260p' "${file}" || true
  exit 2
}

wait_for_text_count() {
  local pattern="$1"
  local file="$2"
  local expected_count="$3"
  local timeout_seconds="$4"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    local count
    count="$(grep -cE "${pattern}" "${file}" 2>/dev/null || true)"
    if [ "${count}" -ge "${expected_count}" ]; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  print_kv "wait_for_text_count" "timeout:${pattern}:${expected_count}"
  sed -n '1,260p' "${file}" || true
  exit 2
}

wait_for_node() {
  local node_name="$1"
  local timeout_seconds="$2"
  local elapsed=0
  local log_file="${3:-}"

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 3s ros2 node list 2>/dev/null | grep -qx "${node_name}"; then
      print_kv "node_${node_name}" "PRESENT"
      return
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "node_${node_name}" "MISSING"
  if [ -n "${log_file}" ]; then
    sed -n '1,260p' "${log_file}" || true
  fi
  exit 2
}

require_node_absent() {
  local node_name="$1"
  local output_file="$2"
  timeout 5s ros2 node list >"${output_file}" 2>&1 || true
  if grep -qx "${node_name}" "${output_file}"; then
    print_kv "node_${node_name}" "PRESENT"
    sed -n '1,220p' "${output_file}" || true
    exit 2
  fi
  print_kv "node_${node_name}" "ABSENT"
}

wait_for_action() {
  local action_name="$1"
  local timeout_seconds="$2"
  local elapsed=0
  local output_file="${EVIDENCE_DIR}/actions_${action_name//\//_}.txt"

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 5s ros2 action list >"${output_file}" 2>&1 \
      && grep -qx "${action_name}" "${output_file}"; then
      print_kv "action_${action_name}" "PRESENT"
      return
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "action_${action_name}" "MISSING"
  sed -n '1,220p' "${output_file}" || true
  exit 2
}

require_route_graph_reload() {
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

wait_for_lifecycle_active() {
  local key="$1"
  local node="$2"
  local output_file="$3"
  local timeout_seconds="$4"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 4s ros2 lifecycle get "${node}" >"${output_file}" 2>&1; then
      if grep -q "^active \\[3\\]$" "${output_file}"; then
        print_kv "${key}" "active"
        return
      fi
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  print_kv "${key}" "FAIL"
  sed -n '1,120p' "${output_file}" || true
  exit 2
}

wait_for_controller_states_active() {
  local output_file="$1"
  local timeout_seconds="$2"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 20s ros2 control list_controllers >"${output_file}" 2>&1; then
      if grep -q "joint_state_broadcaster.*active" "${output_file}" \
        && grep -q "leg_position_controller.*active" "${output_file}" \
        && grep -q "diff_drive_controller.*active" "${output_file}"; then
        print_kv "joint_state_broadcaster_active" "PASS"
        print_kv "leg_position_controller_active" "PASS"
        print_kv "diff_drive_controller_active" "PASS"
        return
      fi
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  print_kv "controller_states_active" "FAIL"
  sed -n '1,220p' "${output_file}" || true
  exit 2
}

require_process_alive() {
  local pid="$1"
  local key="$2"
  local log_file="$3"
  if [ -z "${pid}" ] || ! process_group_alive "${pid}" 2>/dev/null; then
    print_kv "${key}" "FAIL"
    sed -n '1,260p' "${log_file}" || true
    exit 2
  fi
  print_kv "${key}" "PASS"
}

require_topic_once() {
  local key="$1"
  local topic="$2"
  local output_file="$3"
  local timeout_seconds="$4"
  if ! timeout "${timeout_seconds}s" ros2 topic echo --once "${topic}" >"${output_file}" 2>&1; then
    print_kv "${key}" "FAIL"
    sed -n '1,180p' "${output_file}" || true
    exit 2
  fi
  print_kv "${key}" "PASS"
}

require_field_once() {
  local key="$1"
  local topic="$2"
  local field="$3"
  local expected="$4"
  local output_file="$5"
  local timeout_seconds="$6"
  if ! timeout "${timeout_seconds}s" ros2 topic echo --once "${topic}" --field "${field}" >"${output_file}" 2>&1; then
    print_kv "${key}" "FAIL_NO_MESSAGE"
    sed -n '1,160p' "${output_file}" || true
    exit 2
  fi
  if grep -qx "${expected}" "${output_file}"; then
    print_kv "${key}" "${expected}"
    return
  fi
  print_kv "${key}" "FAIL"
  sed -n '1,160p' "${output_file}" || true
  exit 2
}

require_param_contains() {
  local key="$1"
  local node="$2"
  local parameter="$3"
  local expected="$4"
  local output_file="$5"
  if ! timeout 10s ros2 param get "${node}" "${parameter}" >"${output_file}" 2>&1; then
    print_kv "${key}" "FAIL_NO_PARAM"
    sed -n '1,120p' "${output_file}" || true
    exit 2
  fi
  if grep -q "${expected}" "${output_file}"; then
    print_kv "${key}" "${expected}"
    return
  fi
  print_kv "${key}" "FAIL"
  sed -n '1,120p' "${output_file}" || true
  exit 2
}

require_diff_drive_tf_disabled() {
  local output_file="$1"
  if ! timeout 10s ros2 param get /diff_drive_controller enable_odom_tf >"${output_file}" 2>&1; then
    print_kv "diff_drive_enable_odom_tf" "FAIL_NO_PARAM"
    sed -n '1,120p' "${output_file}" || true
    exit 2
  fi
  if grep -q "False" "${output_file}"; then
    print_kv "diff_drive_enable_odom_tf" "False"
    return
  fi
  print_kv "diff_drive_enable_odom_tf" "FAIL"
  sed -n '1,120p' "${output_file}" || true
  exit 2
}

require_adapted_time_field() {
  local output_file="$1"
  if ! timeout 15s ros2 topic echo --once /fastlio/input/lidar_points --field fields >"${output_file}" 2>&1; then
    print_kv "adapted_pointcloud_time_field" "FAIL_NO_MESSAGE"
    sed -n '1,160p' "${output_file}" || true
    exit 2
  fi
  if grep -Eq "name: time|name='time'" "${output_file}" \
    && grep -Eq "datatype: 7|datatype=7" "${output_file}"; then
    print_kv "adapted_pointcloud_time_field" "PASS"
    return
  fi
  print_kv "adapted_pointcloud_time_field" "FAIL"
  sed -n '1,220p' "${output_file}" || true
  exit 2
}

sample_tf_to() {
  local label="$1"
  local duration_seconds="$2"
  timeout "${duration_seconds}s" ros2 topic echo /tf >"${EVIDENCE_DIR}/tf_${label}_dynamic.txt" 2>&1 || true
  timeout 4s ros2 topic echo --once /tf_static >"${EVIDENCE_DIR}/tf_${label}_static.txt" 2>&1 || true
  cat "${EVIDENCE_DIR}/tf_${label}_dynamic.txt" \
    "${EVIDENCE_DIR}/tf_${label}_static.txt" >"${EVIDENCE_DIR}/tf_${label}_all.txt"
}

tf_edge_present_in_file() {
  local parent="$1"
  local child="$2"
  local tf_file="$3"
  awk -v parent="${parent}" -v child="${child}" '
    $1 == "frame_id:" {
      current_parent=$2
    }
    $1 == "child_frame_id:" {
      if (current_parent == parent && $2 == child) {
        found=1
      }
    }
    END {
      exit(found ? 0 : 1)
    }
  ' "${tf_file}"
}

require_tf_edge_absent() {
  local key="$1"
  local parent="$2"
  local child="$3"
  local tf_file="$4"
  if tf_edge_present_in_file "${parent}" "${child}" "${tf_file}"; then
    print_kv "${key}" "PRESENT"
    sed -n '1,220p' "${tf_file}" || true
    exit 2
  fi
  print_kv "${key}" "ABSENT"
}

require_tf_edge_present() {
  local key="$1"
  local parent="$2"
  local child="$3"
  local tf_file="$4"
  if tf_edge_present_in_file "${parent}" "${child}" "${tf_file}"; then
    print_kv "${key}" "PRESENT"
    return
  fi
  print_kv "${key}" "ABSENT"
  sed -n '1,220p' "${tf_file}" || true
  exit 2
}

require_log_absent() {
  local key="$1"
  local pattern="$2"
  local log_file="$3"
  local count
  count="$(grep -Ec "${pattern}" "${log_file}" || true)"
  print_kv "${key}" "${count}"
  if [ "${count}" != "0" ]; then
    sed -n '1,260p' "${log_file}" || true
    exit 2
  fi
}

write_fastlio_params() {
  cat >"${EVIDENCE_DIR}/mission_real_fsf_fastlio.yaml" <<'EOF'
laser_mapping:
  ros__parameters:
    use_sim_time: true
    common.lid_topic: /fastlio/input/lidar_points
    common.imu_topic: /imu
    common.time_sync_en: false
    common.time_offset_lidar_to_imu: 0.0
    preprocess.lidar_type: 2
    preprocess.scan_line: 16
    preprocess.scan_rate: 10
    preprocess.timestamp_unit: 2
    preprocess.blind: 0.1
    preprocess.point_filter_num: 1
    preprocess.feature_extract_enable: false
    mapping.acc_cov: 0.1
    mapping.gyr_cov: 0.1
    mapping.b_acc_cov: 0.0001
    mapping.b_gyr_cov: 0.0001
    mapping.fov_degree: 180.0
    mapping.det_range: 100.0
    mapping.extrinsic_est_en: true
    mapping.extrinsic_T: [0.0, 0.0, 0.0]
    mapping.extrinsic_R: [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    publish.path_en: true
    publish.scan_publish_en: true
    publish.dense_publish_en: true
    publish.scan_bodyframe_pub_en: true
    publish.map_en: true
    publish.effect_map_en: false
    publish.tf_publish_en: false
    pcd_save.pcd_save_en: false
    pcd_save.interval: -1
EOF
}

write_flat_stair_flat_graph_builder() {
  cat >"${EVIDENCE_DIR}/build_mission_flat_stair_flat_graph.py" <<'PYEOF'
#!/usr/bin/env python3
import json
import math
import os
import sys
import time
from pathlib import Path

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node


def quat_to_yaw(q) -> float:
    siny_cosp = 2.0 * (float(q.w) * float(q.z) + float(q.x) * float(q.y))
    cosy_cosp = 1.0 - 2.0 * (float(q.y) * float(q.y) + float(q.z) * float(q.z))
    return math.atan2(siny_cosp, cosy_cosp)


def forward_point(x: float, y: float, yaw: float, distance: float) -> tuple[float, float]:
    return x + distance * math.cos(yaw), y + distance * math.sin(yaw)


class GraphBuilder(Node):
    def __init__(self) -> None:
        super().__init__("mission_real_flat_stair_flat_graph_builder")
        self.latest_odom = None
        self.create_subscription(Odometry, "/go2w/perception/odom", self._odom_cb, 10)

    def _odom_cb(self, msg: Odometry) -> None:
        self.latest_odom = msg

    def wait_for_settled_odom(self, timeout_sec: float):
        deadline = time.monotonic() + timeout_sec
        settle_deadline = None
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.latest_odom is None:
                continue
            if settle_deadline is None:
                settle_deadline = time.monotonic() + 5.0
                continue
            if time.monotonic() >= settle_deadline:
                return self.latest_odom.pose.pose
        return None


def main() -> int:
    output_path = Path(os.environ["GO2W_MISSION_REAL_FSF_GRAPH_FILE"])
    first_offset = float(os.environ.get("GO2W_MISSION_REAL_FSF_FIRST_FLAT_OFFSET_X", "0.120"))
    stair_offset = float(os.environ.get("GO2W_MISSION_REAL_FSF_STAIR_HANDOFF_OFFSET_X", "0.030"))
    second_offset = float(os.environ.get("GO2W_MISSION_REAL_FSF_SECOND_FLAT_OFFSET_X", "0.120"))

    rclpy.init()
    node = GraphBuilder()
    try:
        pose = node.wait_for_settled_odom(30.0)
        if pose is None:
            print("mission_real_flat_stair_flat_graph_error: no_odom")
            return 2
        yaw = quat_to_yaw(pose.orientation)
        x100 = float(pose.position.x)
        y100 = float(pose.position.y)
        x101, y101 = forward_point(x100, y100, yaw, first_offset)
        x102, y102 = forward_point(x101, y101, yaw, stair_offset)
        x103, y103 = forward_point(x102, y102, yaw, second_offset)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        features = [
            {
                "type": "Feature",
                "properties": {
                    "id": 100,
                    "frame": "odom",
                    "mode": "flat",
                    "floor_id": "F1",
                    "yaw": yaw,
                },
                "geometry": {"type": "Point", "coordinates": [x100, y100]},
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 101,
                    "frame": "odom",
                    "mode": "flat",
                    "floor_id": "F1",
                    "connector_id": "stair_a",
                    "connector_terminal": "lower",
                    "yaw": yaw,
                },
                "geometry": {"type": "Point", "coordinates": [x101, y101]},
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 102,
                    "frame": "odom",
                    "mode": "flat",
                    "floor_id": "F2",
                    "connector_id": "stair_a",
                    "connector_terminal": "upper",
                    "yaw": yaw,
                },
                "geometry": {"type": "Point", "coordinates": [x102, y102]},
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 103,
                    "frame": "odom",
                    "mode": "flat",
                    "floor_id": "F2",
                    "yaw": yaw,
                },
                "geometry": {"type": "Point", "coordinates": [x103, y103]},
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 10,
                    "startid": 100,
                    "endid": 101,
                    "overridable": True,
                    "mode": "flat",
                    "floor_id": "F1",
                },
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [[[x100, y100], [x101, y101]]],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 500,
                    "startid": 101,
                    "endid": 102,
                    "overridable": True,
                    "mode": "stair",
                    "connector_id": "stair_a",
                    "connector_type": "manual_stair",
                    "stair_exec_required": True,
                    "floor_from": "F1",
                    "floor_to": "F2",
                },
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [[[x101, y101], [x102, y102]]],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 20,
                    "startid": 102,
                    "endid": 103,
                    "overridable": True,
                    "mode": "flat",
                    "floor_id": "F2",
                },
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [[[x102, y102], [x103, y103]]],
                },
            },
        ]
        graph = {
            "type": "FeatureCollection",
            "name": "mission_real_flat_stair_flat_odom_route",
            "properties": {
                "frame": "odom",
                "contract": "mission_real_flat_stair_flat_fixture",
                "notes": "Generated from perception odom; stair edge is a short handoff connector for Action dispatch only.",
            },
            "features": features,
        }
        output_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
        print(f"mission_real_flat_stair_flat_graph_file: {output_path}")
        print(f"mission_real_flat_stair_flat_graph_start_x: {x100:.6f}")
        print(f"mission_real_flat_stair_flat_graph_start_y: {y100:.6f}")
        print(f"mission_real_flat_stair_flat_graph_yaw: {yaw:.6f}")
        print(f"mission_real_flat_stair_flat_graph_first_flat_target_x: {x101:.6f}")
        print(f"mission_real_flat_stair_flat_graph_first_flat_target_y: {y101:.6f}")
        print(f"mission_real_flat_stair_flat_graph_second_flat_target_x: {x103:.6f}")
        print(f"mission_real_flat_stair_flat_graph_second_flat_target_y: {y103:.6f}")
        print("mission_real_flat_stair_flat_graph_result: PASS")
        return 0
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
PYEOF
  chmod +x "${EVIDENCE_DIR}/build_mission_flat_stair_flat_graph.py"
}

write_mission_client() {
  cat >"${EVIDENCE_DIR}/mission_real_flat_stair_flat_client.py" <<'PYEOF'
#!/usr/bin/env python3
import os
import sys
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from go2w_mission.action import RunMission
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node


STATUS_NAMES = {
    GoalStatus.STATUS_UNKNOWN: "UNKNOWN",
    GoalStatus.STATUS_ACCEPTED: "ACCEPTED",
    GoalStatus.STATUS_EXECUTING: "EXECUTING",
    GoalStatus.STATUS_CANCELING: "CANCELING",
    GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED",
    GoalStatus.STATUS_CANCELED: "CANCELED",
    GoalStatus.STATUS_ABORTED: "ABORTED",
}


class MissionRealFlatStairFlatClient(Node):
    def __init__(self) -> None:
        super().__init__("mission_real_flat_stair_flat_client")
        self.client = ActionClient(self, RunMission, "/go2w/mission/run")
        self.latest_odom = None
        self.start_odom = None
        self.latest_diff_drive_odom = None
        self.start_diff_drive_odom = None
        self.cmd_vel_count = 0
        self.max_linear_x = 0.0
        self.max_angular_z = 0.0
        self.feedback_states = []
        self.create_subscription(Odometry, "/go2w/perception/odom", self._odom_cb, 10)
        self.create_subscription(Odometry, "/diff_drive_controller/odom", self._diff_drive_odom_cb, 10)
        self.create_subscription(Twist, "/cmd_vel", self._cmd_vel_cb, 10)

    def _odom_cb(self, msg: Odometry) -> None:
        self.latest_odom = msg
        if self.start_odom is None:
            self.start_odom = msg

    def _diff_drive_odom_cb(self, msg: Odometry) -> None:
        self.latest_diff_drive_odom = msg
        if self.start_diff_drive_odom is None:
            self.start_diff_drive_odom = msg

    def _cmd_vel_cb(self, msg: Twist) -> None:
        linear_x = float(msg.linear.x)
        angular_z = float(msg.angular.z)
        if abs(linear_x) > 1.0e-4 or abs(angular_z) > 1.0e-4:
            self.cmd_vel_count += 1
        self.max_linear_x = max(self.max_linear_x, abs(linear_x))
        self.max_angular_z = max(self.max_angular_z, abs(angular_z))

    def _feedback_cb(self, feedback_msg) -> None:
        feedback = feedback_msg.feedback
        state = (
            f"{feedback.current_segment_index}:"
            f"{feedback.current_segment_type}:"
            f"{feedback.active_owner}:"
            f"{feedback.state}"
        )
        self.feedback_states.append(state)
        print(f"mission_real_flat_stair_flat_feedback: {state}", flush=True)

    def wait_future(self, future, timeout_sec: float) -> bool:
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        return future.done()

    def wait_for_odom(self, timeout_sec: float) -> bool:
        deadline = time.monotonic() + timeout_sec
        settle_deadline = None
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.latest_odom is None or self.latest_diff_drive_odom is None:
                continue
            if settle_deadline is None:
                settle_deadline = time.monotonic() + 2.0
                continue
            if time.monotonic() >= settle_deadline:
                self.start_odom = self.latest_odom
                self.start_diff_drive_odom = self.latest_diff_drive_odom
                self.cmd_vel_count = 0
                self.max_linear_x = 0.0
                self.max_angular_z = 0.0
                return True
        return False

    def send_goal_and_wait(self) -> int:
        graph_file = os.environ["GO2W_MISSION_REAL_FSF_GRAPH_FILE"]
        nav_timeout_sec = float(os.environ.get("GO2W_MISSION_REAL_FSF_NAV_TIMEOUT_SECONDS", "140"))
        stair_timeout_sec = float(os.environ.get("GO2W_MISSION_REAL_FSF_STAIR_TIMEOUT_SECONDS", "8.0"))
        stair_expected_sec = float(os.environ.get("GO2W_MISSION_REAL_FSF_STAIR_EXPECTED_SECONDS", "0.8"))
        min_perception_delta = float(os.environ.get("GO2W_MISSION_REAL_FSF_MIN_PERCEPTION_ODOM_DELTA", "0.006"))
        min_diff_drive_delta = float(os.environ.get("GO2W_MISSION_REAL_FSF_MIN_DIFF_DRIVE_ODOM_DELTA", "0.006"))

        if not self.wait_for_odom(20.0):
            print("mission_real_flat_stair_flat_error: no_start_odom")
            return 2
        if not self.client.wait_for_server(timeout_sec=30.0):
            print("mission_real_flat_stair_flat_error: mission_action_unavailable")
            return 2

        goal = RunMission.Goal()
        goal.start_id = 100
        goal.goal_id = 103
        goal.graph_file = graph_file
        goal.route_frame_id = "odom"
        goal.expected_stair_duration_sec = stair_expected_sec
        goal.result_timeout_sec = stair_timeout_sec
        goal.flat_result_timeout_sec = nav_timeout_sec

        send_future = self.client.send_goal_async(goal, feedback_callback=self._feedback_cb)
        if not self.wait_future(send_future, 10.0):
            print("mission_real_flat_stair_flat_error: goal_response_timeout")
            return 2
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print("mission_real_flat_stair_flat_error: goal_rejected")
            return 2

        result_future = goal_handle.get_result_async()
        if not self.wait_future(result_future, (nav_timeout_sec * 2.0) + stair_timeout_sec + 30.0):
            print("mission_real_flat_stair_flat_error: result_timeout")
            cancel_future = goal_handle.cancel_goal_async()
            self.wait_future(cancel_future, 5.0)
            return 2

        wrapped = result_future.result()
        result = wrapped.result
        status_name = STATUS_NAMES.get(wrapped.status, str(wrapped.status))
        print(f"mission_real_flat_stair_flat_goal_status: {status_name}")
        print(f"mission_real_flat_stair_flat_goal_success: {result.success}")
        print(f"mission_real_flat_stair_flat_goal_result_code: {result.result_code}")
        print(f"mission_real_flat_stair_flat_goal_message: {result.message}")
        print(f"mission_real_flat_stair_flat_segment_count: {result.segment_count}")
        print(f"mission_real_flat_stair_flat_segment_summary: {result.segment_summary}")

        for _ in range(10):
            rclpy.spin_once(self, timeout_sec=0.1)

        if self.latest_odom is None or self.latest_diff_drive_odom is None:
            print("mission_real_flat_stair_flat_error: missing_final_odom")
            return 2

        start_pose = self.start_odom.pose.pose
        final_pose = self.latest_odom.pose.pose
        dx = float(final_pose.position.x) - float(start_pose.position.x)
        dy = float(final_pose.position.y) - float(start_pose.position.y)
        delta_xy = (dx * dx + dy * dy) ** 0.5

        diff_start = self.start_diff_drive_odom.pose.pose
        diff_final = self.latest_diff_drive_odom.pose.pose
        diff_dx = float(diff_final.position.x) - float(diff_start.position.x)
        diff_dy = float(diff_final.position.y) - float(diff_start.position.y)
        diff_delta_xy = (diff_dx * diff_dx + diff_dy * diff_dy) ** 0.5

        print(f"mission_real_flat_stair_flat_perception_odom_delta_x: {dx:.6f}")
        print(f"mission_real_flat_stair_flat_perception_odom_delta_y: {dy:.6f}")
        print(f"mission_real_flat_stair_flat_perception_odom_delta_xy: {delta_xy:.6f}")
        print(f"mission_real_flat_stair_flat_diff_drive_odom_delta_x: {diff_dx:.6f}")
        print(f"mission_real_flat_stair_flat_diff_drive_odom_delta_y: {diff_dy:.6f}")
        print(f"mission_real_flat_stair_flat_diff_drive_odom_delta_xy: {diff_delta_xy:.6f}")
        print(f"mission_real_flat_stair_flat_cmd_vel_nonzero_count: {self.cmd_vel_count}")
        print(f"mission_real_flat_stair_flat_cmd_vel_max_linear_x: {self.max_linear_x:.6f}")
        print(f"mission_real_flat_stair_flat_cmd_vel_max_angular_z: {self.max_angular_z:.6f}")

        expected_summary = "flat:10;stair:500:stair_a:F1->F2;flat:20"
        if wrapped.status != GoalStatus.STATUS_SUCCEEDED or not result.success:
            print("mission_real_flat_stair_flat_result: FAIL_STATUS")
            return 2
        if result.result_code != "MISSION_SUCCEEDED":
            print("mission_real_flat_stair_flat_result: FAIL_RESULT_CODE")
            return 2
        if result.segment_count != 3 or result.segment_summary != expected_summary:
            print("mission_real_flat_stair_flat_result: FAIL_SEGMENT_SUMMARY")
            return 2
        if self.cmd_vel_count < 4:
            print("mission_real_flat_stair_flat_result: FAIL_NO_CMD_VEL")
            return 2
        if delta_xy < min_perception_delta:
            print("mission_real_flat_stair_flat_result: FAIL_NO_PERCEPTION_ODOM_MOTION")
            return 2
        if diff_delta_xy < min_diff_drive_delta:
            print("mission_real_flat_stair_flat_result: FAIL_NO_DIFF_DRIVE_ODOM_MOTION")
            return 2

        print("mission_real_flat_stair_flat_result: PASS")
        return 0


def main() -> int:
    rclpy.init()
    node = MissionRealFlatStairFlatClient()
    try:
        return node.send_goal_and_wait()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
PYEOF
  chmod +x "${EVIDENCE_DIR}/mission_real_flat_stair_flat_client.py"
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  export GZ_PARTITION="${PARTITION}"

  print_kv "go2w_mission_real_flat_stair_flat_result" "RUNNING"
  print_kv "repo_root" "${REPO_ROOT}"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"
  print_kv "gz_partition" "${GZ_PARTITION}"
  print_kv "route_world" "${ROUTE_WORLD}"
  print_kv "route_world_name" "${ROUTE_WORLD_NAME}"
  print_kv "nav2_params_file" "${NAV2_PARAMS_FILE}"
  print_kv "route_params_file" "${ROUTE_PARAMS_FILE}"
  print_kv "mission_state_file" "${MISSION_STATE_FILE}"
  print_kv "nav_timeout_seconds" "${NAV_TIMEOUT_SECONDS}"
  print_kv "stair_timeout_seconds" "${STAIR_TIMEOUT_SECONDS}"
  print_kv "stair_expected_seconds" "${STAIR_EXPECTED_SECONDS}"
  print_kv "first_flat_offset_x" "${FIRST_FLAT_OFFSET_X}"
  print_kv "stair_handoff_offset_x" "${STAIR_HANDOFF_OFFSET_X}"
  print_kv "second_flat_offset_x" "${SECOND_FLAT_OFFSET_X}"
  print_kv "clean_stale_processes" "${CLEAN_STALE_PROCESSES}"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  cleanup_stale_processes

  [ -f "${NAV2_PARAMS_FILE}" ] || { print_kv "nav2_params_file" "missing:${NAV2_PARAMS_FILE}"; exit 2; }
  [ -f "${ROUTE_PARAMS_FILE}" ] || { print_kv "route_params_file" "missing:${ROUTE_PARAMS_FILE}"; exit 2; }

  maybe_build_repo
  source_file_checked "${REPO_SETUP}" "repo_setup"
  source_file_checked "${FASTLIO_SETUP}" "fastlio_setup"

  write_fastlio_params
  write_flat_stair_flat_graph_builder
  write_mission_client

  setsid ros2 launch go2w_sim sim_go2w_real.launch.py \
    use_gpu:=false \
    headless:=true \
    launch_rviz:=false \
    world:="${ROUTE_WORLD}" \
    world_name:="${ROUTE_WORLD_NAME}" \
    >"${EVIDENCE_DIR}/sim.log" 2>&1 &
  SIM_PID="$!"

  wait_for_log "ign gazebo" "${EVIDENCE_DIR}/sim.log" 30
  wait_for_controller_states_active "${EVIDENCE_DIR}/controllers.txt" 90
  wait_for_log "go2w_stand_initializer_result: PASS" "${EVIDENCE_DIR}/sim.log" 60

  require_topic_once "required_topic__clock" /clock "${EVIDENCE_DIR}/clock.txt" 15
  require_topic_once "required_topic__imu" /imu "${EVIDENCE_DIR}/imu.txt" 15
  require_topic_once "required_topic__lidar_points" /lidar_points "${EVIDENCE_DIR}/lidar_points.txt" 15
  require_topic_once "required_topic__joint_states" /joint_states "${EVIDENCE_DIR}/joint_states.txt" 15
  require_diff_drive_tf_disabled "${EVIDENCE_DIR}/diff_drive_enable_odom_tf.txt"

  sample_tf_to "pre_perception" 6
  require_tf_edge_absent "pre_perception_odom_base_link" odom base_link "${EVIDENCE_DIR}/tf_pre_perception_all.txt"
  require_tf_edge_absent "pre_perception_map_odom" map odom "${EVIDENCE_DIR}/tf_pre_perception_all.txt"

  setsid ros2 launch go2w_perception phase2f_tf_authority.launch.py >"${EVIDENCE_DIR}/perception.log" 2>&1 &
  PERCEPTION_PID="$!"
  sleep 3
  require_process_alive "${PERCEPTION_PID}" "perception_process_alive" "${EVIDENCE_DIR}/perception.log"
  require_adapted_time_field "${EVIDENCE_DIR}/adapted_lidar_fields.txt"

  setsid ros2 run fast_lio fastlio_mapping --ros-args --params-file "${EVIDENCE_DIR}/mission_real_fsf_fastlio.yaml" >"${EVIDENCE_DIR}/fastlio.log" 2>&1 &
  FASTLIO_PID="$!"
  sleep 8
  require_process_alive "${FASTLIO_PID}" "fastlio_process_alive" "${EVIDENCE_DIR}/fastlio.log"

  require_topic_once "contract_topic__odom" /go2w/perception/odom "${EVIDENCE_DIR}/contract_odom.txt" 20
  require_topic_once "contract_topic__cloud_body" /go2w/perception/cloud_body "${EVIDENCE_DIR}/contract_cloud_body.txt" 20
  require_topic_once "contract_topic__cloud_registered" /go2w/perception/cloud_registered "${EVIDENCE_DIR}/contract_cloud_registered.txt" 20
  require_field_once "contract_cloud_body_frame" /go2w/perception/cloud_body header.frame_id base_link "${EVIDENCE_DIR}/contract_cloud_body_frame.txt" 15

  sample_tf_to "pre_nav2" 8
  require_tf_edge_absent "fastlio_tf_camera_init_body" camera_init body "${EVIDENCE_DIR}/tf_pre_nav2_all.txt"
  require_tf_edge_absent "pre_nav2_map_odom" map odom "${EVIDENCE_DIR}/tf_pre_nav2_all.txt"
  require_tf_edge_present "odom_base_link_authority" odom base_link "${EVIDENCE_DIR}/tf_pre_nav2_all.txt"

  setsid ros2 launch go2w_navigation phase3a_nav2_same_floor.launch.py params_file:="${NAV2_PARAMS_FILE}" >"${EVIDENCE_DIR}/nav2.log" 2>&1 &
  NAV2_PID="$!"
  sleep 8
  require_process_alive "${NAV2_PID}" "nav2_launch_process_alive" "${EVIDENCE_DIR}/nav2.log"

  wait_for_lifecycle_active "controller_server_lifecycle" /controller_server "${EVIDENCE_DIR}/controller_server_lifecycle.txt" 45
  wait_for_lifecycle_active "planner_server_lifecycle" /planner_server "${EVIDENCE_DIR}/planner_server_lifecycle.txt" 45
  wait_for_lifecycle_active "bt_navigator_lifecycle" /bt_navigator "${EVIDENCE_DIR}/bt_navigator_lifecycle.txt" 45
  wait_for_action "/navigate_to_pose" 45
  require_param_contains "controller_odom_topic" /controller_server odom_topic /go2w/perception/odom "${EVIDENCE_DIR}/controller_odom_topic.txt"
  require_param_contains "bt_navigator_global_frame" /bt_navigator global_frame odom "${EVIDENCE_DIR}/bt_navigator_global_frame.txt"
  require_param_contains "bt_navigator_robot_base_frame" /bt_navigator robot_base_frame base_link "${EVIDENCE_DIR}/bt_navigator_robot_base_frame.txt"
  require_topic_once "local_costmap_topic_once" /local_costmap/costmap "${EVIDENCE_DIR}/local_costmap.txt" 20
  require_topic_once "global_costmap_topic_once" /global_costmap/costmap "${EVIDENCE_DIR}/global_costmap.txt" 20
  require_field_once "local_costmap_frame" /local_costmap/costmap header.frame_id odom "${EVIDENCE_DIR}/local_costmap_frame.txt" 15

  local graph_file="${EVIDENCE_DIR}/mission_real_flat_stair_flat_route.geojson"
  export GO2W_MISSION_REAL_FSF_GRAPH_FILE="${graph_file}"
  export GO2W_MISSION_REAL_FSF_FIRST_FLAT_OFFSET_X="${FIRST_FLAT_OFFSET_X}"
  export GO2W_MISSION_REAL_FSF_STAIR_HANDOFF_OFFSET_X="${STAIR_HANDOFF_OFFSET_X}"
  export GO2W_MISSION_REAL_FSF_SECOND_FLAT_OFFSET_X="${SECOND_FLAT_OFFSET_X}"
  python3 "${EVIDENCE_DIR}/build_mission_flat_stair_flat_graph.py" >"${EVIDENCE_DIR}/flat_stair_flat_graph_initial.txt" 2>&1
  grep -E '^mission_real_flat_stair_flat_graph_' "${EVIDENCE_DIR}/flat_stair_flat_graph_initial.txt" || true
  if ! grep -q "mission_real_flat_stair_flat_graph_result: PASS" "${EVIDENCE_DIR}/flat_stair_flat_graph_initial.txt"; then
    print_kv "mission_real_flat_stair_flat_graph_result" "FAIL"
    sed -n '1,220p' "${EVIDENCE_DIR}/flat_stair_flat_graph_initial.txt" || true
    exit 2
  fi

  python3 -m json.tool "${graph_file}" >"${EVIDENCE_DIR}/flat_stair_flat_graph_json_parse.txt"
  print_kv "mission_real_flat_stair_flat_graph_json_parse" "PASS"

  setsid ros2 launch go2w_mission mission_api.launch.py \
    use_sim_time:=false \
    route_params_file:="${ROUTE_PARAMS_FILE}" \
    graph_file:="${graph_file}" \
    launch_flat_nav_executor:=false \
    launch_stair_executor:=true \
    flat_behavior_tree:=__empty__ \
    route_tracking_action:=/compute_and_track_route \
    mission_state_file:="${MISSION_STATE_FILE}" \
    mission_retry_limit:=0 \
    log_level:=info \
    >"${EVIDENCE_DIR}/mission_api.log" 2>&1 &
  MISSION_PID="$!"

  wait_for_node "/route_server" 60 "${EVIDENCE_DIR}/mission_api.log"
  wait_for_node "/go2w_command_gate" 60 "${EVIDENCE_DIR}/mission_api.log"
  wait_for_node "/go2w_stair_executor" 60 "${EVIDENCE_DIR}/mission_api.log"
  wait_for_node "/go2w_mission_api" 60 "${EVIDENCE_DIR}/mission_api.log"
  require_node_absent "/go2w_flat_nav_executor" "${EVIDENCE_DIR}/node_list_no_fake_flat_executor.txt"
  wait_for_lifecycle_active "route_server_lifecycle" /route_server "${EVIDENCE_DIR}/route_server_lifecycle.txt" 60
  wait_for_action "/compute_route" 60
  wait_for_action "/compute_and_track_route" 60
  wait_for_action "/go2w/mission/run" 60
  wait_for_action "/navigate_to_pose" 5
  wait_for_action "/stair_exec" 30

  python3 "${EVIDENCE_DIR}/build_mission_flat_stair_flat_graph.py" >"${EVIDENCE_DIR}/flat_stair_flat_graph_reloaded.txt" 2>&1
  grep -E '^mission_real_flat_stair_flat_graph_' "${EVIDENCE_DIR}/flat_stair_flat_graph_reloaded.txt" || true
  if ! grep -q "mission_real_flat_stair_flat_graph_result: PASS" "${EVIDENCE_DIR}/flat_stair_flat_graph_reloaded.txt"; then
    print_kv "mission_real_flat_stair_flat_graph_reload_result" "FAIL"
    sed -n '1,220p' "${EVIDENCE_DIR}/flat_stair_flat_graph_reloaded.txt" || true
    exit 2
  fi
  python3 -m json.tool "${graph_file}" >"${EVIDENCE_DIR}/flat_stair_flat_graph_reloaded_json_parse.txt"
  print_kv "mission_real_flat_stair_flat_graph_reload_json_parse" "PASS"
  require_route_graph_reload "${graph_file}"

  export GO2W_MISSION_REAL_FSF_NAV_TIMEOUT_SECONDS="${NAV_TIMEOUT_SECONDS}"
  export GO2W_MISSION_REAL_FSF_STAIR_TIMEOUT_SECONDS="${STAIR_TIMEOUT_SECONDS}"
  export GO2W_MISSION_REAL_FSF_STAIR_EXPECTED_SECONDS="${STAIR_EXPECTED_SECONDS}"
  export GO2W_MISSION_REAL_FSF_MIN_PERCEPTION_ODOM_DELTA="${MIN_PERCEPTION_ODOM_DELTA}"
  export GO2W_MISSION_REAL_FSF_MIN_DIFF_DRIVE_ODOM_DELTA="${MIN_DIFF_DRIVE_ODOM_DELTA}"
  set +e
  python3 "${EVIDENCE_DIR}/mission_real_flat_stair_flat_client.py" >"${EVIDENCE_DIR}/mission_goal.txt" 2>&1
  local mission_client_status="$?"
  set -e
  grep -E '^mission_real_flat_stair_flat_' "${EVIDENCE_DIR}/mission_goal.txt" || true
  grep -E 'mission_route_tracking_' "${EVIDENCE_DIR}/mission_api.log" || true
  if [ "${mission_client_status}" -ne 0 ] \
    || ! grep -q "mission_real_flat_stair_flat_result: PASS" "${EVIDENCE_DIR}/mission_goal.txt"; then
    print_kv "mission_real_flat_stair_flat_result" "FAIL"
    sed -n '1,320p' "${EVIDENCE_DIR}/mission_goal.txt" || true
    exit 2
  fi
  if ! grep -q "mission_real_flat_stair_flat_segment_summary: flat:10;stair:500:stair_a:F1->F2;flat:20" "${EVIDENCE_DIR}/mission_goal.txt"; then
    print_kv "mission_real_flat_stair_flat_segment_summary" "FAIL"
    sed -n '1,320p' "${EVIDENCE_DIR}/mission_goal.txt" || true
    exit 2
  fi
  if ! grep -q "mission_route_tracking_feedback_edge: 10" "${EVIDENCE_DIR}/mission_api.log" \
    || ! grep -q "mission_route_tracking_feedback_edge: 20" "${EVIDENCE_DIR}/mission_api.log" \
    || ! grep -q "mission_route_tracking_result: PASS" "${EVIDENCE_DIR}/mission_api.log"; then
    print_kv "mission_route_tracking_result" "FAIL"
    sed -n '1,320p' "${EVIDENCE_DIR}/mission_api.log" || true
    exit 2
  fi
  print_kv "mission_route_tracking_result" "PASS"

  wait_for_text_count "go2w_command_gate_state: owner=flat mode=wheeled" "${EVIDENCE_DIR}/mission_api.log" 2 5
  wait_for_text "go2w_command_gate_state: owner=stair mode=legged" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_plan: phases=prepare,wheel_lock,body_height_transition_down,execute_stairs,body_height_transition_up,release" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=prepare" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=wheel_lock" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=body_height_transition_down" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=execute_stairs" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=body_height_transition_up" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=release" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=wheel_lock .*wheel_lock_required=true" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=execute_stairs .*wheel_lock_required=true" "${EVIDENCE_DIR}/mission_api.log" 5
  wait_for_text "go2w_stair_executor_state: phase=release .*wheel_lock_required=false" "${EVIDENCE_DIR}/mission_api.log" 5

  require_log_absent "sim_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/sim.log"
  require_log_absent "perception_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/perception.log"
  require_log_absent "fastlio_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/fastlio.log"
  require_log_absent "nav2_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/nav2.log"
  require_log_absent "mission_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/mission_api.log"

  sample_tf_to "post_mission" 8
  require_tf_edge_absent "post_mission_fastlio_tf_camera_init_body" camera_init body "${EVIDENCE_DIR}/tf_post_mission_all.txt"
  require_tf_edge_absent "post_mission_map_odom" map odom "${EVIDENCE_DIR}/tf_post_mission_all.txt"
  require_tf_edge_present "post_mission_odom_base_link_authority" odom base_link "${EVIDENCE_DIR}/tf_post_mission_all.txt"

  print_kv "sim_log" "${EVIDENCE_DIR}/sim.log"
  print_kv "perception_log" "${EVIDENCE_DIR}/perception.log"
  print_kv "fastlio_log" "${EVIDENCE_DIR}/fastlio.log"
  print_kv "nav2_log" "${EVIDENCE_DIR}/nav2.log"
  print_kv "mission_api_log" "${EVIDENCE_DIR}/mission_api.log"
  print_kv "mission_goal_log" "${EVIDENCE_DIR}/mission_goal.txt"
  print_kv "go2w_mission_real_flat_stair_flat_result" "PASS"
}

main "$@"
