#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/go2w_mission"

python3 -m py_compile \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_api.py" \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_orchestrator.py" \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_queue_replay.py" \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_task_history.py" \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_workflow_backend.py" \
  "${REPO_ROOT}/go2w_mission/go2w_mission/mission_workflow_policy.py" \
  "${REPO_ROOT}/go2w_mission/test/test_mission_workflow_backend.py"

python3 -m pytest \
  "${REPO_ROOT}/go2w_mission/test/test_mission_workflow_backend.py" \
  -q

printf 'mission_workflow_backend_result: PASS\n'
