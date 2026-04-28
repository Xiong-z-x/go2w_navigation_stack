#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_SRC="${GO2W_FASTLIO_SRC:-/tmp/fast_lio_ros2_probe}"
FASTLIO_WS="${GO2W_FASTLIO_WS:-/tmp/go2w_phase2d_fastlio_ws}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
FASTLIO_SETUP="${FASTLIO_WS}/install/setup.bash"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
TMP_DIR="${GO2W_PHASE2D_EVIDENCE_DIR:-/tmp/go2w_phase2d_fastlio_no_tf_dryrun_${$}}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 80 ))}"
PARTITION="go2w_phase2d_${$}"
FASTLIO_PID=""
SIM_PID=""
PHASE2D_STRICT="${GO2W_PHASE2D_STRICT:-0}"
SKIP_PREPARE="${GO2W_FASTLIO_SKIP_PREPARE:-0}"
REBUILD_REPO="${GO2W_PHASE2D_REBUILD_REPO:-0}"
STIMULATE_CMDVEL="${GO2W_PHASE2D_STIMULATE_CMDVEL:-1}"
CLEAN_EVIDENCE="${GO2W_PHASE2D_CLEAN_EVIDENCE:-0}"

set -u

print_kv() {
  printf '%s: %s\n' "$1" "$2"
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
  terminate_pid "${SIM_PID}" "sim"
  "${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true
  if [ "${CLEAN_EVIDENCE}" = "1" ]; then
    rm -rf "${TMP_DIR}"
  fi
}

trap cleanup EXIT

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

