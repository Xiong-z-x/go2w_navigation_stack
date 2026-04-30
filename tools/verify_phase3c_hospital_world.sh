#!/usr/bin/env bash
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${ROOT_DIR}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE3C_WORLD_EVIDENCE_DIR:-/tmp/go2w_phase3c_hospital_world_${$}}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 120) + 80 ))}"
PARTITION="go2w_phase3c_world_${$}"
REBUILD_REPO="${GO2W_PHASE3C_WORLD_REBUILD_REPO:-1}"
CLEAN_EVIDENCE="${GO2W_PHASE3C_WORLD_CLEAN_EVIDENCE:-0}"
WORLD_NAME="go2w_phase3c_hospital_multifloor_world"
LAUNCH_PID=""

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

terminate_launch() {
  local attempts_remaining=5

  if [ -n "${LAUNCH_PID}" ] && kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill -INT "${LAUNCH_PID}" 2>/dev/null || true
    while [ "${attempts_remaining}" -gt 0 ]; do
      if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
        wait "${LAUNCH_PID}" 2>/dev/null || true
        return
      fi
      sleep 1
      attempts_remaining=$((attempts_remaining - 1))
    done

    print_kv "cleanup_launch" "forced_terminate"
    kill -TERM "${LAUNCH_PID}" 2>/dev/null || true
    sleep 1
    if kill -0 "${LAUNCH_PID}" 2>/dev/null; then
      kill -KILL "${LAUNCH_PID}" 2>/dev/null || true
    fi
    wait "${LAUNCH_PID}" 2>/dev/null || true
  fi
}

cleanup() {
  terminate_launch
  "${ROOT_DIR}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true
  if [ "${CLEAN_EVIDENCE}" = "1" ]; then
    rm -rf "${EVIDENCE_DIR}"
  fi
}

trap cleanup EXIT

wait_for_text() {
  local pattern="$1"
  local file="$2"
  local timeout_seconds="$3"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if grep -qE "${pattern}" "${file}" 2>/dev/null; then
      return 0
    fi
    if [ -n "${LAUNCH_PID}" ] && ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
      print_kv "launch_process" "exited_early"
      sed -n '1,260p' "${file}" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  print_kv "wait_for_text" "timeout:${pattern}"
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

maybe_build_repo() {
  if [ "${REBUILD_REPO}" = "1" ] || [ ! -f "${REPO_SETUP}" ]; then
    source_file_checked "${ROS_SETUP}" "ros_setup"
    (
      cd "${ROOT_DIR}"
      colcon build --symlink-install --packages-select go2w_description go2w_sim
    )
  fi
}

validate_world_static() {
  local world_file="$1"
  local output_file="${EVIDENCE_DIR}/static_world_validation.txt"

  if ! python3 - "${world_file}" "${WORLD_NAME}" >"${output_file}" 2>&1 <<'PY'
import sys
import xml.etree.ElementTree as ET


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}")


world_file = sys.argv[1]
expected_world_name = sys.argv[2]
tree = ET.parse(world_file)
root = tree.getroot()
world = root.find("world")
assert world is not None
assert world.attrib.get("name") == expected_world_name
models = {model.attrib.get("name") for model in world.findall("model")}
required = {
    "hospital_floor_1_deck",
    "hospital_floor_2_deck",
    "hospital_manual_stair_connector",
    "hospital_floor_1_corridor_walls",
    "hospital_floor_2_corridor_walls",
    "hospital_localization_columns",
}
missing = sorted(required - models)
assert not missing, missing
print_kv("world_name", expected_world_name)
print_kv("world_model_count", len(models))
print_kv("world_static_validation", "PASS")
PY
  then
    print_kv "world_static_validation" "FAIL"
    sed -n '1,200p' "${output_file}" || true
    exit 2
  fi

  sed -n '1,120p' "${output_file}"
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  print_kv "phase3c_hospital_world_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${DOMAIN_ID}"

  maybe_build_repo
  source_file_checked "${ROS_SETUP}" "ros_setup"
  source_file_checked "${REPO_SETUP}" "repo_setup"

  local world_file
  world_file="$(ros2 pkg prefix go2w_sim)/share/go2w_sim/worlds/phase3c_hospital_multifloor_world.sdf"
  [ -f "${world_file}" ] || { print_kv "phase3c_world_file" "MISSING:${world_file}"; exit 2; }
  print_kv "phase3c_world_file" "${world_file}"
  validate_world_static "${world_file}"

  "${ROOT_DIR}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true

  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  export GZ_PARTITION="${PARTITION}"

  ros2 launch go2w_sim sim.launch.py \
    use_gpu:=false \
    headless:=true \
    launch_rviz:=false \
    world:="${world_file}" \
    world_name:="${WORLD_NAME}" >"${EVIDENCE_DIR}/launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_text "ign gazebo-6" "${EVIDENCE_DIR}/launch.log" 25
  wait_for_text "Configured and activated .*joint_state_broadcaster" "${EVIDENCE_DIR}/launch.log" 45
  wait_for_text "Configured and activated .*diff_drive_controller" "${EVIDENCE_DIR}/launch.log" 45

  require_topic_once /clock "${EVIDENCE_DIR}/clock.txt" 15
  require_topic_once /imu "${EVIDENCE_DIR}/imu.txt" 15
  require_topic_once /lidar_points "${EVIDENCE_DIR}/lidar_points.txt" 15

  if grep -q 'not found:' "${EVIDENCE_DIR}/launch.log"; then
    print_kv "launch_missing_prefix_noise" "FAIL"
    sed -n '1,220p' "${EVIDENCE_DIR}/launch.log" || true
    exit 2
  fi

  print_kv "gazebo_runtime" "ign gazebo-6"
  print_kv "phase3c_hospital_world_result" "PASS"
}

main "$@"
