#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_REAL_MODEL_EVIDENCE_DIR:-/tmp/go2w_real_model_baseline_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 90) + 130 ))}"
PARTITION="go2w_real_model_${$}"
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
  terminate_pid "${LAUNCH_PID}" "go2w_real_model_launch"
  "${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true
}

trap cleanup EXIT

wait_for_text() {
  local pattern="$1"
  local file="$2"
  local timeout_seconds="$3"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if grep -q "${pattern}" "${file}" 2>/dev/null; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "missing_log_pattern" "${pattern}"
  sed -n '1,260p' "${file}" || true
  exit 2
}

require_grep() {
  local pattern="$1"
  local file="$2"
  local label="$3"
  if grep -q "${pattern}" "${file}"; then
    print_kv "${label}" "PASS"
    return 0
  fi

  print_kv "${label}" "FAIL"
  sed -n '1,220p' "${file}" || true
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
        print_kv "controller_states_ready" "PASS"
        return 0
      fi
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  print_kv "controller_states_ready" "FAIL"
  sed -n '1,220p' "${output_file}" || true
  exit 2
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  export GZ_PARTITION="${PARTITION}"

  print_kv "go2w_real_model_baseline_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"
  print_kv "gz_partition" "${GZ_PARTITION}"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  "${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null

  (
    cd "${REPO_ROOT}"
    colcon build --symlink-install --packages-select go2w_description go2w_control go2w_sim
  )
  source_file_checked "${REPO_SETUP}" "repo_setup"

  setsid ros2 launch go2w_sim sim_go2w_real.launch.py \
    use_gpu:=false \
    headless:=true \
    launch_rviz:=false \
    >"${EVIDENCE_DIR}/go2w_real_model_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_text "ign gazebo-" "${EVIDENCE_DIR}/go2w_real_model_launch.log" 25
  wait_for_controller_states_active "${EVIDENCE_DIR}/controllers.txt" 75
  wait_for_text "go2w_stand_initializer_profile: .*mode=legged .*body_height_m=0.32 .*foot_raise_height_m=0.09 .*gait_type=3 .*speed_level=0" "${EVIDENCE_DIR}/go2w_real_model_launch.log" 30
  wait_for_text "go2w_stand_initializer_result: PASS" "${EVIDENCE_DIR}/go2w_real_model_launch.log" 30

  timeout 15s ros2 topic echo --once /clock >"${EVIDENCE_DIR}/clock.txt" 2>&1
  timeout 15s ros2 topic echo --once /imu >"${EVIDENCE_DIR}/imu.txt" 2>&1
  timeout 15s ros2 topic echo --once /lidar_points >"${EVIDENCE_DIR}/lidar_points.txt" 2>&1
  timeout 15s ros2 topic echo --once /joint_states >"${EVIDENCE_DIR}/joint_states.txt" 2>&1
  timeout 15s ros2 control list_controllers >"${EVIDENCE_DIR}/controllers.txt" 2>&1
  timeout 10s ros2 param get /diff_drive_controller enable_odom_tf >"${EVIDENCE_DIR}/diff_drive_enable_odom_tf.txt" 2>&1

  require_grep "joint_state_broadcaster.*active" "${EVIDENCE_DIR}/controllers.txt" "joint_state_broadcaster_active"
  require_grep "leg_position_controller.*active" "${EVIDENCE_DIR}/controllers.txt" "leg_position_controller_active"
  require_grep "diff_drive_controller.*active" "${EVIDENCE_DIR}/controllers.txt" "diff_drive_controller_active"
  require_grep "FL_hip_joint" "${EVIDENCE_DIR}/joint_states.txt" "joint_states_include_leg_joint"
  require_grep "FL_foot_joint" "${EVIDENCE_DIR}/joint_states.txt" "joint_states_include_wheel_joint"
  require_grep "Boolean value is: False" "${EVIDENCE_DIR}/diff_drive_enable_odom_tf.txt" "diff_drive_odom_tf_disabled"
  require_grep "go2w_stand_initializer_profile: .*mode=legged .*body_height_m=0.32 .*foot_raise_height_m=0.09 .*gait_type=3 .*speed_level=0" "${EVIDENCE_DIR}/go2w_real_model_launch.log" "stand_initializer_profile_legged"
  require_grep "go2w_stand_initializer_result: PASS motion_mode=legged" "${EVIDENCE_DIR}/go2w_real_model_launch.log" "stand_initializer_result_legged"

  print_kv "clock_message" "PASS"
  print_kv "imu_message" "PASS"
  print_kv "lidar_points_message" "PASS"
  print_kv "stand_initializer" "PASS"
  print_kv "go2w_real_model_baseline_result" "PASS"
}

main "$@"
