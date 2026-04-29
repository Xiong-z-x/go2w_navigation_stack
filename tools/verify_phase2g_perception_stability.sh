#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_WS="${GO2W_FASTLIO_WS:-/tmp/go2w_phase2d_fastlio_ws}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
FASTLIO_SETUP="${FASTLIO_WS}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE2G_EVIDENCE_DIR:-/tmp/go2w_phase2g_perception_stability_${$}}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 80 ))}"
PARTITION="go2w_phase2g_${$}"
REBUILD_REPO="${GO2W_PHASE2G_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_PHASE2G_CLEAN_EVIDENCE:-0}"
STABILITY_SECONDS="${GO2W_PHASE2G_STABILITY_SECONDS:-30}"
FASTLIO_PID=""
PERCEPTION_PID=""
SIM_PID=""
CMDVEL_PID=""
odom_hz_pid=""
tf_hz_pid=""
adapted_lidar_hz_pid=""
cloud_registered_hz_pid=""

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
  terminate_pid "${CMDVEL_PID}" "cmd_vel"
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
      colcon build --symlink-install --packages-select go2w_perception go2w_description go2w_sim
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
    sed -n '1,220p' "${log_file}" || true
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

require_numeric_field_once() {
  local key="$1"
  local topic="$2"
  local field="$3"
  local output_file="$4"
  local timeout_seconds="$5"
  local value
  if ! timeout "${timeout_seconds}s" ros2 topic echo --once "${topic}" --field "${field}" >"${output_file}" 2>&1; then
    print_kv "${key}" "FAIL_NO_MESSAGE"
    sed -n '1,160p' "${output_file}" || true
    exit 2
  fi
  if ! awk 'NF == 1 && $1 ~ /^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$/ { found=1 } END { exit(found ? 0 : 1) }' "${output_file}"; then
    print_kv "${key}" "FAIL_NOT_NUMERIC"
    sed -n '1,160p' "${output_file}" || true
    exit 2
  fi
  value="$(numeric_file_value "${output_file}")"
  print_kv "${key}" "${value}"
}

numeric_file_value() {
  awk 'NF == 1 && $1 ~ /^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$/ { value=$1 } END { print value }' "$1"
}

print_numeric_delta() {
  local key="$1"
  local start_file="$2"
  local end_file="$3"
  local start_value
  local end_value
  start_value="$(numeric_file_value "${start_file}")"
  end_value="$(numeric_file_value "${end_file}")"
  print_kv "${key}" "${start_value}->${end_value}"
}

require_cmd_vel_publish_count() {
  local output_file="$1"
  local min_count="$2"
  local count
  count="$(grep -c "publishing #" "${output_file}" || true)"
  if [ "${count}" -ge "${min_count}" ]; then
    print_kv "cmd_vel_publish_count" "${count}"
    return
  fi
  print_kv "cmd_vel_publish_count" "FAIL:${count}<${min_count}"
  sed -n '1,160p' "${output_file}" || true
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

require_log_absent() {
  local key="$1"
  local pattern="$2"
  local log_file="$3"
  local count
  count="$(grep -Ec "${pattern}" "${log_file}" || true)"
  print_kv "${key}" "${count}"
  if [ "${count}" != "0" ]; then
    sed -n '1,220p' "${log_file}" || true
    exit 2
  fi
}

write_fastlio_params() {
  cat >"${EVIDENCE_DIR}/phase2g_fastlio.yaml" <<'EOF'
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

printf '# Phase 2G Perception Stability Verification\n'
print_kv "repo_root" "${REPO_ROOT}"
print_kv "fastlio_workspace_path" "${FASTLIO_WS}"
print_kv "ros_domain_id" "${DOMAIN_ID}"
print_kv "gz_partition" "${PARTITION}"
print_kv "stability_seconds" "${STABILITY_SECONDS}"
print_kv "evidence_dir" "${EVIDENCE_DIR}"
mkdir -p "${EVIDENCE_DIR}"

"${REPO_ROOT}/tools/prepare_phase2d_fastlio_external.sh"
maybe_build_repo

source_file_checked "${ROS_SETUP}" "ros_setup"
source_file_checked "${REPO_SETUP}" "repo_setup"
source_file_checked "${FASTLIO_SETUP}" "fastlio_setup"

"${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true

export ROS_DOMAIN_ID="${DOMAIN_ID}"
export GZ_PARTITION="${PARTITION}"

write_fastlio_params

ros2 launch go2w_sim sim.launch.py use_gpu:=false headless:=true launch_rviz:=false >"${EVIDENCE_DIR}/sim.log" 2>&1 &
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

ros2 launch go2w_perception phase2f_tf_authority.launch.py >"${EVIDENCE_DIR}/perception.log" 2>&1 &
PERCEPTION_PID="$!"
sleep 3
require_process_alive "${PERCEPTION_PID}" "perception_process_alive" "${EVIDENCE_DIR}/perception.log"

require_adapted_time_field "${EVIDENCE_DIR}/adapted_lidar_fields.txt"

ros2 run fast_lio fastlio_mapping --ros-args --params-file "${EVIDENCE_DIR}/phase2g_fastlio.yaml" >"${EVIDENCE_DIR}/fastlio.log" 2>&1 &
FASTLIO_PID="$!"
sleep 8
require_process_alive "${FASTLIO_PID}" "fastlio_process_alive" "${EVIDENCE_DIR}/fastlio.log"

require_topic_once "raw_fastlio_topic_odometry" /Odometry "${EVIDENCE_DIR}/raw_odometry.txt" 20
require_topic_once "contract_topic__odom" /go2w/perception/odom "${EVIDENCE_DIR}/contract_odom.txt" 20
require_topic_once "contract_topic__path" /go2w/perception/path "${EVIDENCE_DIR}/contract_path.txt" 20
require_topic_once "contract_topic__cloud_registered" /go2w/perception/cloud_registered "${EVIDENCE_DIR}/contract_cloud_registered.txt" 20
require_topic_once "contract_topic__cloud_body" /go2w/perception/cloud_body "${EVIDENCE_DIR}/contract_cloud_body.txt" 20
require_topic_once "contract_topic__laser_map" /go2w/perception/laser_map "${EVIDENCE_DIR}/contract_laser_map.txt" 20
require_field_once "contract_odometry_frame" /go2w/perception/odom header.frame_id odom "${EVIDENCE_DIR}/contract_odom_frame.txt" 15
require_field_once "contract_odometry_child_frame" /go2w/perception/odom child_frame_id base_link "${EVIDENCE_DIR}/contract_odom_child_frame.txt" 15
require_numeric_field_once "odom_start_x" /go2w/perception/odom pose.pose.position.x "${EVIDENCE_DIR}/odom_start_x.txt" 15

start_hz_capture odom_hz_pid /go2w/perception/odom "${EVIDENCE_DIR}/hz_odom.txt" "${STABILITY_SECONDS}"
start_hz_capture tf_hz_pid /tf "${EVIDENCE_DIR}/hz_tf.txt" "${STABILITY_SECONDS}"
start_hz_capture adapted_lidar_hz_pid /fastlio/input/lidar_points "${EVIDENCE_DIR}/hz_adapted_lidar.txt" "${STABILITY_SECONDS}"
start_hz_capture cloud_registered_hz_pid /go2w/perception/cloud_registered "${EVIDENCE_DIR}/hz_cloud_registered.txt" "${STABILITY_SECONDS}"

timeout "${STABILITY_SECONDS}s" ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.08}, angular: {z: 0.15}}" -r 5 >"${EVIDENCE_DIR}/cmd_vel.txt" 2>&1 &
CMDVEL_PID="$!"
wait "${CMDVEL_PID}" 2>/dev/null || true
CMDVEL_PID=""

