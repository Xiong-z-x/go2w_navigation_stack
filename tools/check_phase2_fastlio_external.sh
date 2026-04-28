#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FASTLIO_SRC="${1:-${GO2W_FASTLIO_SRC:-/tmp/fast_lio_ros2_probe}}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"

if [ -f "${ROS_SETUP}" ]; then
  # Source ROS before enabling nounset; ROS setup scripts may reference unset vars.
  # shellcheck source=/opt/ros/humble/setup.bash
  source "${ROS_SETUP}"
fi

set -u

has_pattern() {
  local pattern="$1"
  shift
  if command -v rg >/dev/null 2>&1; then
    rg -q "${pattern}" "$@" 2>/dev/null
  else
    grep -R -E -q "${pattern}" "$@" 2>/dev/null
  fi
}

print_presence() {
  local key="$1"
  local pattern="$2"
  shift 2
  if has_pattern "${pattern}" "$@"; then
    printf '%s: present\n' "${key}"
  else
    printf '%s: missing\n' "${key}"
  fi
}

print_livox_cmake_status() {
  local cmake_file="$1"
  if has_pattern 'FAST_LIO_ENABLE_LIVOX' "${cmake_file}"; then
    printf 'fastlio_livox_build_option: present\n'
    if has_pattern 'if\(FAST_LIO_ENABLE_LIVOX\)' "${cmake_file}" \
      && has_pattern 'find_package\(livox_ros_driver2 REQUIRED\)' "${cmake_file}"; then
      printf 'fastlio_livox_dependency_cmake: optional_gated\n'
    else
      printf 'fastlio_livox_dependency_cmake: ambiguous\n'
    fi
  else
    printf 'fastlio_livox_build_option: missing\n'
    if has_pattern 'find_package\(livox_ros_driver2 REQUIRED\)' "${cmake_file}"; then
      printf 'fastlio_livox_dependency_cmake: required_unconditional\n'
    else
      printf 'fastlio_livox_dependency_cmake: missing\n'
    fi
  fi
}

print_tf_gate_status() {
  local source_file="$1"
  local has_send=false
  local has_param=false
  local has_default_false=false
  local has_guard=false

  if has_pattern 'sendTransform' "${source_file}"; then
    has_send=true
  fi
  if has_pattern 'publish\.tf_publish_en' "${source_file}"; then
    has_param=true
  fi
  if has_pattern 'declare_parameter<bool>\("publish\.tf_publish_en",[[:space:]]*false\)' "${source_file}"; then
    has_default_false=true
  fi
  if has_pattern 'if[[:space:]]*\([[:space:]]*tf_publish_en[[:space:]]*&&[[:space:]]*tf_br[[:space:]]*\)' "${source_file}"; then
    has_guard=true
  fi

  printf 'fastlio_tf_sendtransform: %s\n' "$([ "${has_send}" = true ] && printf present || printf missing)"
  printf 'fastlio_tf_gate_parameter: %s\n' "$([ "${has_param}" = true ] && printf present || printf missing)"
  printf 'fastlio_tf_default_disabled: %s\n' "$([ "${has_default_false}" = true ] && printf present || printf missing)"
  printf 'fastlio_tf_sendtransform_guard: %s\n' "$([ "${has_guard}" = true ] && printf present || printf missing)"

  printf 'fastlio_no_tf_dryrun_gate: '
  if [ "${has_send}" = false ]; then
    printf 'candidate_no_tf_sender_absent\n'
  elif [ "${has_param}" = true ] && [ "${has_default_false}" = true ] && [ "${has_guard}" = true ]; then
    printf 'candidate_gated_default_off\n'
  else
    printf 'blocked_by_source_tf_broadcaster\n'
  fi
}

print_ros_package() {
  local package="$1"
  if command -v ros2 >/dev/null 2>&1 && ros2 pkg prefix "${package}" >/dev/null 2>&1; then
    printf 'ros_package_%s: present\n' "${package}"
  else
    printf 'ros_package_%s: missing\n' "${package}"
  fi
}

