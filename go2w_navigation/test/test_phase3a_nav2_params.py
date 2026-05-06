from pathlib import Path


def test_phase3a_nav2_params_use_relaxed_goal_tolerance():
    repo_root = Path(__file__).resolve().parents[2]
    params_path = repo_root / "go2w_navigation" / "config" / "phase3a_nav2_same_floor.yaml"

    content = params_path.read_text(encoding="utf-8")

    assert content.count("xy_goal_tolerance: 0.08") == 2
    assert "xy_goal_tolerance: 0.015" not in content