require_hz_capture "odom_average_rate" "${EVIDENCE_DIR}/hz_odom.txt" "${odom_hz_pid}" 1.0
require_hz_capture "tf_average_rate" "${EVIDENCE_DIR}/hz_tf.txt" "${tf_hz_pid}" 1.0
require_hz_capture "adapted_lidar_average_rate" "${EVIDENCE_DIR}/hz_adapted_lidar.txt" "${adapted_lidar_hz_pid}" 1.0
require_hz_capture "cloud_registered_average_rate" "${EVIDENCE_DIR}/hz_cloud_registered.txt" "${cloud_registered_hz_pid}" 1.0

require_process_alive "${SIM_PID}" "sim_process_alive_after_window" "${EVIDENCE_DIR}/sim.log"
require_process_alive "${PERCEPTION_PID}" "perception_process_alive_after_window" "${EVIDENCE_DIR}/perception.log"
require_process_alive "${FASTLIO_PID}" "fastlio_process_alive_after_window" "${EVIDENCE_DIR}/fastlio.log"

require_cmd_vel_publish_count "${EVIDENCE_DIR}/cmd_vel.txt" 10
require_numeric_field_once "odom_end_x" /go2w/perception/odom pose.pose.position.x "${EVIDENCE_DIR}/odom_end_x.txt" 15
print_numeric_delta "odom_x_sample" "${EVIDENCE_DIR}/odom_start_x.txt" "${EVIDENCE_DIR}/odom_end_x.txt"

missing_time_warning_count="$(grep -c "Failed to find match for field 'time'" "${EVIDENCE_DIR}/fastlio.log" || true)"
print_kv "fastlio_missing_time_warning_count" "${missing_time_warning_count}"
if [ "${missing_time_warning_count}" != "0" ]; then
  exit 2
fi

require_log_absent "perception_contract_error_count" "contract adaptation failed|pointcloud timing adaptation failed|TF authority rejected odometry|Traceback" "${EVIDENCE_DIR}/perception.log"
require_log_absent "fastlio_runtime_exception_count" "Segmentation fault|Aborted|terminate called|Traceback" "${EVIDENCE_DIR}/fastlio.log"

sample_tf_to "post_stability" 8
require_tf_edge_absent "fastlio_tf_camera_init_body" camera_init body "${EVIDENCE_DIR}/tf_post_stability_all.txt"
require_tf_edge_present "odom_base_link_authority" odom base_link "${EVIDENCE_DIR}/tf_post_stability_all.txt"

print_kv "sim_log" "${EVIDENCE_DIR}/sim.log"
print_kv "perception_log" "${EVIDENCE_DIR}/perception.log"
print_kv "fastlio_log" "${EVIDENCE_DIR}/fastlio.log"
print_kv "tf_pre_activation_sample" "${EVIDENCE_DIR}/tf_pre_activation_all.txt"
print_kv "tf_post_stability_sample" "${EVIDENCE_DIR}/tf_post_stability_all.txt"
print_kv "phase2g_result" "PASS"
