#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/go2w_mission"

python3 -m py_compile \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_api.py" \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_scheduler.py" \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_task_history.py" \
  "${REPO_ROOT}/go2w_mission/test/test_mission_scheduling_policy.py"

python3 -m pytest \
  "${REPO_ROOT}/go2w_mission/test/test_mission_scheduling_policy.py" \
  -k "task_history or history" \
  -q

printf 'mission_task_history_result: PASS\n'
