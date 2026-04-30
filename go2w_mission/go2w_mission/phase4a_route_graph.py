from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RouteNode:
    node_id: int
    x: float
    y: float
    properties: dict[str, Any]


@dataclass(frozen=True)
class RouteEdge:
    edge_id: int
    start_id: int
    end_id: int
    coordinates: list[tuple[float, float]]
    properties: dict[str, Any]

    @property
    def is_stair_required(self) -> bool:
        return (
            self.properties.get("mode") == "stair"
            and bool(self.properties.get("stair_exec_required"))
            and bool(self.properties.get("connector_id"))
        )


class Phase4ARouteGraph:
    def __init__(self, nodes: dict[int, RouteNode], edges: dict[int, RouteEdge]) -> None:
        self.nodes = nodes
        self.edges = edges

    @classmethod
    def from_file(cls, path: str | Path) -> "Phase4ARouteGraph":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes: dict[int, RouteNode] = {}
        edges: dict[int, RouteEdge] = {}
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            if geometry.get("type") == "Point":
                node_id = int(props["id"])
                x, y = geometry["coordinates"][:2]
                nodes[node_id] = RouteNode(node_id, float(x), float(y), dict(props))
            elif geometry.get("type") == "MultiLineString":
                edge_id = int(props["id"])
                coords = [
                    (float(point[0]), float(point[1]))
                    for point in geometry["coordinates"][0]
                ]
                edges[edge_id] = RouteEdge(
                    edge_id=edge_id,
                    start_id=int(props["startid"]),
                    end_id=int(props["endid"]),
                    coordinates=coords,
                    properties=dict(props),
                )
        return cls(nodes=nodes, edges=edges)

    def geometry_mismatches(self) -> list[str]:
        mismatches: list[str] = []
        for edge in self.edges.values():
            start = self.nodes[edge.start_id]
            end = self.nodes[edge.end_id]
            if edge.coordinates[0] != (start.x, start.y):
                mismatches.append(f"edge_{edge.edge_id}_start")
            if edge.coordinates[-1] != (end.x, end.y):
                mismatches.append(f"edge_{edge.edge_id}_end")
        return mismatches

    def stair_edges_for_ids(self, edge_ids: list[int]) -> list[RouteEdge]:
        return [
            self.edges[edge_id]
            for edge_id in edge_ids
            if edge_id in self.edges and self.edges[edge_id].is_stair_required
        ]
