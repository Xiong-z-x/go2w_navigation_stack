#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_WS="${GO2W_FASTLIO_WS:-/tmp/go2w_phase2d_fastlio_ws}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
FASTLIO_SETUP="${FASTLIO_WS}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE3A_EVIDENCE_DIR:-/tmp/go2w_phase3a_nav2_same_floor_${$}}"
PHASE3A_WORLD="${GO2W_PHASE3A_WORLD:-${REPO_ROOT}/install/go2w_sim/share/go2w_sim/worlds/phase3a_feature_world.sdf}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 80 ))}"
PARTITION="go2w_phase3a_${$}"
REBUILD_REPO="${GO2W_PHASE3A_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_PHASE3A_CLEAN_EVIDENCE:-0}"
HZ_WINDOW_SECONDS="${GO2W_PHASE3A_HZ_WINDOW_SECONDS:-15}"
NAV_TIMEOUT_SECONDS="${GO2W_PHASE3A_NAV_TIMEOUT_SECONDS:-90}"
NAV_GOAL_OFFSET_X="${GO2W_PHASE3A_NAV_GOAL_OFFSET_X:-0.035}"
NAV_GOAL_OFFSET_Y="${GO2W_PHASE3A_NAV_GOAL_OFFSET_Y:-0.020}"
NAV_GOAL_YAW_OFFSET="${GO2W_PHASE3A_NAV_GOAL_YAW_OFFSET:-0.0}"
MIN_ODOM_DELTA="${GO2W_PHASE3A_MIN_ODOM_DELTA:-0.003}"
FASTLIO_PID=""
PERCEPTION_PID=""
SIM_PID=""
NAV2_PID=""
local_costmap_hz_pid=""
global_costmap_hz_pid=""
cloud_body_hz_pid=""
odom_hz_pid=""

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
  terminate_pid "${NAV2_PID}" "nav2"
  terminate_pid "${FASTLIO_PID}" "fastlio"
  pkill -INT -f "${FASTLIO_WS}/install/fast_lio/lib/fast_lio/fastlio_mapping" 2>/dev/null || true
  terminate_pid "${PERCEPTION_PID}" "perception"
  terminate_pid "${SIM_PID}" "sim"
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
        go2w_navigation go2w_perception go2w_description go2w_sim
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
    if [ -n "${SIM_PID}" ] && ! kill -0 "${SIM_PID}" 2>/dev/null; then
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

