#!/usr/bin/env bash
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 80 ))}"
PARTITION="go2w_verify_${$}"
LAUNCH_PID=""

cleanup() {
  if [[ -n "${LAUNCH_PID}" ]] && kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill -INT "${LAUNCH_PID}" 2>/dev/null || true
    wait "${LAUNCH_PID}" 2>/dev/null || true
  fi
  "${ROOT_DIR}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true
  rm -rf "${TMP_DIR}"
}

trap cleanup EXIT

# shellcheck source=/dev/null
source /opt/ros/humble/setup.bash
# shellcheck source=/dev/null
source "${ROOT_DIR}/install/setup.bash"
set -u

"${ROOT_DIR}/tools/cleanup_sim_runtime.sh" >/dev/null

export ROS_DOMAIN_ID="${DOMAIN_ID}"
export GZ_PARTITION="${PARTITION}"

timeout 35s ros2 launch go2w_sim sim.launch.py use_gpu:=false headless:=true launch_rviz:=false >"${TMP_DIR}/launch.log" 2>&1 &
LAUNCH_PID="$!"

wait_for_text() {
  local pattern="$1"
  local file="$2"
  local timeout_seconds="$3"
  local elapsed=0
  while (( elapsed < timeout_seconds )); do
    if grep -q "${pattern}" "${file}" 2>/dev/null; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "[FAIL] pattern not observed: ${pattern}"
  sed -n '1,220p' "${file}" || true
  exit 1
}

wait_for_text "ign gazebo-6" "${TMP_DIR}/launch.log" 20
wait_for_text "Configured and activated .*joint_state_broadcaster" "${TMP_DIR}/launch.log" 30
wait_for_text "Configured and activated .*diff_drive_controller" "${TMP_DIR}/launch.log" 30

if grep -q 'not found:' "${TMP_DIR}/launch.log"; then
  echo "[FAIL] launch log still contains missing chained prefix output"
  sed -n '1,220p' "${TMP_DIR}/launch.log" || true
  exit 1
fi

timeout 15s ros2 topic echo --once /clock >"${TMP_DIR}/clock.txt" 2>&1
timeout 15s ros2 topic echo --once /imu >"${TMP_DIR}/imu.txt" 2>&1
timeout 15s ros2 topic echo --once /lidar_points >"${TMP_DIR}/lidar.txt" 2>&1

controllers_output="$(ros2 control list_controllers)"
if ! grep -q 'joint_state_broadcaster.*active' <<<"${controllers_output}"; then
  echo "[FAIL] joint_state_broadcaster is not active"
  echo "${controllers_output}"
  exit 1
fi
if ! grep -q 'diff_drive_controller.*active' <<<"${controllers_output}"; then
  echo "[FAIL] diff_drive_controller is not active"
  echo "${controllers_output}"
  exit 1
fi

echo "[INFO] launch-chain verification summary"
echo "gazebo_runtime: ign gazebo-6"
echo "joint_state_broadcaster: active"
echo "diff_drive_controller: active"
echo "clock_message: PASS"
echo "imu_message: PASS"
echo "lidar_points_message: PASS"
