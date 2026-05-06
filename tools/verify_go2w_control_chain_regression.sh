#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_kv() {
  printf '%s: %s\n' "$1" "$2"
}

main() {
  print_kv "go2w_control_chain_regression_result" "RUNNING"

  "${SCRIPT_DIR}/verify_go2w_real_model_baseline.sh"
  print_kv "control_chain_regression_baseline" "PASS"

  "${SCRIPT_DIR}/verify_phase4e_stair_fixture.sh"
  print_kv "control_chain_regression_stair_fixture" "PASS"

  "${SCRIPT_DIR}/verify_phase4e_mission_recovery.sh"
  print_kv "control_chain_regression_mission_recovery" "PASS"

  "${SCRIPT_DIR}/verify_phase4e_stair_tuning_overrides.sh"
  print_kv "control_chain_regression_stair_tuning" "PASS"

  "${SCRIPT_DIR}/verify_phase4e_stair_trajectory_outlet.sh"
  print_kv "control_chain_regression_stair_trajectory_outlet" "PASS"

  print_kv "go2w_control_chain_regression_result" "PASS"
}

main "$@"
