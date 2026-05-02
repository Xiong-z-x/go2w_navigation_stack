from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha1
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


RECOVERABLE_RESULT_CODES = frozenset(
    {
        "MISSION_TIMEOUT",
        "MISSION_ROUTE_UNAVAILABLE",
        "MISSION_FLAT_NAV_UNAVAILABLE",
        "MISSION_FLAT_FAILED",
        "MISSION_STAIR_UNAVAILABLE",
        "MISSION_STAIR_FAILED",
        "MISSION_BUSY",
    }
)

TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELED"})


def build_mission_key(
    *,
    start_id: int,
    goal_id: int,
    graph_file: str,
    route_frame_id: str,
) -> str:
    normalized_graph = Path(graph_file).expanduser().as_posix()
    digest = sha1(
        f"{start_id}|{goal_id}|{normalized_graph}|{route_frame_id.strip()}".encode(
            "utf-8"
        )
    ).hexdigest()[:8]
    graph_tag = Path(normalized_graph).name or "graph"
    return f"{start_id}->{goal_id}:{route_frame_id.strip()}:{graph_tag}:{digest}"


def is_recoverable_result_code(result_code: str) -> bool:
    return result_code in RECOVERABLE_RESULT_CODES


def is_terminal_state(state: str) -> bool:
    return state in TERMINAL_STATES


@dataclass(frozen=True)
class MissionCheckpoint:
    mission_key: str
    state: str
    start_id: int
    goal_id: int
    graph_file: str
    route_frame_id: str
    segment_summary: str
    route_edge_ids: tuple[int, ...]
    next_segment_index: int
    current_segment_index: int
    current_segment_type: str
    active_owner: str
    result_code: str
    message: str
    retry_count: int
    updated_at: float

    def with_updates(self, **changes: Any) -> "MissionCheckpoint":
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_key": self.mission_key,
            "state": self.state,
            "start_id": self.start_id,
            "goal_id": self.goal_id,
            "graph_file": self.graph_file,
            "route_frame_id": self.route_frame_id,
            "segment_summary": self.segment_summary,
            "route_edge_ids": list(self.route_edge_ids),
            "next_segment_index": self.next_segment_index,
            "current_segment_index": self.current_segment_index,
            "current_segment_type": self.current_segment_type,
            "active_owner": self.active_owner,
            "result_code": self.result_code,
            "message": self.message,
            "retry_count": self.retry_count,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionCheckpoint":
        return cls(
            mission_key=str(data.get("mission_key", "")),
            state=str(data.get("state", "")),
            start_id=int(data.get("start_id", 0)),
            goal_id=int(data.get("goal_id", 0)),
            graph_file=str(data.get("graph_file", "")),
            route_frame_id=str(data.get("route_frame_id", "")),
            segment_summary=str(data.get("segment_summary", "")),
            route_edge_ids=tuple(int(value) for value in data.get("route_edge_ids", [])),
            next_segment_index=int(data.get("next_segment_index", 0)),
            current_segment_index=int(data.get("current_segment_index", 0)),
            current_segment_type=str(data.get("current_segment_type", "")),
            active_owner=str(data.get("active_owner", "")),
            result_code=str(data.get("result_code", "")),
            message=str(data.get("message", "")),
            retry_count=int(data.get("retry_count", 0)),
            updated_at=float(data.get("updated_at", 0.0)),
        )


def should_resume_checkpoint(
    checkpoint: MissionCheckpoint | None,
    *,
    mission_key: str,
) -> bool:
    if checkpoint is None:
        return False
    if checkpoint.mission_key != mission_key:
        return False
    if is_terminal_state(checkpoint.state):
        return False
    return checkpoint.state in {"RUNNING", "RECOVERABLE", "SEGMENT_ACTIVE"}


def checkpoint_for_goal(
    *,
    mission_key: str,
    state: str,
    start_id: int,
    goal_id: int,
    graph_file: str,
    route_frame_id: str,
    segment_summary: str,
    route_edge_ids: tuple[int, ...],
    next_segment_index: int,
    current_segment_index: int,
    current_segment_type: str,
    active_owner: str,
    result_code: str,
    message: str,
    retry_count: int,
) -> MissionCheckpoint:
    return MissionCheckpoint(
        mission_key=mission_key,
        state=state,
        start_id=start_id,
        goal_id=goal_id,
        graph_file=graph_file,
        route_frame_id=route_frame_id,
        segment_summary=segment_summary,
        route_edge_ids=route_edge_ids,
        next_segment_index=next_segment_index,
        current_segment_index=current_segment_index,
        current_segment_type=current_segment_type,
        active_owner=active_owner,
        result_code=result_code,
        message=message,
        retry_count=retry_count,
        updated_at=time.time(),
    )


class MissionStateStore:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    @classmethod
    def default_path(cls) -> Path:
        env_path = os.environ.get("GO2W_MISSION_STATE_FILE", "").strip()
        if env_path:
            return Path(env_path).expanduser()
        return Path.home() / ".local" / "state" / "go2w" / "mission_state.json"

    def load(self) -> MissionCheckpoint | None:
        if not self.state_file.exists():
            return None
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        try:
            return MissionCheckpoint.from_dict(raw)
        except (TypeError, ValueError):
            return None

    def save(self, checkpoint: MissionCheckpoint) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(checkpoint.to_dict(), indent=2, sort_keys=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.state_file.parent,
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.write("\n")
            temp_path = Path(handle.name)
        os.replace(temp_path, self.state_file)

    def clear(self) -> None:
        try:
            self.state_file.unlink()
        except FileNotFoundError:
            return

