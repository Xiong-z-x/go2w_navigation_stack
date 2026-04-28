#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FASTLIO_SRC="${1:-${GO2W_FASTLIO_SRC:-/tmp/fast_lio_ros2_probe}}"
PATCH_FILE="${REPO_ROOT}/go2w_perception/patches/fast_lio_ros2/phase2c_no_livox_no_tf.patch"

printf '# Phase 2C FAST-LIO2 Patch Apply\n'
printf 'repo_root: %s\n' "${REPO_ROOT}"
printf 'fastlio_source_path: %s\n' "${FASTLIO_SRC}"
printf 'patch_file: %s\n' "${PATCH_FILE}"

if [ ! -d "${FASTLIO_SRC}" ]; then
  printf 'patch_status: source_missing\n'
  exit 2
fi

if [ ! -f "${FASTLIO_SRC}/CMakeLists.txt" ] || [ ! -f "${FASTLIO_SRC}/src/laserMapping.cpp" ]; then
  printf 'patch_status: invalid_fastlio_source\n'
  exit 2
fi

if [ ! -f "${PATCH_FILE}" ]; then
  printf 'patch_status: patch_missing\n'
  exit 2
fi

if grep -q 'FAST_LIO_ENABLE_LIVOX' "${FASTLIO_SRC}/CMakeLists.txt" \
  && grep -q 'publish.tf_publish_en' "${FASTLIO_SRC}/src/laserMapping.cpp"; then
  printf 'patch_status: already_applied\n'
  exit 0
fi

if git -C "${FASTLIO_SRC}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "${FASTLIO_SRC}" apply --check "${PATCH_FILE}"
  git -C "${FASTLIO_SRC}" apply "${PATCH_FILE}"
else
  (
    cd "${FASTLIO_SRC}"
    patch -p1 --forward < "${PATCH_FILE}"
  )
fi

printf 'patch_status: applied\n'
