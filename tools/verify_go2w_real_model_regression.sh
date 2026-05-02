#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_kv() {
  printf '%s: %s\n' "$1" "$2"
}

main() {
  print_kv "go2w_real_model_regression_result" "RUNNING"

  "${SCRIPT_DIR}/verify_go2w_real_model_baseline.sh"
  print_kv "real_model_regression_baseline" "PASS"

  "${SCRIPT_DIR}/verify_go2w_real_model_route_following.sh"
  print_kv "real_model_regression_route_following" "PASS"

  "${SCRIPT_DIR}/verify_phase4e_stair_fixture.sh"
  print_kv "real_model_regression_stair_fixture" "PASS"

  print_kv "go2w_real_model_regression_result" "PASS"
}

main "$@"
