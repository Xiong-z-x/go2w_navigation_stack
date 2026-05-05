#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/go2w_control"

python3 -m py_compile \
  "${REPO_ROOT}/go2w_control/go2w_control_runtime/stair_executor.py" \
  "${REPO_ROOT}/go2w_control/go2w_control_runtime/motion_profiles.py" \
  "${REPO_ROOT}/go2w_control/test/test_stair_executor_policy.py" \
  "${REPO_ROOT}/go2w_control/test/test_stair_executor_phases.py"

python3 -m pytest \
  "${REPO_ROOT}/go2w_control/test/test_stair_executor_policy.py" \
  "${REPO_ROOT}/go2w_control/test/test_stair_executor_phases.py" \
  -q

printf 'phase4e_stair_phase_targets_result: PASS\n'
