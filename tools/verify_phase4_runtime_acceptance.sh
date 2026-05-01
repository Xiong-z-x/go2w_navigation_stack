#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE4_ACCEPTANCE_EVIDENCE_DIR:-/tmp/go2w_phase4_runtime_acceptance_$$}"
CLEAN_EVIDENCE="${GO2W_PHASE4_ACCEPTANCE_CLEAN_EVIDENCE:-0}"

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

cleanup() {
  if [ "${CLEAN_EVIDENCE}" = "1" ]; then
    rm -rf "${EVIDENCE_DIR}"
  fi
}

trap cleanup EXIT

run_gate() {
  local label="$1"
  local output_file="${EVIDENCE_DIR}/${label}.log"
  shift

  print_kv "${label}_result" "RUNNING"
  set +e
  (
    cd "${REPO_ROOT}"
    "$@"
  ) >"${output_file}" 2>&1
  local status="$?"
  set -e

  if [ "${status}" -ne 0 ]; then
    print_kv "${label}_result" "FAIL:${status}"
    print_kv "${label}_log" "${output_file}"
    sed -n '1,260p' "${output_file}" || true
    exit 2
  fi

  print_kv "${label}_result" "PASS"
  print_kv "${label}_log" "${output_file}"
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  print_kv "phase4_runtime_acceptance_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"

  run_gate "phase4_pre_handoff" \
    "${REPO_ROOT}/tools/verify_phase4_pre_handoff.sh"
  run_gate "phase4a_stair_handoff" \
    timeout 180s "${REPO_ROOT}/tools/verify_phase4a_stair_handoff.sh"
  run_gate "phase4b_mission_segments" \
    timeout 180s "${REPO_ROOT}/tools/verify_phase4b_mission_segments.sh"
  run_gate "phase4c_flat_segment_gate" \
    timeout 180s "${REPO_ROOT}/tools/verify_phase4c_flat_segment_gate.sh"
  run_gate "phase4d_route_tracking_feedback" \
    timeout 180s "${REPO_ROOT}/tools/verify_phase4d_route_tracking_feedback.sh"

  source_file_checked "${ROS_SETUP}" "ros_setup"
  run_gate "phase4_packages_build" \
    colcon build --symlink-install --packages-select go2w_navigation go2w_control go2w_mission

  source_file_checked "${REPO_SETUP}" "repo_setup"
  run_gate "phase4_packages_test" \
    colcon test --packages-select go2w_navigation go2w_control go2w_mission
  run_gate "phase4_test_result" \
    colcon test-result --verbose

  print_kv "phase4_runtime_acceptance_result" "PASS"
}

main "$@"
