#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"

print_kv() {
  printf '%s: %s\n' "$1" "$2"
}

if [ ! -f "${ROS_SETUP}" ]; then
  print_kv "ros_setup" "missing:${ROS_SETUP}"
  exit 2
fi

set +u
# shellcheck source=/dev/null
source "${ROS_SETUP}"
set -u

export PYTHONPATH="${REPO_ROOT}/go2w_control:${PYTHONPATH:-}"

python3 -m py_compile \
  "${REPO_ROOT}/go2w_control/go2w_control_runtime/stair_executor.py" \
  "${REPO_ROOT}/go2w_control/go2w_control_runtime/motion_profiles.py" \
  "${REPO_ROOT}/go2w_control/test/test_stair_executor_policy.py" \
  "${REPO_ROOT}/go2w_control/test/test_stair_executor_phases.py"

python3 -m pytest \
  "${REPO_ROOT}/go2w_control/test/test_stair_executor_policy.py" \
  "${REPO_ROOT}/go2w_control/test/test_stair_executor_phases.py" \
  -q

python3 - <<'PY'
from go2w_control_runtime.stair_executor import (
    StairExecutionPolicy,
    build_stair_phase_trajectory_command_data,
    summarize_stair_phase_trajectory,
)


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


policy = StairExecutionPolicy(execute_body_height_m=0.29)
plan = policy.build_phase_plan(0.5, force_timeout=False)

for phase in plan.phases:
    command_data = build_stair_phase_trajectory_command_data(phase, policy.profile)
    if len(command_data) != 12:
        print_kv(f"stair_trajectory_phase_{phase.name}", "FAIL_BAD_JOINT_COUNT")
        raise SystemExit(2)
    summary = summarize_stair_phase_trajectory(phase, policy.profile)
    print_kv(f"stair_trajectory_phase_{phase.name}", summary)

print_kv("phase4e_stair_trajectory_outlet_result", "PASS")
PY
