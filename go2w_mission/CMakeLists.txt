cmake_minimum_required(VERSION 3.8)
project(go2w_mission)

find_package(ament_cmake REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(rosidl_default_generators REQUIRED)

set(PYTHON_INSTALL_DIR lib/python${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}/site-packages)

install(DIRECTORY go2w_mission
  DESTINATION ${PYTHON_INSTALL_DIR}
  FILES_MATCHING
  PATTERN "*.py"
  PATTERN "__pycache__" EXCLUDE
)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/RunMission.action"
  "srv/MissionControl.srv"
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/go2w_phase4a_handoff_demo
  scripts/go2w_phase4b_mission_runtime
  scripts/go2w_phase4d_route_tracking_observer
  scripts/go2w_phase5a_live_route_tracking
  scripts/go2w_mission_api
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_pytest_test(test_phase4a_route_graph test/test_phase4a_route_graph.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_phase4a_handoff_demo test/test_phase4a_handoff_demo.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_phase4b_mission_segments test/test_phase4b_mission_segments.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_phase4b_mission_runtime test/test_phase4b_mission_runtime.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_mission_api_skeleton test/test_mission_api_skeleton.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_mission_scheduling_policy test/test_mission_scheduling_policy.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_mission_workflow_policy test/test_mission_workflow_policy.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_mission_assignment_policy test/test_mission_assignment_policy.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_mission_recovery test/test_mission_recovery.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_phase4d_route_tracking_observer test/test_phase4d_route_tracking_observer.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  ament_add_pytest_test(test_phase5a_live_route_tracking test/test_phase5a_live_route_tracking.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
endif()

ament_export_dependencies(rosidl_default_runtime)

ament_package()
