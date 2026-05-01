cmake_minimum_required(VERSION 3.8)
project(go2w_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  config
  dae
  launch
  rviz
  urdf
  DESTINATION share/${PROJECT_NAME}
)

install(FILES
  UNITREE_MODEL_LICENSE.txt
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_pytest_test(test_go2w_real_model test/test_go2w_real_model.py)
endif()

ament_package()
