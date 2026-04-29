#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_WS="${GO2W_FASTLIO_WS:-/tmp/go2w_phase2d_fastlio_ws}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
FASTLIO_SETUP="${FASTLIO_WS}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE2E_EVIDENCE_DIR:-/tmp/go2w_phase2e_fastlio_contract_${$}}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 80 ))}"
PARTITION="go2w_phase2e_${$}"
REBUILD_REPO="${GO2W_PHASE2E_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_PHASE2E_CLEAN_EVIDENCE:-0}"
STIMULATE_CMDVEL="${GO2W_PHASE2E_STIMULATE_CMDVEL:-1}"
FASTLIO_PID=""
ADAPTER_PID=""
SIM_PID=""
contract_odom_frame_pid=""
contract_odom_child_pid=""
contract_cloud_registered_pid=""
contract_cloud_body_pid=""
contract_laser_map_pid=""
contract_path_pid=""

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
  terminate_pid "${FASTLIO_PID}" "fastlio"
  pkill -INT -f "${FASTLIO_WS}/install/fast_lio/lib/fast_lio/fastlio_mapping" 2>/dev/null || true
  terminate_pid "${ADAPTER_PID}" "adapter"
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

start_field_capture() {
  local pid_var="$1"
  shift
  local topic="$1"
  local field="$2"
  local output_file="$3"
  local timeout_seconds="$4"
  timeout "${timeout_seconds}s" ros2 topic echo --once "${topic}" --field "${field}" >"${output_file}" 2>&1 &
  printf -v "${pid_var}" '%s' "$!"
}

require_field_capture() {
  local key="$1"
  local expected="$2"
  local output_file="$3"
  local pid="$4"
  if ! wait "${pid}"; then
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

sample_tf() {
  timeout 8s ros2 topic echo /tf >"${EVIDENCE_DIR}/tf_dynamic.txt" 2>&1 || true
  timeout 4s ros2 topic echo --once /tf_static >"${EVIDENCE_DIR}/tf_static.txt" 2>&1 || true
  cat "${EVIDENCE_DIR}/tf_dynamic.txt" "${EVIDENCE_DIR}/tf_static.txt" >"${EVIDENCE_DIR}/tf_all.txt"
}

tf_edge_present() {
  local parent="$1"
  local child="$2"
  awk -v parent="${parent}" -v child="${child}" '
    /frame_id:/ {
      current_parent=$0
    }
    /child_frame_id:/ {
      if (current_parent ~ parent && $0 ~ child) {
        found=1
      }
    }
    END {
      exit(found ? 0 : 1)
    }
  ' "${EVIDENCE_DIR}/tf_all.txt"
}

write_fastlio_params() {
  cat >"${EVIDENCE_DIR}/phase2e_fastlio.yaml" <<'EOF'
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

printf '# Phase 2E FAST-LIO Contract Verification\n'
print_kv "repo_root" "${REPO_ROOT}"
print_kv "fastlio_workspace_path" "${FASTLIO_WS}"
print_kv "ros_domain_id" "${DOMAIN_ID}"
print_kv "gz_partition" "${PARTITION}"
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

ros2 launch go2w_perception phase2e_fastlio_contract.launch.py >"${EVIDENCE_DIR}/adapter.log" 2>&1 &
ADAPTER_PID="$!"
sleep 3
require_process_alive "${ADAPTER_PID}" "adapter_process_alive" "${EVIDENCE_DIR}/adapter.log"

require_adapted_time_field "${EVIDENCE_DIR}/adapted_lidar_fields.txt"

start_field_capture contract_odom_frame_pid /go2w/perception/odom header.frame_id "${EVIDENCE_DIR}/contract_odom_frame.txt" 45
start_field_capture contract_odom_child_pid /go2w/perception/odom child_frame_id "${EVIDENCE_DIR}/contract_odom_child_frame.txt" 45
start_field_capture contract_cloud_registered_pid /go2w/perception/cloud_registered header.frame_id "${EVIDENCE_DIR}/contract_cloud_registered_frame.txt" 45
start_field_capture contract_cloud_body_pid /go2w/perception/cloud_body header.frame_id "${EVIDENCE_DIR}/contract_cloud_body_frame.txt" 45
start_field_capture contract_laser_map_pid /go2w/perception/laser_map header.frame_id "${EVIDENCE_DIR}/contract_laser_map_frame.txt" 45
start_field_capture contract_path_pid /go2w/perception/path header.frame_id "${EVIDENCE_DIR}/contract_path_frame.txt" 45

ros2 run fast_lio fastlio_mapping --ros-args --params-file "${EVIDENCE_DIR}/phase2e_fastlio.yaml" >"${EVIDENCE_DIR}/fastlio.log" 2>&1 &
FASTLIO_PID="$!"
sleep 8
require_process_alive "${FASTLIO_PID}" "fastlio_process_alive" "${EVIDENCE_DIR}/fastlio.log"

if [ "${STIMULATE_CMDVEL}" = "1" ]; then
  timeout 4s ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}, angular: {z: 0.0}}" -r 5 >"${EVIDENCE_DIR}/cmd_vel.txt" 2>&1 || true
