from pathlib import Path


def test_real_model_route_following_supports_min_planned_path_length() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_real_model_route_following.sh"

    content = script_path.read_text(encoding="utf-8")

    assert "GO2W_REAL_ROUTE_MIN_PLANNED_PATH_LENGTH_M" in content
    assert "real_route_goal_min_planned_path_length_m" in content
    assert "real_route_goal_candidate_" in content
    assert "path_length_m={path_length_m:.3f}<min_planned_path_length_m=" in content
    assert "contract_topic__laser_map" in content


def test_real_model_single_floor_hospital_wrapper_sets_hospital_defaults() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_real_model_single_floor_hospital.sh"

    content = script_path.read_text(encoding="utf-8")

    assert "phase3c_hospital_multifloor_world.sdf" in content
    assert "GO2W_REAL_ROUTE_GOAL_OFFSET_X" in content
    assert "0.600" in content
    assert "GO2W_REAL_ROUTE_MIN_PLANNED_PATH_LENGTH_M" in content
    assert "0.250" in content
    assert "verify_go2w_real_model_route_following.sh" in content
