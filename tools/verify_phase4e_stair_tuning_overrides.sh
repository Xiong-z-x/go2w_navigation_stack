#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_kv() {
  printf '%s: %s\n' "$1" "$2"
}

main() {
  print_kv "phase4e_stair_tuning_overrides_result" "RUNNING"

  GO2W_STAIR_BODY_HEIGHT_M="${GO2W_STAIR_BODY_HEIGHT_M:-0.31}" \
  GO2W_STAIR_FOOT_RAISE_HEIGHT_M="${GO2W_STAIR_FOOT_RAISE_HEIGHT_M:-0.08}" \
  GO2W_STAIR_GAIT_TYPE="${GO2W_STAIR_GAIT_TYPE:-3}" \
  GO2W_STAIR_SPEED_LEVEL="${GO2W_STAIR_SPEED_LEVEL:-1}" \
  GO2W_STAIR_MAX_LINEAR_VELOCITY_MPS="${GO2W_STAIR_MAX_LINEAR_VELOCITY_MPS:-0.12}" \
  GO2W_STAIR_LINEAR_VELOCITY_MPS="${GO2W_STAIR_LINEAR_VELOCITY_MPS:-0.02}" \
    "${SCRIPT_DIR}/verify_phase4e_stair_fixture.sh"

  print_kv "phase4e_stair_tuning_overrides_result" "PASS"
}

main "$@"
