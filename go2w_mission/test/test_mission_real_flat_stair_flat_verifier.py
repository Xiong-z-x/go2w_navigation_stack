from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mission_real_flat_stair_flat_verifier_contract() -> None:
    script = REPO_ROOT / "tools" / "verify_go2w_mission_real_flat_stair_flat.sh"
    assert script.exists(), "missing mission real flat/stair/flat verifier"

    content = script.read_text(encoding="utf-8")
    assert "mission_real_flat_stair_flat_result: PASS" in content
    assert "launch_flat_nav_executor:=false" in content
    assert "launch_stair_executor:=true" in content
    assert "route_tracking_action:=/compute_and_track_route" in content
    assert "mission_real_flat_stair_flat_segment_summary: flat:10;stair:500:stair_a:F1->F2;flat:20" in content
    assert "mission_route_tracking_feedback_edge: 10" in content
    assert "mission_route_tracking_feedback_edge: 20" in content
    assert "go2w_stair_executor_state: phase=execute_stairs" in content
    assert "go2w_command_gate_state: owner=stair mode=legged" in content
    assert "post_mission_map_odom" in content
    assert "post_mission_odom_base_link_authority" in content
