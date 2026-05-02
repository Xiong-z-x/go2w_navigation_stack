from pathlib import Path

from go2w_mission.mission_recovery import (
    MissionCheckpoint,
    MissionStateStore,
    build_mission_key,
    is_recoverable_result_code,
    should_resume_checkpoint,
)


def test_build_mission_key_is_stable_for_same_goal() -> None:
    key_a = build_mission_key(
        start_id=100,
        goal_id=202,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
    )
    key_b = build_mission_key(
        start_id=100,
        goal_id=202,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
    )
    key_c = build_mission_key(
        start_id=100,
        goal_id=203,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
    )

    assert key_a == key_b
    assert key_a != key_c


def test_state_store_round_trips_checkpoint(tmp_path: Path) -> None:
    state_file = tmp_path / "mission_state.json"
    store = MissionStateStore(state_file)
    checkpoint = MissionCheckpoint(
        mission_key="100->202:map:graph:deadbeef",
        state="RUNNING",
        start_id=100,
        goal_id=202,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
        segment_summary="flat:300|301;stair:500",
        route_edge_ids=(300, 301, 500),
        next_segment_index=1,
        current_segment_index=0,
        current_segment_type="flat",
        active_owner="flat",
        result_code="MISSION_SUCCEEDED",
        message="mission_running",
        retry_count=1,
        updated_at=1234.5,
    )

    store.save(checkpoint)
    loaded = store.load()

    assert loaded == checkpoint
    assert state_file.exists()

    store.clear()
    assert store.load() is None


def test_resume_checkpoint_requires_matching_non_terminal_state() -> None:
    mission_key = "100->202:map:graph:deadbeef"
    recoverable = MissionCheckpoint(
        mission_key=mission_key,
        state="RECOVERABLE",
        start_id=100,
        goal_id=202,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
        segment_summary="flat:300|301;stair:500",
        route_edge_ids=(300, 301, 500),
        next_segment_index=1,
        current_segment_index=0,
        current_segment_type="flat",
        active_owner="flat",
        result_code="MISSION_TIMEOUT",
        message="flat_timeout",
        retry_count=2,
        updated_at=1234.5,
    )

    terminal = recoverable.with_updates(state="SUCCEEDED")
    other_mission = recoverable.with_updates(mission_key="100->203:map:graph:beefcafe")

    assert should_resume_checkpoint(recoverable, mission_key=mission_key)
    assert not should_resume_checkpoint(terminal, mission_key=mission_key)
    assert not should_resume_checkpoint(other_mission, mission_key=mission_key)
    assert is_recoverable_result_code("MISSION_TIMEOUT")
    assert not is_recoverable_result_code("MISSION_INVALID_GOAL")