maybe_build_repo() {
  if [ "${REBUILD_REPO}" = "1" ] || [ ! -f "${REPO_SETUP}" ]; then
    source_file_checked "${ROS_SETUP}" "ros_setup"
    (
      cd "${REPO_ROOT}"
      colcon build --symlink-install --packages-select go2w_description go2w_sim
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

require_topic_once() {
  local topic="$1"
  local output_file="$2"
  local timeout_seconds="$3"
  if ! timeout "${timeout_seconds}s" ros2 topic echo --once "${topic}" >"${output_file}" 2>&1; then
    print_kv "required_topic_${topic//\//_}" "FAIL"
    sed -n '1,160p' "${output_file}" || true
    exit 2
  fi
  print_kv "required_topic_${topic//\//_}" "PASS"
}

observe_topic_once() {
  local key="$1"
  local topic="$2"
  local output_file="$3"
  local timeout_seconds="$4"
  if timeout "${timeout_seconds}s" ros2 topic echo --once "${topic}" >"${output_file}" 2>&1; then
    print_kv "${key}" "PASS"
    return 0
  fi
  print_kv "${key}" "NO_MESSAGE"
  return 1
}

sample_tf() {
  timeout 8s ros2 topic echo /tf >"${TMP_DIR}/tf_dynamic.txt" 2>&1 || true
  timeout 4s ros2 topic echo --once /tf_static >"${TMP_DIR}/tf_static.txt" 2>&1 || true
  cat "${TMP_DIR}/tf_dynamic.txt" "${TMP_DIR}/tf_static.txt" >"${TMP_DIR}/tf_all.txt"
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
  ' "${TMP_DIR}/tf_all.txt"
}

write_fastlio_params() {
  cat >"${TMP_DIR}/phase2d_fastlio.yaml" <<'EOF'
laser_mapping:
  ros__parameters:
    use_sim_time: true
    common.lid_topic: /lidar_points
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

strict_exit_if_needed() {
  local result="$1"
  if [ "${PHASE2D_STRICT}" = "1" ] && [ "${result}" != "PASS" ]; then
    exit 1
  fi
}

printf '# Phase 2D FAST-LIO2 No-TF Runtime Dry-Run\n'
print_kv "repo_root" "${REPO_ROOT}"
print_kv "fastlio_source_path" "${FASTLIO_SRC}"
print_kv "fastlio_workspace_path" "${FASTLIO_WS}"
print_kv "ros_domain_id" "${DOMAIN_ID}"
print_kv "gz_partition" "${PARTITION}"
print_kv "evidence_dir" "${TMP_DIR}"
mkdir -p "${TMP_DIR}"

if [ "${SKIP_PREPARE}" != "1" ]; then
  "${REPO_ROOT}/tools/prepare_phase2d_fastlio_external.sh"
else
  print_kv "prepare_status" "skipped"
fi

maybe_build_repo
source_file_checked "${ROS_SETUP}" "ros_setup"
source_file_checked "${REPO_SETUP}" "repo_setup"
source_file_checked "${FASTLIO_SETUP}" "fastlio_setup"

"${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true

export ROS_DOMAIN_ID="${DOMAIN_ID}"
export GZ_PARTITION="${PARTITION}"

write_fastlio_params

ros2 launch go2w_sim sim.launch.py use_gpu:=false headless:=true launch_rviz:=false >"${TMP_DIR}/sim.log" 2>&1 &
SIM_PID="$!"

wait_for_log "ign gazebo-6" "${TMP_DIR}/sim.log" 25
wait_for_log "Configured and activated .*joint_state_broadcaster" "${TMP_DIR}/sim.log" 35
wait_for_log "Configured and activated .*diff_drive_controller" "${TMP_DIR}/sim.log" 35

require_topic_once /clock "${TMP_DIR}/clock.txt" 15
require_topic_once /imu "${TMP_DIR}/imu.txt" 15
require_topic_once /lidar_points "${TMP_DIR}/lidar_points.txt" 15

ros2 run fast_lio fastlio_mapping --ros-args --params-file "${TMP_DIR}/phase2d_fastlio.yaml" >"${TMP_DIR}/fastlio.log" 2>&1 &
FASTLIO_PID="$!"
sleep 8

if kill -0 "${FASTLIO_PID}" 2>/dev/null; then
  print_kv "fastlio_process_alive" "PASS"
else
  print_kv "fastlio_process_alive" "FAIL"
fi

if [ "${STIMULATE_CMDVEL}" = "1" ]; then
  timeout 4s ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}, angular: {z: 0.0}}" -r 5 >"${TMP_DIR}/cmd_vel.txt" 2>&1 || true
fi

sleep 8

output_pass_count=0
if observe_topic_once "fastlio_topic_odometry" /Odometry "${TMP_DIR}/odometry.txt" 12; then
  output_pass_count=$((output_pass_count + 1))
fi
if observe_topic_once "fastlio_topic_cloud_registered" /cloud_registered "${TMP_DIR}/cloud_registered.txt" 12; then
  output_pass_count=$((output_pass_count + 1))
fi
if observe_topic_once "fastlio_topic_cloud_registered_body" /cloud_registered_body "${TMP_DIR}/cloud_registered_body.txt" 12; then
  output_pass_count=$((output_pass_count + 1))
fi
if observe_topic_once "fastlio_topic_laser_map" /Laser_map "${TMP_DIR}/laser_map.txt" 12; then
  output_pass_count=$((output_pass_count + 1))
fi
if observe_topic_once "fastlio_topic_path" /path "${TMP_DIR}/path.txt" 12; then
  output_pass_count=$((output_pass_count + 1))
fi

sample_tf

tf_violation="false"
if tf_edge_present "camera_init" "body"; then
  print_kv "fastlio_tf_camera_init_body" "PRESENT"
  tf_violation="true"
else
  print_kv "fastlio_tf_camera_init_body" "ABSENT"
fi

if tf_edge_present "odom" "base_link"; then
  print_kv "odom_base_link_authority" "PRESENT"
  tf_violation="true"
else
  print_kv "odom_base_link_authority" "ABSENT"
fi

print_kv "fastlio_output_topics_with_messages" "${output_pass_count}"
print_kv "sim_log" "${TMP_DIR}/sim.log"
print_kv "fastlio_log" "${TMP_DIR}/fastlio.log"
print_kv "fastlio_params" "${TMP_DIR}/phase2d_fastlio.yaml"
print_kv "tf_sample" "${TMP_DIR}/tf_all.txt"

phase2d_result="PARTIAL"
if [ "${tf_violation}" = "true" ]; then
  phase2d_result="FAIL_FORBIDDEN_TF"
elif ! kill -0 "${FASTLIO_PID}" 2>/dev/null; then
  phase2d_result="PARTIAL_FASTLIO_EXITED"
elif [ "${output_pass_count}" -gt 0 ]; then
  phase2d_result="PASS"
else
  phase2d_result="PARTIAL_NO_FASTLIO_OUTPUT"
fi

print_kv "phase2d_result" "${phase2d_result}"
strict_exit_if_needed "${phase2d_result}"
