from pathlib import Path


def test_real_model_route_following_verifier_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_real_model_route_following.sh"

    assert script_path.exists(), f"missing verifier script: {script_path}"

    content = script_path.read_text(encoding="utf-8")
    assert "sim_go2w_real.launch.py" in content
    assert "phase5_real_model_nav2_same_floor.yaml" in content
    assert "NavigateToPose" in content
    assert "go2w_real_model_route_following_result" in content
    assert "/diff_drive_controller/odom" in content
    assert "/go2w/perception/odom" in content


def test_real_model_route_following_prefers_first_reachable_candidate():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_real_model_route_following.sh"

    content = script_path.read_text(encoding="utf-8")
    assert "real_route_goal_selection_policy: first_reachable_in_preference_order" in content
    assert "selected_candidate is None" in content
    assert "score = (path_length_m, path_pose_count)" not in content


def test_real_model_route_following_cleans_stale_perception_and_fastlio_processes():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_real_model_route_following.sh"

    content = script_path.read_text(encoding="utf-8")
    assert "GO2W_REAL_ROUTE_CLEAN_STALE_PROCESSES" in content
    assert "cleanup_stale_route_processes" in content
    assert "phase2f_tf_authority.launch.py" in content
    assert "fastlio_mapping" in content
    assert "sim_go2w_real.launch.py" in content
    assert "collect_matching_pgids" in content
