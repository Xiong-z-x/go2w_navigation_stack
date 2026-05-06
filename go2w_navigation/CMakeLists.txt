cmake_minimum_required(VERSION 3.8)
project(go2w_navigation)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(go2w_navigation_runtime)

install(DIRECTORY
  behavior_trees
  config
  graphs
  launch
  maps
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/go2w_flat_nav_executor
  scripts/go2w_rviz_goal_bridge
  scripts/go2w_route_tracking_feedback_executor
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_pytest_test(test_phase4c_flat_nav_executor test/test_phase4c_flat_nav_executor.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_phase4d_route_tracking_feedback_executor test/test_phase4d_route_tracking_feedback_executor.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_real_model_route_following_verifier test/test_real_model_route_following_verifier.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_real_model_route_tracking_verifier test/test_real_model_route_tracking_verifier.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_rviz_goal_bridge_demo test/test_rviz_goal_bridge_demo.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
endif()

ament_package()
