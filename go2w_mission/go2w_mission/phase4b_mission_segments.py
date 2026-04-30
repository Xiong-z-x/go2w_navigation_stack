from __future__ import annotations

from dataclasses import dataclass

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph, RouteEdge


@dataclass(frozen=True)
class MissionSegment:
    segment_type: str
    edge_ids: tuple[int, ...]
    connector_id: str = ""
    floor_from: str = ""
    floor_to: str = ""


def build_mission_segments(
    graph: Phase4ARouteGraph,
    edge_ids: list[int],
) -> list[MissionSegment]:
    segments: list[MissionSegment] = []
    flat_buffer: list[int] = []

    def flush_flat() -> None:
        if flat_buffer:
            segments.append(MissionSegment(segment_type="flat", edge_ids=tuple(flat_buffer)))
            flat_buffer.clear()

    for edge_id in edge_ids:
        edge = graph.edges.get(edge_id)
        if edge is None:
            raise ValueError(f"missing_route_edge:{edge_id}")
        if edge.is_stair_required:
            flush_flat()
            segments.append(_stair_segment(edge))
            continue
        flat_buffer.append(edge_id)

    flush_flat()
    return segments


def _stair_segment(edge: RouteEdge) -> MissionSegment:
    return MissionSegment(
        segment_type="stair",
        edge_ids=(edge.edge_id,),
        connector_id=str(edge.properties.get("connector_id", "")),
        floor_from=str(edge.properties.get("floor_from", "")),
        floor_to=str(edge.properties.get("floor_to", "")),
    )


def classify_stair_result(result_code: str) -> str:
    if result_code == "SUCCEEDED":
        return "MISSION_SUCCEEDED"
    if result_code == "CANCELED":
        return "MISSION_CANCELED"
    return "MISSION_FAILED"
