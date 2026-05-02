#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_CACHE_ROOT="${GO2W_FASTLIO_CACHE_ROOT:-${REPO_ROOT}/.go2w_external}"
FASTLIO_WS="${GO2W_FASTLIO_WS:-${FASTLIO_CACHE_ROOT}/workspaces/fast_lio_ros2}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
FASTLIO_SETUP="${FASTLIO_WS}/install/setup.bash"
EVIDENCE_DIR="${GO2W_REAL_ROUTE_EVIDENCE_DIR:-/tmp/go2w_real_model_route_following_${$}}"
ROUTE_WORLD="${GO2W_REAL_ROUTE_WORLD:-${REPO_ROOT}/install/go2w_sim/share/go2w_sim/worlds/phase3a_feature_world.sdf}"
ROUTE_WORLD_NAME="${GO2W_REAL_ROUTE_WORLD_NAME:-go2w_phase3a_feature_world}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 90) + 130 ))}"
PARTITION="go2w_real_route_${$}"
REBUILD_REPO="${GO2W_REAL_ROUTE_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_REAL_ROUTE_CLEAN_EVIDENCE:-0}"
NAV_TIMEOUT_SECONDS="${GO2W_REAL_ROUTE_NAV_TIMEOUT_SECONDS:-120}"
NAV_GOAL_OFFSET_X="${GO2W_REAL_ROUTE_GOAL_OFFSET_X:-0.150}"
NAV_GOAL_OFFSET_Y="${GO2W_REAL_ROUTE_GOAL_OFFSET_Y:-0.000}"
NAV_GOAL_YAW_OFFSET="${GO2W_REAL_ROUTE_GOAL_YAW_OFFSET:-0.0}"
MIN_PERCEPTION_ODOM_DELTA="${GO2W_REAL_ROUTE_MIN_PERCEPTION_ODOM_DELTA:-0.003}"
MIN_DIFF_DRIVE_ODOM_DELTA="${GO2W_REAL_ROUTE_MIN_DIFF_DRIVE_ODOM_DELTA:-0.003}"
NAV2_PARAMS_FILE="${GO2W_REAL_ROUTE_NAV2_PARAMS_FILE:-${REPO_ROOT}/go2w_navigation/config/phase5_real_model_nav2_same_floor.yaml}"
FASTLIO_PID=""
PERCEPTION_PID=""
SIM_PID=""
NAV2_PID=""

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
        go2w_navigation go2w_perception go2w_description go2w_sim go2w_control
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

