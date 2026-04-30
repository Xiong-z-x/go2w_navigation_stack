cmake_minimum_required(VERSION 3.8)
project(go2w_navigation)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  behavior_trees
  config
  graphs
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
