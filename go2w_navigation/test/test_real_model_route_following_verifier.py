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
