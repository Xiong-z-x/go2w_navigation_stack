#!/usr/bin/env bash
set -euo pipefail

collect_target_pids() {
  ps -eo pid=,comm=,args= | awk '
    {
      pid = $1
      comm = $2
      args = $0
      sub(/^[[:space:]]*[0-9]+[[:space:]]+[^[:space:]]+[[:space:]]*/, "", args)
      is_ign_gazebo = args ~ /(^|[[:space:]\/])ign[[:space:]]+gazebo(-[0-9]+)?([[:space:]]|$)/
      is_gz_sim = args ~ /(^|[[:space:]\/])gz[[:space:]]+sim([[:space:]]|$)/
      is_rviz = comm == "rviz2" || args ~ /(^|[[:space:]\/])rviz2([[:space:]]|$)/
      is_go2w_launch = args ~ /(^|[[:space:]\/])ros2[[:space:]]+launch[[:space:]]+go2w_sim[[:space:]]+sim\.launch\.py([[:space:]]|$)/
      if (pid ~ /^[0-9]+$/ && (is_ign_gazebo || is_gz_sim || is_rviz || is_go2w_launch)) {
        print pid
      }
    }
  '
}

load_target_pids() {
  local target_array_name="$1"
  local pid_output
  if ! pid_output="$(collect_target_pids)"; then
    echo "[FAIL] failed to collect go2w_sim runtime processes" >&2
    return 1
  fi
  if [[ -z "${pid_output}" ]]; then
    eval "${target_array_name}=()"
    return 0
  fi
  mapfile -t "${target_array_name}" <<<"${pid_output}"
}

terminate_signal() {
  local signal_name="$1"
  shift
  local pid
  for pid in "$@"; do
    kill "-${signal_name}" "${pid}" 2>/dev/null || true
  done
}

main() {
  local pids
  load_target_pids pids
  if [[ "${#pids[@]}" -eq 0 ]]; then
    echo "[INFO] no stale go2w_sim runtime processes found"
    return 0
  fi

  echo "[INFO] terminating stale processes: ${pids[*]}"
  terminate_signal TERM "${pids[@]}"
  sleep 2

  local remaining
  load_target_pids remaining
  if [[ "${#remaining[@]}" -gt 0 ]]; then
    echo "[WARN] escalating to SIGKILL for: ${remaining[*]}"
    terminate_signal KILL "${remaining[@]}"
  fi

  echo "[INFO] runtime cleanup complete"
}

main "$@"
