#!/usr/bin/env bash
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_NAME="${GO2W_MODEL_NAME:-go2w_placeholder}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

# shellcheck source=/dev/null
source /opt/ros/humble/setup.bash
# shellcheck source=/dev/null
source "${ROOT_DIR}/install/setup.bash"
set -u

require_once_message() {
  local topic="$1"
  local output_file="$2"
  if ! timeout 15s ros2 topic echo --once "${topic}" >"${output_file}" 2>&1; then
    echo "[FAIL] topic ${topic} did not yield a message within timeout"
    cat "${output_file}" || true
    exit 1
  fi
  echo "[PASS] topic ${topic} produced a message"
}

extract_average_rate() {
  local log_file="$1"
  local topic_name="$2"
  local average_rate
  average_rate="$(grep 'average rate:' "${log_file}" | tail -n 1 | awk '{print $3}')"
  if [[ -z "${average_rate}" ]]; then
    echo "[FAIL] topic ${topic_name} did not produce a usable rate sample"
    cat "${log_file}" || true
    exit 1
  fi
  echo "${average_rate}"
}

echo "[INFO] collecting topic list"
ros2 topic list | sort >"${TMP_DIR}/topic_list.txt"

require_once_message /clock "${TMP_DIR}/clock.txt"
require_once_message /imu "${TMP_DIR}/imu.txt"
require_once_message /lidar_points "${TMP_DIR}/lidar_points.txt"

echo "[INFO] sampling topic rates"
timeout 6s ros2 topic hz /imu >"${TMP_DIR}/imu_hz.txt" 2>&1 || true
timeout 6s ros2 topic hz /lidar_points >"${TMP_DIR}/lidar_hz.txt" 2>&1 || true
IMU_RATE="$(extract_average_rate "${TMP_DIR}/imu_hz.txt" "/imu")"
LIDAR_RATE="$(extract_average_rate "${TMP_DIR}/lidar_hz.txt" "/lidar_points")"

echo "[INFO] sampling TF graph"
pushd "${TMP_DIR}" >/dev/null
ros2 run tf2_tools view_frames >"${TMP_DIR}/view_frames.txt" 2>&1
popd >/dev/null

python3 - "${TMP_DIR}/view_frames.txt" "${MODEL_NAME}" <<'PY'
import re
import sys

view_frames_path = sys.argv[1]
model_name = sys.argv[2]
text = open(view_frames_path, "r", encoding="utf-8").read()

required_frames = [
    "base_link",
    "lidar_link",
    "imu_link",
    f"{model_name}/base_footprint/lidar_sensor",
    f"{model_name}/base_footprint/imu_sensor",
]

missing = [frame for frame in required_frames if f"{frame}: " not in text]
if missing:
    print(f"[FAIL] required TF frames missing: {', '.join(missing)}")
    sys.exit(1)

match = re.search(r"base_link: \\n  parent: '([^']+)'", text)
if not match:
    print("[FAIL] could not locate base_link parent in TF graph")
    sys.exit(1)

base_parent = match.group(1)
if base_parent == "odom":
    print("[FAIL] base_link is still parented to odom")
    sys.exit(1)

if "parent: 'odom'" in text:
    print("[FAIL] an odom parent edge still exists in the current TF graph")
    sys.exit(1)

print(f"[PASS] base_link parent is '{base_parent}', and no odom parent edge exists")
PY

echo "[INFO] verification summary"
echo "clock_message: PASS"
echo "imu_message: PASS"
echo "lidar_points_message: PASS"
echo "imu_rate_hz: ${IMU_RATE}"
echo "lidar_points_rate_hz: ${LIDAR_RATE}"
echo "required_tf_frames: PASS"
echo "odom_to_base_link_absent: PASS"
echo
echo "[INFO] recorded topic list"
cat "${TMP_DIR}/topic_list.txt"