require_no_forbidden_nodes() {
  local output_file="$1"
  timeout 10s ros2 node list >"${output_file}" 2>&1 || true
  if grep -Eq '(^|/)(amcl|map_server|route_server|waypoint_follower|behavior_server|smoother_server|velocity_smoother|go2w_mission|stair_exec|elevation|traversability)($|_)' "${output_file}"; then
    print_kv "forbidden_extra_nodes" "PRESENT"
    sed -n '1,220p' "${output_file}" || true
    exit 2
  fi
  print_kv "forbidden_extra_nodes" "ABSENT"
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
  cat >"${EVIDENCE_DIR}/real_route_fastlio.yaml" <<'EOF'
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
  cat >"${EVIDENCE_DIR}/real_route_goal_client.py" <<'PYEOF'
#!/usr/bin/env python3
import math
import os
import sys
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from nav2_msgs.action import ComputePathToPose, NavigateToPose
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


class RealRouteGoalClient(Node):
    def __init__(self) -> None:
        super().__init__("real_route_goal_client")
        self._path_client = ActionClient(self, ComputePathToPose, "compute_path_to_pose")
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
        settle_seconds = 5.0
        settle_deadline = None
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self._latest_odom is None or self._latest_diff_drive_odom is None:
                continue
            if settle_deadline is None:
                settle_deadline = time.monotonic() + settle_seconds
                continue
            if time.monotonic() < settle_deadline:
                continue
            self._start_odom = self._latest_odom
            self._start_diff_drive_odom = self._latest_diff_drive_odom
            return True
        return False

    def build_goal_pose(self, start_pose, start_yaw: float, offset_x: float, offset_y: float, yaw_offset: float):
        from geometry_msgs.msg import PoseStamped

        target_yaw = normalize_angle(start_yaw + yaw_offset)
        pose = PoseStamped()
        pose.header.frame_id = "odom"
        pose.header.stamp = self.get_clock().now().to_msg()
        # Keep the target short, but project it from the current heading frame
        # into odom so the verifier does not depend on a brittle raw world-x
        # displacement.
        pose.pose.position.x = (
            float(start_pose.position.x)
            + offset_x * math.cos(start_yaw)
            - offset_y * math.sin(start_yaw)
        )
        pose.pose.position.y = (
            float(start_pose.position.y)
            + offset_x * math.sin(start_yaw)
            + offset_y * math.cos(start_yaw)
        )
        pose.pose.position.z = 0.0
        pose.pose.orientation = yaw_to_quat(target_yaw)
        return pose, target_yaw

    def candidate_offsets(self, offset_x: float, offset_y: float):
        base_forward = max(float(offset_x), 0.05)
        forward_candidates = [
            base_forward,
            max(base_forward * 0.75, 0.08),
            max(base_forward * 0.60, 0.06),
            max(base_forward * 0.50, 0.05),
        ]
        lateral_candidates = [
            float(offset_y),
            float(offset_y) + 0.05,
            float(offset_y) - 0.05,
        ]
        seen = set()
        for candidate_x in forward_candidates:
            for candidate_y in lateral_candidates:
                key = (round(candidate_x, 3), round(candidate_y, 3))
                if key in seen:
                    continue
                seen.add(key)
                yield candidate_x, candidate_y

    def probe_path(self, goal_pose, timeout_sec: float) -> tuple[bool, int, float, str]:
        if not self._path_client.wait_for_server(timeout_sec=10.0):
            return False, 0, 0.0, "NO_PATH_SERVER"

        goal = ComputePathToPose.Goal()
        goal.goal = goal_pose
        goal.planner_id = "GridBased"
        goal.use_start = False

        send_future = self._path_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return False, 0, 0.0, "REJECTED"

        result_future = goal_handle.get_result_async()
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and not result_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

        if not result_future.done():
            cancel_future = goal_handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, cancel_future, timeout_sec=5.0)
            return False, 0, 0.0, "TIMEOUT"

        wrapped = result_future.result()
        status_name = STATUS_NAMES.get(wrapped.status, str(wrapped.status))
        path_poses = wrapped.result.path.poses
        path_pose_count = len(path_poses)
        path_length_m = 0.0
        previous_pose = None
        for pose_stamped in path_poses:
            if previous_pose is not None:
                dx = float(pose_stamped.pose.position.x) - float(previous_pose.pose.position.x)
                dy = float(pose_stamped.pose.position.y) - float(previous_pose.pose.position.y)
                path_length_m += math.hypot(dx, dy)
            previous_pose = pose_stamped
        if wrapped.status != GoalStatus.STATUS_SUCCEEDED or path_pose_count == 0:
            return False, path_pose_count, path_length_m, status_name
        return True, path_pose_count, path_length_m, status_name

    def select_reachable_goal(self, start_pose, start_yaw: float, offset_x: float, offset_y: float, yaw_offset: float, timeout_sec: float):
        probe_timeout = min(10.0, max(4.0, timeout_sec / 6.0))
        best_candidate = None
        for index, (candidate_x, candidate_y) in enumerate(self.candidate_offsets(offset_x, offset_y), start=1):
            goal_pose, _ = self.build_goal_pose(start_pose, start_yaw, candidate_x, candidate_y, yaw_offset)
            reachable, path_pose_count, path_length_m, status_name = self.probe_path(goal_pose, probe_timeout)
            print(
                f"real_route_goal_candidate_{index}: offset_x={candidate_x:.3f} "
                f"offset_y={candidate_y:.3f} status={status_name} path_poses={path_pose_count} "
                f"path_length_m={path_length_m:.3f}"
            )
            if not reachable:
                continue
            score = (path_length_m, path_pose_count)
            if best_candidate is None or score > best_candidate["score"]:
                best_candidate = {
                    "index": index,
                    "offset_x": candidate_x,
                    "offset_y": candidate_y,
                    "score": score,
                }
        if best_candidate is None:
            return None
        return best_candidate["index"], best_candidate["offset_x"], best_candidate["offset_y"]

    def send_goal_and_wait(self, offset_x: float, offset_y: float, yaw_offset: float, timeout_sec: float) -> int:
        if not self.wait_for_odom(20.0):
            print("real_route_goal_error: no_start_odom")
            return 2

        if not self._path_client.wait_for_server(timeout_sec=30.0):
            print("real_route_goal_error: no_path_server")
            return 2
        if not self._action_client.wait_for_server(timeout_sec=30.0):
            print("real_route_goal_error: no_action_server")
            return 2

        start_pose = self._start_odom.pose.pose
        start_yaw = quat_to_yaw(start_pose.orientation)
        selected = self.select_reachable_goal(start_pose, start_yaw, offset_x, offset_y, yaw_offset, timeout_sec)
        if selected is None:
            print("real_route_goal_error: no_reachable_goal")
            return 2

        selected_index, selected_offset_x, selected_offset_y = selected
        goal = NavigateToPose.Goal()
        goal.pose, target_yaw = self.build_goal_pose(start_pose, start_yaw, selected_offset_x, selected_offset_y, yaw_offset)

        print(f"real_route_goal_start_x: {start_pose.position.x:.6f}")
        print(f"real_route_goal_start_y: {start_pose.position.y:.6f}")
        print(f"real_route_goal_start_yaw: {start_yaw:.6f}")
        print(f"real_route_goal_selected_candidate: {selected_index}")
        print(f"real_route_goal_selected_offset_x: {selected_offset_x:.6f}")
        print(f"real_route_goal_selected_offset_y: {selected_offset_y:.6f}")
        print(f"real_route_goal_target_x: {goal.pose.pose.position.x:.6f}")
        print(f"real_route_goal_target_y: {goal.pose.pose.position.y:.6f}")
        print(f"real_route_goal_target_yaw: {target_yaw:.6f}")

        send_future = self._action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print("real_route_goal_error: goal_rejected")
            return 2

        result_future = goal_handle.get_result_async()
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and not result_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

        if not result_future.done():
            print("real_route_goal_error: result_timeout")
            cancel_future = goal_handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, cancel_future, timeout_sec=5.0)
            return 2

        result = result_future.result()
        status_name = STATUS_NAMES.get(result.status, str(result.status))
        print(f"real_route_goal_status: {status_name}")

        for _ in range(10):
            rclpy.spin_once(self, timeout_sec=0.1)

        if self._latest_odom is None or self._latest_diff_drive_odom is None:
            print("real_route_goal_error: missing_final_odom")
            return 2

        final_pose = self._latest_odom.pose.pose
        final_yaw = quat_to_yaw(final_pose.orientation)
        dx = float(final_pose.position.x) - float(start_pose.position.x)
        dy = float(final_pose.position.y) - float(start_pose.position.y)
        delta_xy = math.hypot(dx, dy)
        delta_yaw = normalize_angle(final_yaw - start_yaw)

        diff_start = self._start_diff_drive_odom.pose.pose
        diff_final = self._latest_diff_drive_odom.pose.pose
        diff_dx = float(diff_final.position.x) - float(diff_start.position.x)
        diff_dy = float(diff_final.position.y) - float(diff_start.position.y)
        diff_delta_xy = math.hypot(diff_dx, diff_dy)
        diff_delta_yaw = normalize_angle(
            quat_to_yaw(diff_final.orientation) - quat_to_yaw(diff_start.orientation)
        )

        print(f"real_route_goal_final_x: {final_pose.position.x:.6f}")
        print(f"real_route_goal_final_y: {final_pose.position.y:.6f}")
        print(f"real_route_goal_final_yaw: {final_yaw:.6f}")
        print(f"real_route_perception_odom_delta_x: {dx:.6f}")
        print(f"real_route_perception_odom_delta_y: {dy:.6f}")
        print(f"real_route_perception_odom_delta_xy: {delta_xy:.6f}")
        print(f"real_route_perception_odom_delta_yaw: {delta_yaw:.6f}")
        print(f"real_route_diff_drive_odom_delta_x: {diff_dx:.6f}")
        print(f"real_route_diff_drive_odom_delta_y: {diff_dy:.6f}")
        print(f"real_route_diff_drive_odom_delta_xy: {diff_delta_xy:.6f}")
        print(f"real_route_diff_drive_odom_delta_yaw: {diff_delta_yaw:.6f}")
        print(f"real_route_cmd_vel_nonzero_count: {self._cmd_vel_count}")
        print(f"real_route_cmd_vel_max_linear_x: {self._max_linear_x:.6f}")
        print(f"real_route_cmd_vel_max_angular_z: {self._max_angular_z:.6f}")

        min_perception_delta = float(os.environ.get("GO2W_REAL_ROUTE_MIN_PERCEPTION_ODOM_DELTA", "0.003"))
        min_diff_drive_delta = float(os.environ.get("GO2W_REAL_ROUTE_MIN_DIFF_DRIVE_ODOM_DELTA", "0.003"))

        if result.status != GoalStatus.STATUS_SUCCEEDED:
            print("real_route_goal_result: FAIL_STATUS")
            return 2
        if self._cmd_vel_count < 2:
            print("real_route_goal_result: FAIL_NO_CMD_VEL")
            return 2
        if delta_xy < min_perception_delta:
            print("real_route_goal_result: FAIL_NO_PERCEPTION_ODOM_MOTION")
            return 2
        if diff_delta_xy < min_diff_drive_delta:
            print("real_route_goal_result: FAIL_NO_DIFF_DRIVE_ODOM_MOTION")
            return 2

        print("real_route_goal_result: PASS")
        return 0


