from pathlib import Path


def test_phase3a_verifier_prefers_first_reachable_candidate():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_phase3a_nav2_same_floor.sh"

    content = script_path.read_text(encoding="utf-8")

    assert "ComputePathToPose" in content
    assert "phase3a_goal_selection_policy: first_reachable_in_preference_order" in content
    assert 'selected_candidate is None' in content


def test_phase3a_verifier_cleans_stale_process_groups_and_supports_params_override():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "verify_phase3a_nav2_same_floor.sh"

    content = script_path.read_text(encoding="utf-8")

    assert "GO2W_PHASE3A_NAV2_PARAMS_FILE" in content
    assert "cleanup_stale_phase3a_processes" in content
    assert "collect_matching_pgids" in content
    assert 'params_file:="${NAV2_PARAMS_FILE}"' in content
