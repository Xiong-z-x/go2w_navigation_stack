#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
REPO_SETUP="${REPO_ROOT}/install/setup.bash"
FASTLIO_SETUP="${REPO_ROOT}/.go2w_external/workspaces/fast_lio_ros2/install/setup.bash"
DOMAIN_ID="${GO2W_VERIFY_DOMAIN_ID:-208}"
PARTITION="${GO2W_REAL_HOSPITAL_DEMO_PARTITION:-go2w_real_hospital_demo}"

source "${ROS_SETUP}"
source "${REPO_SETUP}"
source "${FASTLIO_SETUP}"

export ROS_DOMAIN_ID="${DOMAIN_ID}"
export GZ_PARTITION="${PARTITION}"

printf 'repo_root: %s\n' "${REPO_ROOT}"
printf 'ros_domain_id: %s\n' "${ROS_DOMAIN_ID}"
printf 'gz_partition: %s\n' "${GZ_PARTITION}"
printf 'demo_launch: go2w_navigation real_model_single_floor_hospital_demo.launch.py\n'

"${REPO_ROOT}/tools/cleanup_sim_runtime.sh" >/dev/null 2>&1 || true

exec ros2 launch go2w_navigation real_model_single_floor_hospital_demo.launch.py
