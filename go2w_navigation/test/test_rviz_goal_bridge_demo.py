from pathlib import Path


def test_rviz_goal_bridge_runtime_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    runtime_path = repo_root / "go2w_navigation" / "go2w_navigation_runtime" / "rviz_goal_bridge.py"

    content = runtime_path.read_text(encoding="utf-8")

    assert "/move_base_simple/goal" in content
    assert "NavigateToPose" in content
    assert "canceling_active_goal_for_new_rviz_goal" in content


def test_hospital_demo_launch_references_real_model_chain() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    launch_path = repo_root / "go2w_navigation" / "launch" / "real_model_single_floor_hospital_demo.launch.py"

    content = launch_path.read_text(encoding="utf-8")

    assert "sim_go2w_real.launch.py" in content
    assert "phase3c_hospital_multifloor_world.sdf" in content
    assert "phase2d_fastlio_sim.yaml" in content
    assert "phase5_real_model_nav2_same_floor.yaml" in content
    assert "go2w_rviz_goal_bridge" in content


def test_hospital_demo_rviz_config_shows_point_cloud_and_plans() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    rviz_path = repo_root / "go2w_description" / "rviz" / "go2w_real_hospital_nav.rviz"

    content = rviz_path.read_text(encoding="utf-8")

    assert "/go2w/perception/cloud_registered" in content
    assert "/go2w/perception/laser_map" in content
    assert "/plan" in content
    assert "/local_plan" in content
    assert "/move_base_simple/goal" in content
