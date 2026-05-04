from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


QUEUED_STATE = "QUEUED"
ACTIVE_STATE = "ACTIVE"


@dataclass(frozen=True)
class MissionQueueRecord:
    mission_key: str
    ticket: int
    queue_position: int
    priority: int
    state: str
    start_id: int
    goal_id: int
    graph_file: str
    route_frame_id: str
    expected_stair_duration_sec: float
    result_timeout_sec: float
    flat_result_timeout_sec: float
    last_command: str
    last_message: str
    admitted_at: float
    updated_at: float

    def with_updates(self, **changes: Any) -> "MissionQueueRecord":
        return replace(self, **changes)

    @property
    def is_outstanding(self) -> bool:
        return self.state in {QUEUED_STATE, ACTIVE_STATE}

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_key": self.mission_key,
            "ticket": self.ticket,
            "queue_position": self.queue_position,
            "priority": self.priority,
            "state": self.state,
            "start_id": self.start_id,
            "goal_id": self.goal_id,
            "graph_file": self.graph_file,
            "route_frame_id": self.route_frame_id,
            "expected_stair_duration_sec": self.expected_stair_duration_sec,
            "result_timeout_sec": self.result_timeout_sec,
            "flat_result_timeout_sec": self.flat_result_timeout_sec,
            "last_command": self.last_command,
            "last_message": self.last_message,
            "admitted_at": self.admitted_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionQueueRecord":
        return cls(
            mission_key=str(data.get("mission_key", "")),
            ticket=int(data.get("ticket", -1)),
            queue_position=int(data.get("queue_position", 0)),
            priority=int(data.get("priority", 0)),
            state=str(data.get("state", QUEUED_STATE)),
            start_id=int(data.get("start_id", 0)),
            goal_id=int(data.get("goal_id", 0)),
            graph_file=str(data.get("graph_file", "")),
            route_frame_id=str(data.get("route_frame_id", "")),
            expected_stair_duration_sec=float(
                data.get("expected_stair_duration_sec", 0.0)
            ),
            result_timeout_sec=float(data.get("result_timeout_sec", 0.0)),
            flat_result_timeout_sec=float(data.get("flat_result_timeout_sec", 0.0)),
            last_command=str(data.get("last_command", "")),
            last_message=str(data.get("last_message", "")),
            admitted_at=float(data.get("admitted_at", 0.0)),
            updated_at=float(data.get("updated_at", 0.0)),
        )


@dataclass(frozen=True)
class MissionQueueReplayState:
    queue_replay_pending: bool
    queue_capacity: int
    next_ticket: int
    records: tuple[MissionQueueRecord, ...]
    last_command: str
    last_message: str
    updated_at: float

    def with_updates(self, **changes: Any) -> "MissionQueueReplayState":
        return replace(self, **changes)

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def active_ticket(self) -> int:
        for record in self.sorted_records():
            if record.state == ACTIVE_STATE:
                return record.ticket
        return -1

    @property
    def queued_tickets(self) -> tuple[int, ...]:
        return tuple(
            record.ticket
            for record in self.sorted_queued_records()
            if record.state == QUEUED_STATE
        )

    def sorted_records(self) -> tuple[MissionQueueRecord, ...]:
        return tuple(sorted(self.records, key=lambda record: record.ticket))

    def sorted_queued_records(self) -> tuple[MissionQueueRecord, ...]:
        return tuple(
            sorted(
                (record for record in self.records if record.state == QUEUED_STATE),
                key=lambda record: (-record.priority, record.ticket),
            )
        )

    def ticket_priorities(self) -> dict[int, int]:
        return {record.ticket: record.priority for record in self.records}

    def find_record(self, mission_key: str) -> MissionQueueRecord | None:
        for record in self.records:
            if record.mission_key == mission_key:
                return record
        return None

    def upsert_record(self, record: MissionQueueRecord) -> "MissionQueueReplayState":
        records = [existing for existing in self.records if existing.mission_key != record.mission_key]
        records.append(record)
        return self.with_updates(
            next_ticket=max(self.next_ticket, record.ticket + 1),
            records=tuple(sorted(records, key=lambda item: item.ticket)),
        )

    def remove_record(self, mission_key: str) -> "MissionQueueReplayState":
        records = tuple(
            record for record in self.records if record.mission_key != mission_key
        )
        return self.with_updates(records=records)

    def summary(self) -> str:
        queued = ",".join(str(ticket) for ticket in self.queued_tickets) or "-"
        priorities = ",".join(
            f"{record.ticket}:{record.priority}"
            for record in self.sorted_queued_records()
        ) or "-"
        active_ticket = self.active_ticket if self.active_ticket >= 0 else "-"
        replay_status = "PENDING" if self.queue_replay_pending else "ACKED"
        return (
            f"replay={replay_status} records={self.record_count} "
            f"active_ticket={active_ticket} queued=[{queued}] priorities=[{priorities}] "
            f"capacity={self.queue_capacity} next_ticket={self.next_ticket} "
            f"last_command={self.last_command} last_message={self.last_message or '-'}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_replay_pending": self.queue_replay_pending,
            "queue_capacity": self.queue_capacity,
            "next_ticket": self.next_ticket,
            "records": [record.to_dict() for record in self.sorted_records()],
            "last_command": self.last_command,
            "last_message": self.last_message,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionQueueReplayState":
        return cls(
            queue_replay_pending=bool(data.get("queue_replay_pending", False)),
            queue_capacity=max(1, int(data.get("queue_capacity", 1))),
            next_ticket=max(0, int(data.get("next_ticket", 0))),
            records=tuple(
                MissionQueueRecord.from_dict(item) for item in data.get("records", [])
            ),
            last_command=str(data.get("last_command", "BOOT")),
            last_message=str(data.get("last_message", "")),
            updated_at=float(data.get("updated_at", 0.0)),
        )


def build_initial_queue_replay_state(
    queue_capacity: int,
) -> MissionQueueReplayState:
    return MissionQueueReplayState(
        queue_replay_pending=False,
        queue_capacity=max(1, int(queue_capacity)),
        next_ticket=0,
        records=(),
        last_command="BOOT",
        last_message="queue_ready",
        updated_at=time.time(),
    )


def sanitize_queue_replay_state_for_runtime(
    state: MissionQueueReplayState,
    *,
    queue_capacity: int,
) -> MissionQueueReplayState:
    sorted_records = tuple(sorted(state.records, key=lambda record: record.ticket))
    next_ticket = max(
        max((record.ticket for record in sorted_records), default=-1) + 1,
        max(0, int(state.next_ticket)),
    )
    return state.with_updates(
        queue_capacity=max(1, int(queue_capacity)),
        next_ticket=next_ticket,
        records=sorted_records,
    )


class MissionQueueReplayStateStore:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    @classmethod
    def default_path(cls) -> Path:
        env_path = os.environ.get(
            "GO2W_MISSION_QUEUE_REPLAY_STATE_FILE", ""
        ).strip()
        if env_path:
            return Path(env_path).expanduser()
        return Path.home() / ".local" / "state" / "go2w" / "mission_queue_replay.json"

    def load(self) -> MissionQueueReplayState | None:
        if not self.state_file.exists():
            return None
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        try:
            return MissionQueueReplayState.from_dict(raw)
        except (TypeError, ValueError):
            return None

    def save(self, state: MissionQueueReplayState) -> None:
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