require_process_alive() {
  local pid="$1"
  local key="$2"
  local log_file="$3"
  if [ -z "${pid}" ] || ! kill -0 "${pid}" 2>/dev/null; then
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

require_node_subscription() {
  local key="$1"
  local node="$2"
  local topic="$3"
  local output_file="$4"
  if ! timeout 10s ros2 node info "${node}" >"${output_file}" 2>&1; then
    print_kv "${key}" "FAIL_NODE_INFO"
    sed -n '1,220p' "${output_file}" || true
    exit 2
  fi
  if grep -q "${topic}" "${output_file}"; then
    print_kv "${key}" "PASS"
    return
  fi
  print_kv "${key}" "FAIL"
  sed -n '1,260p' "${output_file}" || true
  exit 2
}

require_action_server() {
  local output_file="$1"
  if ! timeout 10s ros2 action list >"${output_file}" 2>&1; then
    print_kv "navigate_to_pose_action" "FAIL_LIST"
    sed -n '1,160p' "${output_file}" || true
    exit 2
  fi
  if grep -qx "/navigate_to_pose" "${output_file}"; then
    print_kv "navigate_to_pose_action" "AVAILABLE"
    return
  fi
  print_kv "navigate_to_pose_action" "MISSING"
  sed -n '1,160p' "${output_file}" || true
  exit 2
}

start_hz_capture() {
  local pid_var="$1"
  local topic="$2"
  local output_file="$3"
  local duration_seconds="$4"
  timeout --signal=INT "${duration_seconds}s" ros2 topic hz "${topic}" >"${output_file}" 2>&1 &
  printf -v "${pid_var}" '%s' "$!"
}

require_hz_capture() {
  local key="$1"
  local output_file="$2"
  local pid="$3"
  local min_rate="$4"
  local average_rate
  wait "${pid}" 2>/dev/null || true
  average_rate="$(awk '/average rate:/ { value=$3 } END { print value }' "${output_file}")"
  if [ -z "${average_rate}" ]; then
    print_kv "${key}" "FAIL_NO_RATE"
    sed -n '1,180p' "${output_file}" || true
    exit 2
  fi
  if awk -v rate="${average_rate}" -v min="${min_rate}" 'BEGIN { exit(rate >= min ? 0 : 1) }'; then
    print_kv "${key}" "${average_rate}"
    return
  fi
  print_kv "${key}" "FAIL:${average_rate}<${min_rate}"
  sed -n '1,180p' "${output_file}" || true
  exit 2
}

require_no_forbidden_nodes() {
  local output_file="$1"
  timeout 10s ros2 node list >"${output_file}" 2>&1 || true
  if grep -Eq '(^|/)(amcl|map_server|route_server|waypoint_follower|behavior_server|smoother_server|velocity_smoother|go2w_mission|stair_exec|elevation|traversability)($|_)' "${output_file}"; then
    print_kv "forbidden_phase3a_extra_nodes" "PRESENT"
    sed -n '1,220p' "${output_file}" || true
    exit 2
  fi
  print_kv "forbidden_phase3a_extra_nodes" "ABSENT"
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
  cat >"${EVIDENCE_DIR}/phase3a_fastlio.yaml" <<'EOF'
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

write_nav_goal_client() {
  cat >"${EVIDENCE_DIR}/phase3a_nav_goal_client.py" <<'PYEOF'
#!/usr/bin/env python3
import math
import os
import sys
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from nav2_msgs.action import NavigateToPose
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


def quat_to_yaw(q) -> float:
    siny_cosp = 2.0 * (float(q.w) * float(q.z) + float(q.x) * float(q.y))
    cosy_cosp = 1.0 - 2.0 * (float(q.y) * float(q.y) + float(q.z) * float(q.z))
    return math.atan2(siny_cosp, cosy_cosp)


def yaw_to_quat(yaw: float):
    from geometry_msgs.msg import Quaternion

    q = Quaternion()
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


def normalize_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class Phase3ANavGoalClient(Node):
    def __init__(self) -> None:
        super().__init__("phase3a_nav_goal_client")
        self._action_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self._latest_odom = None
        self._start_odom = None
        self._latest_diff_drive_odom = None
        self._start_diff_drive_odom = None
        self._cmd_vel_count = 0
        self._max_linear_x = 0.0
        self._max_angular_z = 0.0
        self.create_subscription(Odometry, "/go2w/perception/odom", self._odom_cb, 10)
        self.create_subscription(Odometry, "/diff_drive_controller/odom", self._diff_drive_odom_cb, 10)
        self.create_subscription(Twist, "/cmd_vel", self._cmd_vel_cb, 10)

    def _odom_cb(self, msg: Odometry) -> None:
        self._latest_odom = msg
        if self._start_odom is None:
            self._start_odom = msg

    def _diff_drive_odom_cb(self, msg: Odometry) -> None:
        self._latest_diff_drive_odom = msg
        if self._start_diff_drive_odom is None:
            self._start_diff_drive_odom = msg

    def _cmd_vel_cb(self, msg) -> None:
        linear_x = float(msg.linear.x)
        angular_z = float(msg.angular.z)
        if abs(linear_x) > 1.0e-4 or abs(angular_z) > 1.0e-4:
            self._cmd_vel_count += 1
        self._max_linear_x = max(self._max_linear_x, abs(linear_x))
        self._max_angular_z = max(self._max_angular_z, abs(angular_z))

    def wait_for_odom(self, timeout_sec: float) -> bool:
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and self._start_odom is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        return self._start_odom is not None

    def send_goal_and_wait(self, offset_x: float, offset_y: float, yaw_offset: float, timeout_sec: float) -> int:
        if not self.wait_for_odom(20.0):
            print("phase3a_nav_goal_error: no_start_odom")
            return 2

        if not self._action_client.wait_for_server(timeout_sec=30.0):
            print("phase3a_nav_goal_error: no_action_server")
            return 2

        start_pose = self._start_odom.pose.pose
        start_yaw = quat_to_yaw(start_pose.orientation)
        target_yaw = normalize_angle(start_yaw + yaw_offset)
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "odom"
        goal.pose.pose.position.x = float(start_pose.position.x) + offset_x
        goal.pose.pose.position.y = float(start_pose.position.y) + offset_y
        goal.pose.pose.position.z = 0.0
        goal.pose.pose.orientation = yaw_to_quat(target_yaw)

        print(f"phase3a_goal_start_x: {start_pose.position.x:.6f}")
        print(f"phase3a_goal_start_y: {start_pose.position.y:.6f}")
        print(f"phase3a_goal_start_yaw: {start_yaw:.6f}")
        print(f"phase3a_goal_target_x: {goal.pose.pose.position.x:.6f}")
        print(f"phase3a_goal_target_y: {goal.pose.pose.position.y:.6f}")
        print(f"phase3a_goal_target_yaw: {target_yaw:.6f}")

        send_future = self._action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print("phase3a_nav_goal_error: goal_rejected")
            return 2

        result_future = goal_handle.get_result_async()
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and not result_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

        if not result_future.done():
            print("phase3a_nav_goal_error: result_timeout")
            cancel_future = goal_handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, cancel_future, timeout_sec=5.0)
            return 2

        result = result_future.result()
        status_name = STATUS_NAMES.get(result.status, str(result.status))
        print(f"phase3a_goal_status: {status_name}")

        # Let one final odometry sample arrive after the action result.
        for _ in range(10):
            rclpy.spin_once(self, timeout_sec=0.1)

        final_pose = self._latest_odom.pose.pose
        final_yaw = quat_to_yaw(final_pose.orientation)
        dx = float(final_pose.position.x) - float(start_pose.position.x)
        dy = float(final_pose.position.y) - float(start_pose.position.y)
        delta_xy = math.hypot(dx, dy)
        delta_yaw = normalize_angle(final_yaw - start_yaw)
        min_delta = float(os.environ.get("PHASE3A_MIN_ODOM_DELTA", "0.10"))

        print(f"phase3a_goal_final_x: {final_pose.position.x:.6f}")
        print(f"phase3a_goal_final_y: {final_pose.position.y:.6f}")
        print(f"phase3a_goal_final_yaw: {final_yaw:.6f}")
        print(f"phase3a_odom_delta_x: {dx:.6f}")
        print(f"phase3a_odom_delta_y: {dy:.6f}")
        print(f"phase3a_odom_delta_xy: {delta_xy:.6f}")
        print(f"phase3a_odom_delta_yaw: {delta_yaw:.6f}")
        print(f"phase3a_cmd_vel_nonzero_count: {self._cmd_vel_count}")
        print(f"phase3a_cmd_vel_max_linear_x: {self._max_linear_x:.6f}")
        print(f"phase3a_cmd_vel_max_angular_z: {self._max_angular_z:.6f}")

        if self._start_diff_drive_odom is not None and self._latest_diff_drive_odom is not None:
            diff_start = self._start_diff_drive_odom.pose.pose
            diff_final = self._latest_diff_drive_odom.pose.pose
            diff_dx = float(diff_final.position.x) - float(diff_start.position.x)
            diff_dy = float(diff_final.position.y) - float(diff_start.position.y)
            diff_delta_xy = math.hypot(diff_dx, diff_dy)
            diff_delta_yaw = normalize_angle(
                quat_to_yaw(diff_final.orientation) - quat_to_yaw(diff_start.orientation)
            )
            print(f"phase3a_diff_drive_delta_x: {diff_dx:.6f}")
            print(f"phase3a_diff_drive_delta_y: {diff_dy:.6f}")
            print(f"phase3a_diff_drive_delta_xy: {diff_delta_xy:.6f}")
            print(f"phase3a_diff_drive_delta_yaw: {diff_delta_yaw:.6f}")

        if result.status != GoalStatus.STATUS_SUCCEEDED:
            print("phase3a_nav_goal_result: FAIL_STATUS")
            return 2
        if self._cmd_vel_count < 2:
            print("phase3a_nav_goal_result: FAIL_NO_CMD_VEL")
            return 2
        if delta_xy < min_delta:
            print("phase3a_nav_goal_result: FAIL_NO_ODOM_MOTION")
            return 2

        print("phase3a_nav_goal_result: PASS")
        return 0


def main() -> int:
    rclpy.init()
    node = Phase3ANavGoalClient()
    try:
        offset_x = float(os.environ.get("PHASE3A_GOAL_OFFSET_X", "0.035"))
        offset_y = float(os.environ.get("PHASE3A_GOAL_OFFSET_Y", "0.0"))
        yaw_offset = float(os.environ.get("PHASE3A_GOAL_YAW_OFFSET", "0.0"))
        timeout_sec = float(os.environ.get("PHASE3A_NAV_TIMEOUT_SECONDS", "90"))
        return node.send_goal_and_wait(offset_x, offset_y, yaw_offset, timeout_sec)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
PYEOF
  chmod +x "${EVIDENCE_DIR}/phase3a_nav_goal_client.py"
}

run_nav_goal() {
  local output_file="$1"
  if ! PHASE3A_GOAL_OFFSET_X="${NAV_GOAL_OFFSET_X}" \
    PHASE3A_GOAL_OFFSET_Y="${NAV_GOAL_OFFSET_Y}" \
    PHASE3A_GOAL_YAW_OFFSET="${NAV_GOAL_YAW_OFFSET}" \
    PHASE3A_NAV_TIMEOUT_SECONDS="${NAV_TIMEOUT_SECONDS}" \
    PHASE3A_MIN_ODOM_DELTA="${MIN_ODOM_DELTA}" \
    python3 "${EVIDENCE_DIR}/phase3a_nav_goal_client.py" >"${output_file}" 2>&1; then
    print_kv "navigate_to_pose_goal" "FAIL"
    sed -n '1,260p' "${output_file}" || true
    exit 2
  fi
  grep -E '^phase3a_' "${output_file}" || true
  print_kv "navigate_to_pose_goal" "PASS"
}

printf '# Phase 3A Nav2 Same-Floor Verification\n'
print_kv "repo_root" "${REPO_ROOT}"
print_kv "fastlio_workspace_path" "${FASTLIO_WS}"
print_kv "ros_domain_id" "${DOMAIN_ID}"
print_kv "gz_partition" "${PARTITION}"
print_kv "phase3a_world" "${PHASE3A_WORLD}"
print_kv "hz_window_seconds" "${HZ_WINDOW_SECONDS}"
print_kv "nav_timeout_seconds" "${NAV_TIMEOUT_SECONDS}"
print_kv "nav_goal_offset_x" "${NAV_GOAL_OFFSET_X}"
print_kv "nav_goal_offset_y" "${NAV_GOAL_OFFSET_Y}"
print_kv "nav_goal_yaw_offset" "${NAV_GOAL_YAW_OFFSET}"
print_kv "evidence_dir" "${EVIDENCE_DIR}"
mkdir -p "${EVIDENCE_DIR}"

"${REPO_ROOT}/tools/prepare_phase2d_fastlio_external.sh"
maybe_build_repo

source_file_checked "${ROS_SETUP}" "ros_setup"
source_file_checked "${REPO_SETUP}" "repo_setup"
source_file_checked "${FASTLIO_SETUP}" "fastlio_setup"

if [ ! -f "${PHASE3A_WORLD}" ]; then
  print_kv "phase3a_world_present" "missing:${PHASE3A_WORLD}"
  exit 2
fi
print_kv "phase3a_world_present" "PASS"

"${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true

export ROS_DOMAIN_ID="${DOMAIN_ID}"
export GZ_PARTITION="${PARTITION}"

write_fastlio_params
write_nav_goal_client

ros2 launch go2w_sim sim.launch.py use_gpu:=false headless:=true launch_rviz:=false world:="${PHASE3A_WORLD}" world_name:=go2w_phase3a_feature_world >"${EVIDENCE_DIR}/sim.log" 2>&1 &
SIM_PID="$!"

wait_for_log "ign gazebo-6" "${EVIDENCE_DIR}/sim.log" 25
wait_for_log "Configured and activated .*joint_state_broadcaster" "${EVIDENCE_DIR}/sim.log" 35
wait_for_log "Configured and activated .*diff_drive_controller" "${EVIDENCE_DIR}/sim.log" 35

require_topic_once "required_topic__clock" /clock "${EVIDENCE_DIR}/clock.txt" 15
require_topic_once "required_topic__imu" /imu "${EVIDENCE_DIR}/imu.txt" 15
require_topic_once "required_topic__lidar_points" /lidar_points "${EVIDENCE_DIR}/lidar_points.txt" 15
require_diff_drive_tf_disabled "${EVIDENCE_DIR}/diff_drive_enable_odom_tf.txt"

sample_tf_to "pre_activation" 6
require_tf_edge_absent "pre_activation_odom_base_link" odom base_link "${EVIDENCE_DIR}/tf_pre_activation_all.txt"
require_tf_edge_absent "pre_activation_map_odom" map odom "${EVIDENCE_DIR}/tf_pre_activation_all.txt"

ros2 launch go2w_perception phase2f_tf_authority.launch.py >"${EVIDENCE_DIR}/perception.log" 2>&1 &
PERCEPTION_PID="$!"
sleep 3
require_process_alive "${PERCEPTION_PID}" "perception_process_alive" "${EVIDENCE_DIR}/perception.log"
require_adapted_time_field "${EVIDENCE_DIR}/adapted_lidar_fields.txt"

ros2 run fast_lio fastlio_mapping --ros-args --params-file "${EVIDENCE_DIR}/phase3a_fastlio.yaml" >"${EVIDENCE_DIR}/fastlio.log" 2>&1 &
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

ros2 launch go2w_navigation phase3a_nav2_same_floor.launch.py >"${EVIDENCE_DIR}/nav2.log" 2>&1 &
NAV2_PID="$!"
sleep 8
require_process_alive "${NAV2_PID}" "nav2_launch_process_alive" "${EVIDENCE_DIR}/nav2.log"

wait_for_lifecycle_active "controller_server_lifecycle" /controller_server "${EVIDENCE_DIR}/controller_server_lifecycle.txt" 45
wait_for_lifecycle_active "planner_server_lifecycle" /planner_server "${EVIDENCE_DIR}/planner_server_lifecycle.txt" 45
wait_for_lifecycle_active "bt_navigator_lifecycle" /bt_navigator "${EVIDENCE_DIR}/bt_navigator_lifecycle.txt" 45

require_action_server "${EVIDENCE_DIR}/action_list.txt"
require_param_contains "controller_odom_topic" /controller_server odom_topic /go2w/perception/odom "${EVIDENCE_DIR}/controller_odom_topic.txt"
require_param_contains "local_costmap_global_frame" /local_costmap/local_costmap global_frame odom "${EVIDENCE_DIR}/local_costmap_global_frame.txt"
require_param_contains "local_costmap_robot_base_frame" /local_costmap/local_costmap robot_base_frame base_link "${EVIDENCE_DIR}/local_costmap_robot_base_frame.txt"
require_param_contains "local_costmap_observation_topic" /local_costmap/local_costmap voxel_layer.perception_cloud.topic /go2w/perception/cloud_body "${EVIDENCE_DIR}/local_costmap_observation_topic.txt"
require_param_contains "global_costmap_global_frame" /global_costmap/global_costmap global_frame odom "${EVIDENCE_DIR}/global_costmap_global_frame.txt"
require_param_contains "global_costmap_robot_base_frame" /global_costmap/global_costmap robot_base_frame base_link "${EVIDENCE_DIR}/global_costmap_robot_base_frame.txt"
require_param_contains "global_costmap_observation_topic" /global_costmap/global_costmap voxel_layer.perception_cloud.topic /go2w/perception/cloud_body "${EVIDENCE_DIR}/global_costmap_observation_topic.txt"

require_node_subscription "local_costmap_cloud_subscription" /local_costmap/local_costmap /go2w/perception/cloud_body "${EVIDENCE_DIR}/local_costmap_node_info.txt"
require_node_subscription "global_costmap_cloud_subscription" /global_costmap/global_costmap /go2w/perception/cloud_body "${EVIDENCE_DIR}/global_costmap_node_info.txt"
require_topic_once "local_costmap_topic_once" /local_costmap/costmap "${EVIDENCE_DIR}/local_costmap.txt" 20
require_topic_once "global_costmap_topic_once" /global_costmap/costmap "${EVIDENCE_DIR}/global_costmap.txt" 20
require_field_once "local_costmap_frame" /local_costmap/costmap header.frame_id odom "${EVIDENCE_DIR}/local_costmap_frame.txt" 15
require_field_once "global_costmap_frame" /global_costmap/costmap header.frame_id odom "${EVIDENCE_DIR}/global_costmap_frame.txt" 15
require_no_forbidden_nodes "${EVIDENCE_DIR}/node_list_pre_goal.txt"

start_hz_capture local_costmap_hz_pid /local_costmap/costmap "${EVIDENCE_DIR}/hz_local_costmap.txt" "${HZ_WINDOW_SECONDS}"
start_hz_capture global_costmap_hz_pid /global_costmap/costmap "${EVIDENCE_DIR}/hz_global_costmap.txt" "${HZ_WINDOW_SECONDS}"
start_hz_capture cloud_body_hz_pid /go2w/perception/cloud_body "${EVIDENCE_DIR}/hz_cloud_body.txt" "${HZ_WINDOW_SECONDS}"
start_hz_capture odom_hz_pid /go2w/perception/odom "${EVIDENCE_DIR}/hz_odom.txt" "${HZ_WINDOW_SECONDS}"

run_nav_goal "${EVIDENCE_DIR}/nav_goal.txt"

require_hz_capture "local_costmap_average_rate" "${EVIDENCE_DIR}/hz_local_costmap.txt" "${local_costmap_hz_pid}" 0.5
require_hz_capture "global_costmap_average_rate" "${EVIDENCE_DIR}/hz_global_costmap.txt" "${global_costmap_hz_pid}" 0.2
require_hz_capture "cloud_body_average_rate" "${EVIDENCE_DIR}/hz_cloud_body.txt" "${cloud_body_hz_pid}" 1.0
require_hz_capture "odom_average_rate" "${EVIDENCE_DIR}/hz_odom.txt" "${odom_hz_pid}" 1.0

require_process_alive "${SIM_PID}" "sim_process_alive_after_goal" "${EVIDENCE_DIR}/sim.log"
require_process_alive "${PERCEPTION_PID}" "perception_process_alive_after_goal" "${EVIDENCE_DIR}/perception.log"
require_process_alive "${FASTLIO_PID}" "fastlio_process_alive_after_goal" "${EVIDENCE_DIR}/fastlio.log"
require_process_alive "${NAV2_PID}" "nav2_process_alive_after_goal" "${EVIDENCE_DIR}/nav2.log"
require_no_forbidden_nodes "${EVIDENCE_DIR}/node_list_after_goal.txt"

missing_time_warning_count="$(grep -c "Failed to find match for field 'time'" "${EVIDENCE_DIR}/fastlio.log" || true)"
print_kv "fastlio_missing_time_warning_count" "${missing_time_warning_count}"
if [ "${missing_time_warning_count}" != "0" ]; then
  exit 2
fi

require_log_absent "perception_contract_error_count" "contract adaptation failed|pointcloud timing adaptation failed|TF authority rejected odometry|Traceback" "${EVIDENCE_DIR}/perception.log"
require_log_absent "fastlio_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback" "${EVIDENCE_DIR}/fastlio.log"
require_log_absent "nav2_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/nav2.log"

sample_tf_to "post_nav2" 8
require_tf_edge_absent "post_nav2_fastlio_tf_camera_init_body" camera_init body "${EVIDENCE_DIR}/tf_post_nav2_all.txt"
require_tf_edge_absent "post_nav2_map_odom" map odom "${EVIDENCE_DIR}/tf_post_nav2_all.txt"
require_tf_edge_present "post_nav2_odom_base_link_authority" odom base_link "${EVIDENCE_DIR}/tf_post_nav2_all.txt"

print_kv "sim_log" "${EVIDENCE_DIR}/sim.log"
print_kv "perception_log" "${EVIDENCE_DIR}/perception.log"
print_kv "fastlio_log" "${EVIDENCE_DIR}/fastlio.log"
print_kv "nav2_log" "${EVIDENCE_DIR}/nav2.log"
print_kv "nav_goal_log" "${EVIDENCE_DIR}/nav_goal.txt"
print_kv "local_costmap_node_info" "${EVIDENCE_DIR}/local_costmap_node_info.txt"
print_kv "global_costmap_node_info" "${EVIDENCE_DIR}/global_costmap_node_info.txt"
print_kv "tf_post_nav2_sample" "${EVIDENCE_DIR}/tf_post_nav2_all.txt"
print_kv "phase3a_result" "PASS"
