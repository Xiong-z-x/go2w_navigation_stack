#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
EVIDENCE_DIR="${GO2W_PHASE4E_STAIR_EVIDENCE_DIR:-/tmp/go2w_phase4e_stair_fixture_$$}"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-$(( ($$ % 80) + 120 ))}"
PARTITION="go2w_phase4e_stair_${$}"
LAUNCH_PID=""
COMMAND_GATE_PID=""
STAIR_EXEC_PID=""
STAIR_EXEC_ARGS=()

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
  terminate_pid "${STAIR_EXEC_PID}" "stair_executor"
  terminate_pid "${COMMAND_GATE_PID}" "command_gate"
  terminate_pid "${LAUNCH_PID}" "real_model_launch"
  "${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true
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
    if [ -n "${LAUNCH_PID}" ] && ! process_group_alive "${LAUNCH_PID}" 2>/dev/null; then
      print_kv "launch" "exited_early"
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

wait_for_text_count() {
  local pattern="$1"
  local file="$2"
  local expected_count="$3"
  local timeout_seconds="$4"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    local count
    count="$(grep -cE "${pattern}" "${file}" 2>/dev/null || true)"
    if [ "${count}" -ge "${expected_count}" ]; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "wait_for_text_count" "timeout:${pattern}:${expected_count}"
  sed -n '1,260p' "${file}" || true
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
        return
      fi
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  print_kv "controller_states_ready" "FAIL"
  sed -n '1,220p' "${output_file}" || true
  exit 2
}

wait_for_node() {
  local node_name="$1"
  local timeout_seconds="$2"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 3s ros2 node list 2>/dev/null | grep -qx "${node_name}"; then
      print_kv "node_${node_name}" "PRESENT"
      return
    fi
    if [ -n "${LAUNCH_PID}" ] && ! process_group_alive "${LAUNCH_PID}" 2>/dev/null; then
      print_kv "launch" "exited_early"
      sed -n '1,260p' "${EVIDENCE_DIR}/real_model_launch.log" || true
      exit 2
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "node_${node_name}" "MISSING"
  sed -n '1,260p' "${EVIDENCE_DIR}/real_model_launch.log" || true
  exit 2
}

wait_for_action() {
  local action_name="$1"
  local timeout_seconds="$2"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if timeout 5s ros2 action list 2>/dev/null | grep -qx "${action_name}"; then
      print_kv "action_${action_name}" "PRESENT"
      return
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  print_kv "action_${action_name}" "MISSING"
  timeout 5s ros2 action list >"${EVIDENCE_DIR}/actions_timeout.txt" 2>&1 || true
  sed -n '1,260p' "${EVIDENCE_DIR}/real_model_launch.log" || true
  exit 2
}

append_override_arg() {
  local env_value="$1"
  local flag_name="$2"
  if [ -n "${env_value}" ]; then
    STAIR_EXEC_ARGS+=("${flag_name}" "${env_value}")
  fi
}