printf '# Phase 2 FAST-LIO2 External Audit\n'
printf 'repo_root: %s\n' "${REPO_ROOT}"
printf 'fastlio_source_path: %s\n' "${FASTLIO_SRC}"

if [ ! -d "${FASTLIO_SRC}" ]; then
  printf 'fastlio_source_present: false\n'
  printf 'audit_status: source_missing\n'
  exit 2
fi

printf 'fastlio_source_present: true\n'

if git -C "${FASTLIO_SRC}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf 'fastlio_git_remote: %s\n' "$(git -C "${FASTLIO_SRC}" remote get-url origin 2>/dev/null || printf 'unknown')"
  printf 'fastlio_git_branch: %s\n' "$(git -C "${FASTLIO_SRC}" branch --show-current 2>/dev/null || printf 'unknown')"
  printf 'fastlio_git_commit: %s\n' "$(git -C "${FASTLIO_SRC}" rev-parse HEAD)"
else
  printf 'fastlio_git_remote: unknown\n'
  printf 'fastlio_git_branch: unknown\n'
  printf 'fastlio_git_commit: unknown\n'
fi

print_ros_package fast_lio
print_ros_package livox_ros_driver2
print_ros_package pcl_ros
print_ros_package pcl_conversions

print_presence fastlio_project_declared 'project\(fast_lio\)' "${FASTLIO_SRC}/CMakeLists.txt"
print_presence fastlio_executable_declared 'add_executable\(fastlio_mapping' "${FASTLIO_SRC}/CMakeLists.txt"
print_livox_cmake_status "${FASTLIO_SRC}/CMakeLists.txt"
print_presence fastlio_livox_dependency_package '<depend>livox_ros_driver2</depend>' "${FASTLIO_SRC}/package.xml"
print_presence fastlio_pointcloud2_subscription 'sensor_msgs::msg::PointCloud2' "${FASTLIO_SRC}/src/laserMapping.cpp"
print_presence fastlio_livox_custom_subscription 'livox_ros_driver2::msg::CustomMsg' "${FASTLIO_SRC}/src/laserMapping.cpp"
if [ -f "${FASTLIO_SRC}/include/ikd-Tree/ikd_Tree.cpp" ] && [ -f "${FASTLIO_SRC}/include/ikd-Tree/ikd_Tree.h" ]; then
  printf 'fastlio_ikdtree_submodule_source: present\n'
else
  printf 'fastlio_ikdtree_submodule_source: missing\n'
fi
print_presence fastlio_tf_broadcaster_declared 'tf2_ros::TransformBroadcaster' "${FASTLIO_SRC}/src/laserMapping.cpp"
print_presence fastlio_tf_parent_camera_init 'frame_id[[:space:]]*=[[:space:]]*"camera_init"' "${FASTLIO_SRC}/src/laserMapping.cpp"
print_presence fastlio_tf_child_body 'child_frame_id[[:space:]]*=[[:space:]]*"body"' "${FASTLIO_SRC}/src/laserMapping.cpp"
print_tf_gate_status "${FASTLIO_SRC}/src/laserMapping.cpp"

printf 'fastlio_output_topic_cloud_registered: '
if has_pattern '"/cloud_registered"' "${FASTLIO_SRC}/src/laserMapping.cpp"; then
  printf 'present\n'
else
  printf 'missing\n'
fi

printf 'fastlio_output_topic_cloud_registered_body: '
if has_pattern '"/cloud_registered_body"' "${FASTLIO_SRC}/src/laserMapping.cpp"; then
  printf 'present\n'
else
  printf 'missing\n'
fi

printf 'fastlio_output_topic_laser_map: '
if has_pattern '"/Laser_map"' "${FASTLIO_SRC}/src/laserMapping.cpp"; then
  printf 'present\n'
else
  printf 'missing\n'
fi

printf 'fastlio_output_topic_odometry: '
if has_pattern '"/Odometry"' "${FASTLIO_SRC}/src/laserMapping.cpp"; then
  printf 'present\n'
else
  printf 'missing\n'
fi

printf 'audit_status: complete\n'
