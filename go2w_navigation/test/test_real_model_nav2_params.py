from pathlib import Path


def test_real_model_nav2_params_tighten_footprint():
    repo_root = Path(__file__).resolve().parents[2]
    params_path = repo_root / "go2w_navigation" / "config" / "phase5_real_model_nav2_same_floor.yaml"

    assert params_path.exists(), f"missing nav2 params file: {params_path}"

    content = params_path.read_text(encoding="utf-8")
    assert "robot_radius: 0.28" in content
    assert "footprint_padding: 0.01" in content
    assert content.count("origin_z: -0.40") == 2
    assert content.count("z_voxels: 16") == 2
