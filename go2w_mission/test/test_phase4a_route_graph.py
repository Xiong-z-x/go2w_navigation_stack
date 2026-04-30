from pathlib import Path

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph


REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = (
    REPO_ROOT
    / "go2w_navigation"
    / "graphs"
    / "phase3c_hospital_multifloor_route.geojson"
)


def test_phase3c_graph_edges_match_node_coordinates() -> None:
    graph = Phase4ARouteGraph.from_file(GRAPH_PATH)

    assert graph.geometry_mismatches() == []


def test_phase3c_route_100_to_202_contains_stair_exec_edge() -> None:
    graph = Phase4ARouteGraph.from_file(GRAPH_PATH)

    stair_edges = graph.stair_edges_for_ids([300, 301, 500, 400, 401])

    assert [edge.edge_id for edge in stair_edges] == [500]
    assert stair_edges[0].properties["connector_id"] == "stair_a"
    assert stair_edges[0].properties["floor_from"] == "F1"
    assert stair_edges[0].properties["floor_to"] == "F2"
