#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTLIO_SRC="${GO2W_FASTLIO_SRC:-/tmp/fast_lio_ros2_probe}"
FASTLIO_WS="${GO2W_FASTLIO_WS:-/tmp/go2w_phase2d_fastlio_ws}"
FASTLIO_REF="${GO2W_FASTLIO_REF:-ros2}"
IKDTREE_REF="${GO2W_IKDTREE_REF:-fast_lio}"
FASTLIO_REPO_URL="${GO2W_FASTLIO_REPO_URL:-https://github.com/Ericsii/FAST_LIO_ROS2.git}"
FASTLIO_ARCHIVE_URL="${GO2W_FASTLIO_ARCHIVE_URL:-https://github.com/Ericsii/FAST_LIO_ROS2/archive/refs/heads/${FASTLIO_REF}.tar.gz}"
IKDTREE_REPO_URL="${GO2W_IKDTREE_REPO_URL:-https://github.com/hku-mars/ikd-Tree.git}"
FORCE_REFRESH="${GO2W_FASTLIO_FORCE_REFRESH:-0}"
FORCE_REBUILD="${GO2W_FASTLIO_REBUILD:-0}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
BUILD_LOG="${FASTLIO_WS}/phase2d_fastlio_build.log"
FASTLIO_EXE="${FASTLIO_WS}/install/fast_lio/lib/fast_lio/fastlio_mapping"

set -u

print_kv() {
  printf '%s: %s\n' "$1" "$2"
}

source_ros() {
  if [ ! -f "${ROS_SETUP}" ]; then
    print_kv "ros_setup" "missing:${ROS_SETUP}"
    exit 2
  fi
  set +u
  # shellcheck source=/dev/null
  source "${ROS_SETUP}"
  set -u
}

remote_head() {
  local repo_url="$1"
  local ref_name="$2"
  git ls-remote --heads "${repo_url}" "refs/heads/${ref_name}" 2>/dev/null | awk '{print $1}' | head -n 1
}

source_is_valid() {
  [ -f "${FASTLIO_SRC}/CMakeLists.txt" ] \
    && [ -f "${FASTLIO_SRC}/src/laserMapping.cpp" ] \
    && [ -f "${FASTLIO_SRC}/include/ikd-Tree/ikd_Tree.cpp" ] \
    && [ -f "${FASTLIO_SRC}/include/ikd-Tree/ikd_Tree.h" ]
}

acquire_fastlio_source() {
  local tmp_dir
  local extracted_dir
  tmp_dir="$(mktemp -d)"

  print_kv "source_acquisition" "download_archive"
  rm -rf "${FASTLIO_SRC}"
  mkdir -p "$(dirname "${FASTLIO_SRC}")"

  curl --fail --location --connect-timeout 20 --max-time 180 "${FASTLIO_ARCHIVE_URL}" \
    | tar -xz -C "${tmp_dir}"

  extracted_dir="$(find "${tmp_dir}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  if [ -z "${extracted_dir}" ]; then
    print_kv "source_acquisition_status" "archive_empty"
    exit 2
  fi

  mv "${extracted_dir}" "${FASTLIO_SRC}"
  rm -rf "${tmp_dir}"
  rm -rf "${FASTLIO_SRC}/include/ikd-Tree"
  git clone --depth 1 --branch "${IKDTREE_REF}" "${IKDTREE_REPO_URL}" "${FASTLIO_SRC}/include/ikd-Tree"

  print_kv "source_acquisition_status" "downloaded"
}

ensure_source() {
  if [ "${FORCE_REFRESH}" != "1" ] && source_is_valid; then
    print_kv "source_acquisition" "reused_existing"
    return
  fi

  acquire_fastlio_source
}

ensure_build_workspace() {
  local existing_link

  if [ "${FORCE_REBUILD}" != "1" ] && [ -x "${FASTLIO_EXE}" ]; then
    existing_link="$(readlink -f "${FASTLIO_WS}/src/FAST_LIO_ROS2" 2>/dev/null || true)"
    if [ "${existing_link}" = "$(readlink -f "${FASTLIO_SRC}")" ]; then
      print_kv "fastlio_build_status" "reused_existing"
      return
    fi
  fi

  rm -rf "${FASTLIO_WS}"
  mkdir -p "${FASTLIO_WS}/src"
  ln -s "${FASTLIO_SRC}" "${FASTLIO_WS}/src/FAST_LIO_ROS2"

  source_ros

  print_kv "fastlio_build_status" "building"
  (
    cd "${FASTLIO_WS}"
    colcon build --symlink-install --packages-select fast_lio --cmake-args -DFAST_LIO_ENABLE_LIVOX=OFF
  ) 2>&1 | tee "${BUILD_LOG}"

  if [ ! -x "${FASTLIO_EXE}" ]; then
    print_kv "fastlio_mapping_executable" "missing"
    exit 2
  fi

  print_kv "fastlio_build_status" "PASS"
}

printf '# Phase 2D FAST-LIO2 External Preparation\n'
print_kv "repo_root" "${REPO_ROOT}"
print_kv "fastlio_source_path" "${FASTLIO_SRC}"
print_kv "fastlio_workspace_path" "${FASTLIO_WS}"
print_kv "fastlio_ref" "${FASTLIO_REF}"
print_kv "ikdtree_ref" "${IKDTREE_REF}"
print_kv "fastlio_remote_head" "$(remote_head "${FASTLIO_REPO_URL}" "${FASTLIO_REF}" || printf 'unknown')"
print_kv "ikdtree_remote_head" "$(remote_head "${IKDTREE_REPO_URL}" "${IKDTREE_REF}" || printf 'unknown')"

ensure_source

"${REPO_ROOT}/tools/apply_phase2c_fastlio_patch.sh" "${FASTLIO_SRC}"
"${REPO_ROOT}/tools/check_phase2_fastlio_external.sh" "${FASTLIO_SRC}"

ensure_build_workspace

print_kv "fastlio_mapping_executable" "present"
print_kv "build_log" "${BUILD_LOG}"
print_kv "prepare_status" "complete"