fi

require_topic_once "raw_fastlio_topic_odometry" /Odometry "${EVIDENCE_DIR}/raw_odometry.txt" 20
require_topic_once "raw_fastlio_topic_cloud_registered" /cloud_registered "${EVIDENCE_DIR}/raw_cloud_registered.txt" 20
require_topic_once "raw_fastlio_topic_cloud_registered_body" /cloud_registered_body "${EVIDENCE_DIR}/raw_cloud_registered_body.txt" 20
require_topic_once "raw_fastlio_topic_laser_map" /Laser_map "${EVIDENCE_DIR}/raw_laser_map.txt" 20
require_topic_once "raw_fastlio_topic_path" /path "${EVIDENCE_DIR}/raw_path.txt" 20

require_field_capture "contract_odometry_frame" odom "${EVIDENCE_DIR}/contract_odom_frame.txt" "${contract_odom_frame_pid}"
require_field_capture "contract_odometry_child_frame" base_link "${EVIDENCE_DIR}/contract_odom_child_frame.txt" "${contract_odom_child_pid}"
require_field_capture "contract_cloud_registered_frame" odom "${EVIDENCE_DIR}/contract_cloud_registered_frame.txt" "${contract_cloud_registered_pid}"
require_field_capture "contract_cloud_body_frame" base_link "${EVIDENCE_DIR}/contract_cloud_body_frame.txt" "${contract_cloud_body_pid}"
require_field_capture "contract_laser_map_frame" odom "${EVIDENCE_DIR}/contract_laser_map_frame.txt" "${contract_laser_map_pid}"
require_field_capture "contract_path_frame" odom "${EVIDENCE_DIR}/contract_path_frame.txt" "${contract_path_pid}"

missing_time_warning_count="$(grep -c "Failed to find match for field 'time'" "${EVIDENCE_DIR}/fastlio.log" || true)"
print_kv "fastlio_missing_time_warning_count" "${missing_time_warning_count}"
if [ "${missing_time_warning_count}" != "0" ]; then
  exit 2
fi

sample_tf
if tf_edge_present "camera_init" "body"; then
  print_kv "fastlio_tf_camera_init_body" "PRESENT"
  exit 2
else
  print_kv "fastlio_tf_camera_init_body" "ABSENT"
fi

if tf_edge_present "odom" "base_link"; then
  print_kv "odom_base_link_authority" "PRESENT"
  exit 2
else
  print_kv "odom_base_link_authority" "ABSENT"
fi

print_kv "sim_log" "${EVIDENCE_DIR}/sim.log"
print_kv "adapter_log" "${EVIDENCE_DIR}/adapter.log"
print_kv "fastlio_log" "${EVIDENCE_DIR}/fastlio.log"
print_kv "tf_sample" "${EVIDENCE_DIR}/tf_all.txt"
print_kv "phase2e_result" "PASS"
