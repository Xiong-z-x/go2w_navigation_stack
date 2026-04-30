cmake_minimum_required(VERSION 3.8)
project(go2w_control)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

ament_python_install_package(go2w_control_runtime)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/StairExec.action"
  DEPENDENCIES builtin_interfaces
)

install(PROGRAMS
  scripts/go2w_command_gate
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_pytest_test(test_command_gate test/test_command_gate.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
endif()

ament_export_dependencies(rosidl_default_runtime)

ament_package()
