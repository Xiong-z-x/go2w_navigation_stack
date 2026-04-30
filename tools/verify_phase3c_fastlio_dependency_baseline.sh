#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_CACHE_ROOT="${GO2W_FASTLIO_CACHE_ROOT:-${REPO_ROOT}/.go2w_external}"
FASTLIO_SRC="${GO2W_FASTLIO_SRC:-${FASTLIO_CACHE_ROOT}/src/FAST_LIO_ROS2}"
FASTLIO_WS="${GO2W_FASTLIO_WS:-${FASTLIO_CACHE_ROOT}/workspaces/fast_lio_ros2}"
LOCK_FILE="${GO2W_FASTLIO_LOCK_FILE:-${REPO_ROOT}/go2w_perception/external/fast_lio_ros2.lock.env}"

set -u

print_kv() {
  printf '%s: %s\n' "$1" "$2"
}

fail() {
  print_kv "phase3c_fastlio_dependency_result" "FAIL"
  print_kv "failure_reason" "$1"
  exit 2
}

path_is_under_tmp() {
  case "$1" in
    /tmp|/tmp/*) return 0 ;;
    *) return 1 ;;
  esac
}

require_file_contains() {
  local file="$1"
  local pattern="$2"
  local key="$3"

  if grep -Eq "${pattern}" "${file}"; then
    print_kv "${key}" "PASS"
    return
  fi
  fail "${key}_missing"
}

printf '# Phase 3C FAST-LIO External Dependency Baseline\n'
print_kv "repo_root" "${REPO_ROOT}"
print_kv "fastlio_lock_file" "${LOCK_FILE}"
print_kv "fastlio_source_path" "${FASTLIO_SRC}"
print_kv "fastlio_workspace_path" "${FASTLIO_WS}"

[ -f "${LOCK_FILE}" ] || fail "lock_file_missing"

require_file_contains "${LOCK_FILE}" '^GO2W_FASTLIO_REF=[0-9a-f]{40}$' "fastlio_ref_pinned_sha"
require_file_contains "${LOCK_FILE}" '^GO2W_IKDTREE_REF=[0-9a-f]{40}$' "ikdtree_ref_pinned_sha"

if path_is_under_tmp "${FASTLIO_SRC}" || path_is_under_tmp "${FASTLIO_WS}"; then
  fail "default_fastlio_paths_must_not_use_tmp"
fi
print_kv "default_fastlio_paths_not_tmp" "PASS"

mkdir -p "${FASTLIO_CACHE_ROOT}"

GO2W_FASTLIO_SKIP_BUILD="${GO2W_FASTLIO_SKIP_BUILD:-1}" \
  "${REPO_ROOT}/tools/prepare_phase2d_fastlio_external.sh" >"${FASTLIO_CACHE_ROOT}/phase3c_fastlio_prepare.log" 2>&1

print_kv "prepare_log" "${FASTLIO_CACHE_ROOT}/phase3c_fastlio_prepare.log"

[ -f "${FASTLIO_SRC}/CMakeLists.txt" ] || fail "fastlio_cmakelists_missing"
[ -f "${FASTLIO_SRC}/src/laserMapping.cpp" ] || fail "fastlio_laser_mapping_missing"
[ -f "${FASTLIO_SRC}/include/ikd-Tree/ikd_Tree.cpp" ] || fail "ikdtree_source_missing"
[ -f "${FASTLIO_SRC}/.go2w_fastlio_provenance.env" ] || fail "provenance_missing"
[ -L "${FASTLIO_WS}/src/FAST_LIO_ROS2" ] || fail "workspace_source_symlink_missing"

"${REPO_ROOT}/tools/check_phase2_fastlio_external.sh" "${FASTLIO_SRC}" >"${FASTLIO_CACHE_ROOT}/phase3c_fastlio_audit.log" 2>&1
print_kv "audit_log" "${FASTLIO_CACHE_ROOT}/phase3c_fastlio_audit.log"

if grep -q '^audit_status: complete$' "${FASTLIO_CACHE_ROOT}/phase3c_fastlio_audit.log"; then
  print_kv "fastlio_external_audit" "PASS"
else
  fail "fastlio_external_audit_failed"
fi

if git ls-files --error-unmatch .go2w_external >/dev/null 2>&1; then
  fail "external_cache_is_tracked"
fi
print_kv "external_cache_untracked" "PASS"

print_kv "phase3c_fastlio_dependency_result" "PASS"