send_stair_goal() {
  local output_file="${EVIDENCE_DIR}/stair_goal.txt"

  if ! timeout 40s python3 - >"${output_file}" 2>&1 <<'PY'
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from go2w_control.action import StairExec


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def wait_future(node: Node, future, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    return future.done()


def main() -> int:
    rclpy.init()
    node = Node("phase4e_stair_fixture_client")
    client = ActionClient(node, StairExec, "/stair_exec")
    try:
        if not client.wait_for_server(timeout_sec=20.0):
            print_kv("stair_fixture_action", "FAIL_UNAVAILABLE")
            return 2

        goal = StairExec.Goal()
        goal.connector_id = "stair_a"
        goal.edge_id = 500
        goal.direction = "F1_to_F2"
        goal.expected_duration_sec = 0.8
        goal.force_fail = False
        goal.force_timeout = False

        send_future = client.send_goal_async(goal)
        if not wait_future(node, send_future, 10.0):
            print_kv("stair_fixture_goal_response", "FAIL_TIMEOUT")
            return 2
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print_kv("stair_fixture_goal_response", "REJECTED")
            return 2

        result_future = goal_handle.get_result_async()
        if not wait_future(node, result_future, 30.0):
            print_kv("stair_fixture_result", "FAIL_TIMEOUT")
            return 2
        wrapped = result_future.result()
        result = wrapped.result
        print_kv("stair_fixture_action_status", wrapped.status)
        print_kv("stair_fixture_result_code", result.result_code)
        print_kv("stair_fixture_success", result.success)
        return 0 if result.success and result.result_code == "SUCCEEDED" else 2
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
PY
  then
    print_kv "stair_fixture_goal" "FAIL"
    sed -n '1,260p' "${output_file}" || true
    exit 2
  fi

  if grep -q "stair_fixture_result_code: SUCCEEDED" "${output_file}"; then
    print_kv "stair_fixture_goal" "PASS"
    return
  fi

  print_kv "stair_fixture_goal" "FAIL_NO_SUCCESS"
  sed -n '1,260p' "${output_file}" || true
  exit 2
}

main() {
  mkdir -p "${EVIDENCE_DIR}"
  export ROS_DOMAIN_ID="${DOMAIN_ID}"
  export GZ_PARTITION="${PARTITION}"

  append_override_arg "${GO2W_STAIR_BODY_HEIGHT_M:-}" "--stair-body-height-m"
  append_override_arg "${GO2W_STAIR_EXECUTE_BODY_HEIGHT_M:-}" "--stair-execute-body-height-m"
  append_override_arg "${GO2W_STAIR_FOOT_RAISE_HEIGHT_M:-}" "--stair-foot-raise-height-m"
  append_override_arg "${GO2W_STAIR_GAIT_TYPE:-}" "--stair-gait-type"
  append_override_arg "${GO2W_STAIR_SPEED_LEVEL:-}" "--stair-speed-level"
  append_override_arg "${GO2W_STAIR_MAX_LINEAR_VELOCITY_MPS:-}" "--stair-max-linear-velocity-mps"
  append_override_arg "${GO2W_STAIR_LINEAR_VELOCITY_MPS:-}" "--stair-linear-velocity-mps"

  EXPECTED_STAIR_BODY_HEIGHT_M="$(printf '%.2f' "${GO2W_STAIR_BODY_HEIGHT_M:-0.32}")"
  DEFAULT_STAIR_EXECUTE_BODY_HEIGHT_M="${GO2W_STAIR_BODY_HEIGHT_M:-0.32}"
  EXPECTED_STAIR_EXECUTE_BODY_HEIGHT_M="$(printf '%.2f' "${GO2W_STAIR_EXECUTE_BODY_HEIGHT_M:-${DEFAULT_STAIR_EXECUTE_BODY_HEIGHT_M}}")"
  EXPECTED_STAIR_FOOT_RAISE_HEIGHT_M="$(printf '%.2f' "${GO2W_STAIR_FOOT_RAISE_HEIGHT_M:-0.09}")"
  EXPECTED_STAIR_GAIT_TYPE="${GO2W_STAIR_GAIT_TYPE:-3}"
  EXPECTED_STAIR_SPEED_LEVEL="${GO2W_STAIR_SPEED_LEVEL:-0}"
  EXPECTED_STAIR_LINEAR_VELOCITY_MPS="$(printf '%.3f' "${GO2W_STAIR_LINEAR_VELOCITY_MPS:-0.025}")"

  print_kv "phase4e_stair_fixture_result" "RUNNING"
  print_kv "evidence_dir" "${EVIDENCE_DIR}"
  print_kv "ros_domain_id" "${ROS_DOMAIN_ID}"
  print_kv "gz_partition" "${GZ_PARTITION}"
  if [ "${#STAIR_EXEC_ARGS[@]}" -gt 0 ]; then
    print_kv "stair_exec_override_args" "${STAIR_EXEC_ARGS[*]}"
  fi

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
    >"${EVIDENCE_DIR}/real_model_launch.log" 2>&1 &
  LAUNCH_PID="$!"

  wait_for_text "ign gazebo-" "${EVIDENCE_DIR}/real_model_launch.log" 25
  wait_for_controller_states_active "${EVIDENCE_DIR}/controllers.txt" 90
  wait_for_text "go2w_stand_initializer_result: PASS motion_mode=legged" "${EVIDENCE_DIR}/real_model_launch.log" 60

  setsid ros2 run go2w_control go2w_command_gate \
    >"${EVIDENCE_DIR}/command_gate.log" 2>&1 &
  COMMAND_GATE_PID="$!"
  setsid ros2 run go2w_control go2w_stair_executor "${STAIR_EXEC_ARGS[@]}" \
    >"${EVIDENCE_DIR}/stair_executor.log" 2>&1 &
  STAIR_EXEC_PID="$!"

  wait_for_node "/go2w_command_gate" 30
  wait_for_node "/go2w_stair_executor" 30
  wait_for_action "/stair_exec" 30

  send_stair_goal

  wait_for_text_count "go2w_command_gate_state: owner=flat mode=wheeled" "${EVIDENCE_DIR}/command_gate.log" 2 30
  wait_for_text "go2w_command_gate_state: owner=stair mode=legged" "${EVIDENCE_DIR}/command_gate.log" 30

  wait_for_text "go2w_stair_executor_profile: .*mode=legged .*body_height_m=${EXPECTED_STAIR_BODY_HEIGHT_M} .*foot_raise_height_m=${EXPECTED_STAIR_FOOT_RAISE_HEIGHT_M} .*gait_type=${EXPECTED_STAIR_GAIT_TYPE} .*speed_level=${EXPECTED_STAIR_SPEED_LEVEL} .*execute_body_height_m=${EXPECTED_STAIR_EXECUTE_BODY_HEIGHT_M} .*stair_linear_velocity_mps=${EXPECTED_STAIR_LINEAR_VELOCITY_MPS}" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_plan: phases=prepare,wheel_lock,body_height_transition_down,execute_stairs,body_height_transition_up,release" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=prepare" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=wheel_lock" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=body_height_transition_down" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=execute_stairs" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=body_height_transition_up" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=release" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=wheel_lock .*wheel_lock_required=true" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=body_height_transition_down .*body_height_m=${EXPECTED_STAIR_EXECUTE_BODY_HEIGHT_M} .*wheel_lock_required=true" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=execute_stairs .*body_height_m=${EXPECTED_STAIR_EXECUTE_BODY_HEIGHT_M} .*wheel_lock_required=true" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=body_height_transition_up .*body_height_m=${EXPECTED_STAIR_BODY_HEIGHT_M} .*wheel_lock_required=true" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=release .*wheel_lock_required=false" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=release .* complete" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=release" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_trajectory: phase=prepare .*trajectory_joint_count=12" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_trajectory: phase=wheel_lock .*trajectory_joint_count=12" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_trajectory: phase=body_height_transition_down .*trajectory_joint_count=12" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_trajectory: phase=execute_stairs .*trajectory_joint_count=12" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_trajectory: phase=body_height_transition_up .*trajectory_joint_count=12" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_trajectory: phase=release .*trajectory_joint_count=12" "${EVIDENCE_DIR}/stair_executor.log" 30
  wait_for_text "go2w_stair_executor_state: phase=execute_stairs .*trajectory_joint_count=12 .*trajectory_checksum=" "${EVIDENCE_DIR}/stair_executor.log" 30

  print_kv "phase4e_stair_fixture_result" "PASS"
}

main "$@"
