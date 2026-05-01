from go2w_mission.phase4a_route_graph import Phase4ARouteGraph, RouteNode
from go2w_mission.phase5a_live_route_tracking import build_route_pose_samples


def test_build_route_pose_samples_uses_graph_coordinates_in_order() -> None:
    graph = Phase4ARouteGraph(
        nodes={
            100: RouteNode(node_id=100, x=0.0, y=0.0, properties={"id": 100}),
            101: RouteNode(node_id=101, x=1.5, y=0.0, properties={"id": 101}),
            102: RouteNode(node_id=102, x=3.0, y=0.0, properties={"id": 102}),
        },
        edges={},
    )

    samples = build_route_pose_samples(graph, [100, 101, 102], hold_sec=0.25)

    assert [sample.node_id for sample in samples] == [100, 101, 102]
    assert [(sample.x, sample.y) for sample in samples] == [
        (0.0, 0.0),
        (1.5, 0.0),
        (3.0, 0.0),
    ]
    assert all(sample.hold_sec == 0.25 for sample in samples)
