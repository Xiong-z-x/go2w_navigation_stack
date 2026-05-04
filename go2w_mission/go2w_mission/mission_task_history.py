from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELED"})


def build_mission_run_id(mission_key: str, ticket: int, admitted_at: float) -> str:
    timestamp_ms = int(max(0.0, float(admitted_at)) * 1000.0)
    return f"{mission_key}:{int(ticket)}:{timestamp_ms}"


def mission_history_state_for_result(
    *,
    success: bool,
    result_code: str,
) -> str:
    if result_code == "MISSION_CANCELED":
        return "CANCELED"
    if success:
        return "SUCCEEDED"
    return "FAILED"


@dataclass(frozen=True)
class MissionTaskHistoryRecord:
    run_id: str
    mission_key: str
    ticket: int
    queue_position: int
    priority: int
    state: str
    result_code: str
    message: str
    start_id: int
    goal_id: int
    graph_file: str
    route_frame_id: str
    segment_count: int
    segment_summary: str
    admitted_at: float
    activated_at: float
    completed_at: float
    last_command: str
    last_message: str
    updated_at: float

    def with_updates(self, **changes: Any) -> "MissionTaskHistoryRecord":
        return replace(self, **changes)

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mission_key": self.mission_key,
            "ticket": self.ticket,
            "queue_position": self.queue_position,
            "priority": self.priority,
            "state": self.state,
            "result_code": self.result_code,
            "message": self.message,
            "start_id": self.start_id,
            "goal_id": self.goal_id,
            "graph_file": self.graph_file,
            "route_frame_id": self.route_frame_id,
            "segment_count": self.segment_count,
            "segment_summary": self.segment_summary,
            "admitted_at": self.admitted_at,
            "activated_at": self.activated_at,
            "completed_at": self.completed_at,
            "last_command": self.last_command,
            "last_message": self.last_message,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionTaskHistoryRecord":
        return cls(
            run_id=str(data.get("run_id", "")),
            mission_key=str(data.get("mission_key", "")),
            ticket=int(data.get("ticket", -1)),
            queue_position=int(data.get("queue_position", 0)),
            priority=int(data.get("priority", 0)),
            state=str(data.get("state", "FAILED")),
            result_code=str(data.get("result_code", "")),
            message=str(data.get("message", "")),
            start_id=int(data.get("start_id", 0)),
            goal_id=int(data.get("goal_id", 0)),
            graph_file=str(data.get("graph_file", "")),
            route_frame_id=str(data.get("route_frame_id", "")),
            segment_count=int(data.get("segment_count", 0)),
            segment_summary=str(data.get("segment_summary", "")),
            admitted_at=float(data.get("admitted_at", 0.0)),
            activated_at=float(data.get("activated_at", 0.0)),
            completed_at=float(data.get("completed_at", 0.0)),
            last_command=str(data.get("last_command", "")),
            last_message=str(data.get("last_message", "")),
            updated_at=float(data.get("updated_at", 0.0)),
        )


@dataclass(frozen=True)
class MissionTaskHistoryState:
    retention_limit: int
    records: tuple[MissionTaskHistoryRecord, ...]
    last_command: str
    last_message: str
    updated_at: float

    def with_updates(self, **changes: Any) -> "MissionTaskHistoryState":
        return replace(self, **changes)

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def latest_record(self) -> MissionTaskHistoryRecord | None:
        if not self.records:
            return None
        return self.sorted_records()[-1]

    def sorted_records(self) -> tuple[MissionTaskHistoryRecord, ...]:
        return tuple(
            sorted(
                self.records,
                key=lambda record: (
                    record.completed_at,
                    record.updated_at,
                    record.run_id,
                ),
            )
        )

    def append_record(self, record: MissionTaskHistoryRecord) -> "MissionTaskHistoryState":
        records = list(self.records)
        records = [existing for existing in records if existing.run_id != record.run_id]
        records.append(record)
        return self.with_updates(records=tuple(records)).archive_to_limit(
            self.retention_limit
        )

    def archive_to_limit(self, retain_limit: int) -> "MissionTaskHistoryState":
        limit = max(1, int(retain_limit))
        sorted_records = self.sorted_records()
        if len(sorted_records) > limit:
            sorted_records = sorted_records[-limit:]
        return self.with_updates(
            retention_limit=limit,
            records=sorted_records,
        )

    def summary(self) -> str:
        latest = self.latest_record
        if latest is None:
            latest_state = "-"
            latest_result = "-"
            latest_mission = "-"
            latest_run_id = "-"
            latest_priority = "-"
        else:
            latest_state = latest.state
            latest_result = latest.result_code
            latest_mission = latest.mission_key
            latest_run_id = latest.run_id
            latest_priority = latest.priority
        return (
            f"history=records={self.record_count} retain={self.retention_limit} "
            f"latest_state={latest_state} latest_result={latest_result} "
            f"latest_priority={latest_priority} "
            f"latest_mission={latest_mission} latest_run={latest_run_id} "
            f"last_command={self.last_command} "
            f"last_message={self.last_message or '-'}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "retention_limit": self.retention_limit,
            "records": [record.to_dict() for record in self.sorted_records()],
            "last_command": self.last_command,
            "last_message": self.last_message,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionTaskHistoryState":
        return cls(
            retention_limit=max(1, int(data.get("retention_limit", 50))),
            records=tuple(
                MissionTaskHistoryRecord.from_dict(item)
                for item in data.get("records", [])
            ),
            last_command=str(data.get("last_command", "BOOT")),
            last_message=str(data.get("last_message", "")),
            updated_at=float(data.get("updated_at", 0.0)),
        )


def build_initial_task_history_state(
    retention_limit: int,
) -> MissionTaskHistoryState:
    return MissionTaskHistoryState(
        retention_limit=max(1, int(retention_limit)),
        records=(),
        last_command="BOOT",
        last_message="history_ready",
        updated_at=time.time(),
    )


def sanitize_task_history_state_for_runtime(
    state: MissionTaskHistoryState,
    *,
    retention_limit: int,
) -> MissionTaskHistoryState:
    return state.archive_to_limit(retention_limit)


class MissionTaskHistoryStateStore:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    @classmethod
    def default_path(cls) -> Path:
        env_path = os.environ.get("GO2W_MISSION_TASK_HISTORY_STATE_FILE", "").strip()
        if env_path:
            return Path(env_path).expanduser()
        return Path.home() / ".local" / "state" / "go2w" / "mission_task_history.json"

    def load(self) -> MissionTaskHistoryState | None:
        if not self.state_file.exists():
            return None
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        try:
            return MissionTaskHistoryState.from_dict(raw)
        except (TypeError, ValueError):
            return None

    def save(self, state: MissionTaskHistoryState) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), indent=2, sort_keys=True)
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
