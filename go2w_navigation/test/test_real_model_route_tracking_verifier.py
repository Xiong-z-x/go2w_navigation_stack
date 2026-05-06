from pathlib import Path


def test_real_model_route_tracking_verifier_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_real_model_route_tracking.sh"

    assert script_path.exists(), f"missing verifier script: {script_path}"

    content = script_path.read_text(encoding="utf-8")
    assert "sim_go2w_real.launch.py" in content
    assert "phase5_real_model_nav2_same_floor.yaml" in content
    assert "phase3b_route_server.yaml" in content
    assert "ComputeAndTrackRoute" in content
    assert "NavigateToPose" in content
    assert "/compute_and_track_route" in content
    assert "/route_server/set_route_graph" in content
    assert "real_route_tracking_graph_result: PASS" in content
    assert "real_route_tracking_feedback_result: PASS" in content
    assert "real_route_tracking_goal_result: PASS" in content
    assert "go2w_real_model_route_tracking_result" in content
    assert "/go2w/perception/odom" in content
    assert "/diff_drive_controller/odom" in content


def test_real_model_route_tracking_verifier_keeps_tf_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_go2w_real_model_route_tracking.sh"

    assert script_path.exists(), f"missing verifier script: {script_path}"

    content = script_path.read_text(encoding="utf-8")
    assert "require_tf_edge_present \"odom_base_link_authority\" odom base_link" in content
    assert "require_tf_edge_absent \"pre_nav2_map_odom\" map odom" in content
    assert "require_tf_edge_absent \"post_tracking_map_odom\" map odom" in content
    assert "enable_odom_tf" in content