def main() -> int:
    rclpy.init()
    node = RealRouteGoalClient()
    try:
        offset_x = float(os.environ.get("GO2W_REAL_ROUTE_GOAL_OFFSET_X", "0.250"))
        offset_y = float(os.environ.get("GO2W_REAL_ROUTE_GOAL_OFFSET_Y", "0.000"))
        yaw_offset = float(os.environ.get("GO2W_REAL_ROUTE_GOAL_YAW_OFFSET", "0.0"))
        timeout_sec = float(os.environ.get("GO2W_REAL_ROUTE_NAV_TIMEOUT_SECONDS", "120"))
        return node.send_goal_and_wait(offset_x, offset_y, yaw_offset, timeout_sec)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
PYEOF
  chmod +x "${EVIDENCE_DIR}/real_route_goal_client.py"
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  export GZ_PARTITION="${PARTITION}"

  print_kv "go2w_real_model_route_following_result" "RUNNING"
  print_kv "repo_root" "${REPO_ROOT}"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"
  print_kv "gz_partition" "${GZ_PARTITION}"
  print_kv "route_world" "${ROUTE_WORLD}"
  print_kv "route_world_name" "${ROUTE_WORLD_NAME}"
  print_kv "nav2_params_file" "${NAV2_PARAMS_FILE}"
  print_kv "nav_timeout_seconds" "${NAV_TIMEOUT_SECONDS}"
  print_kv "nav_goal_offset_x" "${NAV_GOAL_OFFSET_X}"
  print_kv "nav_goal_offset_y" "${NAV_GOAL_OFFSET_Y}"
  print_kv "nav_goal_yaw_offset" "${NAV_GOAL_YAW_OFFSET}"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  "${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true

  if [ ! -f "${NAV2_PARAMS_FILE}" ]; then
    print_kv "nav2_params_file" "missing:${NAV2_PARAMS_FILE}"
    exit 2
  fi

  maybe_build_repo
  source_file_checked "${REPO_SETUP}" "repo_setup"
  source_file_checked "${FASTLIO_SETUP}" "fastlio_setup"

  write_fastlio_params
  write_nav_goal_client

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
  if ! grep -q "FL_hip_joint" "${EVIDENCE_DIR}/joint_states.txt"; then
    print_kv "joint_states_include_leg_joint" "FAIL"
    sed -n '1,160p' "${EVIDENCE_DIR}/joint_states.txt" || true
    exit 2
  fi
  if ! grep -q "FL_foot_joint" "${EVIDENCE_DIR}/joint_states.txt"; then
    print_kv "joint_states_include_wheel_joint" "FAIL"
    sed -n '1,160p' "${EVIDENCE_DIR}/joint_states.txt" || true
    exit 2
  fi
  print_kv "joint_states_include_leg_joint" "PASS"
  print_kv "joint_states_include_wheel_joint" "PASS"

  sample_tf_to "pre_perception" 6
  require_tf_edge_absent "pre_perception_odom_base_link" odom base_link "${EVIDENCE_DIR}/tf_pre_perception_all.txt"
  require_tf_edge_absent "pre_perception_map_odom" map odom "${EVIDENCE_DIR}/tf_pre_perception_all.txt"

  setsid ros2 launch go2w_perception phase2f_tf_authority.launch.py >"${EVIDENCE_DIR}/perception.log" 2>&1 &
  PERCEPTION_PID="$!"
  sleep 3
  require_process_alive "${PERCEPTION_PID}" "perception_process_alive" "${EVIDENCE_DIR}/perception.log"
  require_adapted_time_field "${EVIDENCE_DIR}/adapted_lidar_fields.txt"

  setsid ros2 run fast_lio fastlio_mapping --ros-args --params-file "${EVIDENCE_DIR}/real_route_fastlio.yaml" >"${EVIDENCE_DIR}/fastlio.log" 2>&1 &
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

  require_action_server "${EVIDENCE_DIR}/action_list.txt"
  require_param_contains "controller_odom_topic" /controller_server odom_topic /go2w/perception/odom "${EVIDENCE_DIR}/controller_odom_topic.txt"
  require_param_contains "bt_navigator_global_frame" /bt_navigator global_frame odom "${EVIDENCE_DIR}/bt_navigator_global_frame.txt"
  require_param_contains "bt_navigator_robot_base_frame" /bt_navigator robot_base_frame base_link "${EVIDENCE_DIR}/bt_navigator_robot_base_frame.txt"
  require_topic_once "local_costmap_topic_once" /local_costmap/costmap "${EVIDENCE_DIR}/local_costmap.txt" 20
  require_topic_once "global_costmap_topic_once" /global_costmap/costmap "${EVIDENCE_DIR}/global_costmap.txt" 20
  require_field_once "local_costmap_frame" /local_costmap/costmap header.frame_id odom "${EVIDENCE_DIR}/local_costmap_frame.txt" 15
  sleep 10

  require_no_forbidden_nodes "${EVIDENCE_DIR}/node_list_pre_goal.txt"

  setsid env \
    GO2W_REAL_ROUTE_GOAL_OFFSET_X="${NAV_GOAL_OFFSET_X}" \
    GO2W_REAL_ROUTE_GOAL_OFFSET_Y="${NAV_GOAL_OFFSET_Y}" \
    GO2W_REAL_ROUTE_GOAL_YAW_OFFSET="${NAV_GOAL_YAW_OFFSET}" \
    GO2W_REAL_ROUTE_NAV_TIMEOUT_SECONDS="${NAV_TIMEOUT_SECONDS}" \
    GO2W_REAL_ROUTE_MIN_PERCEPTION_ODOM_DELTA="${MIN_PERCEPTION_ODOM_DELTA}" \
    GO2W_REAL_ROUTE_MIN_DIFF_DRIVE_ODOM_DELTA="${MIN_DIFF_DRIVE_ODOM_DELTA}" \
    python3 "${EVIDENCE_DIR}/real_route_goal_client.py" >"${EVIDENCE_DIR}/nav_goal.txt" 2>&1

  grep -E '^real_route_' "${EVIDENCE_DIR}/nav_goal.txt" || true
  if ! grep -q "real_route_goal_result: PASS" "${EVIDENCE_DIR}/nav_goal.txt"; then
    print_kv "real_route_goal_result" "FAIL"
    sed -n '1,260p' "${EVIDENCE_DIR}/nav_goal.txt" || true
    exit 2
  fi

  require_log_absent "sim_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/sim.log"
  require_log_absent "perception_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/perception.log"
  require_log_absent "fastlio_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback|Caught exception" "${EVIDENCE_DIR}/fastlio.log"
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
  print_kv "go2w_real_model_route_following_result" "PASS"
}

main "$@"
