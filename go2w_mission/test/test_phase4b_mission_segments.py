from pathlib import Path

import pytest

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph
from go2w_mission.phase4b_mission_segments import (
    MissionSegment,
    build_mission_segments,
    classify_stair_result,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = (
    REPO_ROOT
    / "go2w_navigation"
    / "graphs"
    / "phase3c_hospital_multifloor_route.geojson"
)


def _graph() -> Phase4ARouteGraph:
    return Phase4ARouteGraph.from_file(GRAPH_PATH)


def test_route_with_stair_edge_splits_into_flat_stair_flat() -> None:
    segments = build_mission_segments(_graph(), [300, 301, 500, 400, 401])

    assert segments == [
        MissionSegment(segment_type="flat", edge_ids=(300, 301)),
        MissionSegment(
            segment_type="stair",
            edge_ids=(500,),
            connector_id="stair_a",
            floor_from="F1",
            floor_to="F2",
        ),
        MissionSegment(segment_type="flat", edge_ids=(400, 401)),
    ]


def test_flat_only_route_remains_one_flat_segment() -> None:
    segments = build_mission_segments(_graph(), [300, 302])

    assert segments == [MissionSegment(segment_type="flat", edge_ids=(300, 302))]


def test_missing_edge_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing_route_edge:999"):
        build_mission_segments(_graph(), [300, 999])


def test_stair_result_classification() -> None:
    assert classify_stair_result("SUCCEEDED") == "MISSION_SUCCEEDED"
    assert classify_stair_result("FAILED") == "MISSION_FAILED"
    assert classify_stair_result("CANCELED") == "MISSION_CANCELED"
    assert classify_stair_result("OTHER") == "MISSION_FAILED"
