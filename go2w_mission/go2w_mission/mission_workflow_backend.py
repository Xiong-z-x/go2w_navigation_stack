from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


@dataclass(frozen=True)
class MissionWorkflowEvent:
    event_id: int
    event_type: str
    mission_key: str
    ticket: int
    mode: str
    message: str
    created_at: float

    def normalized(self) -> "MissionWorkflowEvent":
        return replace(
            self,
            event_id=max(0, int(self.event_id)),
            event_type=str(self.event_type).strip().upper() or "EVENT",
            mission_key=str(self.mission_key).strip(),
            ticket=int(self.ticket),
            mode=str(self.mode).strip().upper() or "OPEN",
            message=str(self.message).strip(),
            created_at=float(self.created_at),
        )

    def to_dict(self) -> dict[str, Any]:
        event = self.normalized()
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "mission_key": event.mission_key,
            "ticket": event.ticket,
            "mode": event.mode,
            "message": event.message,
            "created_at": event.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionWorkflowEvent":
        return cls(
            event_id=int(data.get("event_id", 0)),
            event_type=str(data.get("event_type", "EVENT")),
            mission_key=str(data.get("mission_key", "")),
            ticket=int(data.get("ticket", -1)),
            mode=str(data.get("mode", "OPEN")),
            message=str(data.get("message", "")),
            created_at=float(data.get("created_at", 0.0)),
        ).normalized()


@dataclass(frozen=True)
class MissionWorkflowEventState:
    retention_limit: int
    next_event_id: int
    events: tuple[MissionWorkflowEvent, ...]
    last_command: str
    last_message: str
    updated_at: float

    def with_updates(self, **changes: Any) -> "MissionWorkflowEventState":
        return replace(self, **changes)

    @property
    def record_count(self) -> int:
        return len(self.events)

    @property
    def latest_event(self) -> MissionWorkflowEvent | None:
        if not self.events:
            return None
        return self.events[-1]

    def append_event(
        self,
        event: MissionWorkflowEvent,
    ) -> "MissionWorkflowEventState":
        normalized_event = event.normalized()
        retention_limit = max(1, int(self.retention_limit))
        retained_events = (*self.events, normalized_event)[-retention_limit:]
        return self.with_updates(
            retention_limit=retention_limit,
            next_event_id=max(
                int(self.next_event_id),
                normalized_event.event_id + 1,
            ),
            events=retained_events,
            last_command=normalized_event.event_type,
            last_message=normalized_event.message,
            updated_at=normalized_event.created_at,
        )

    def archive_to_limit(self, retention_limit: int) -> "MissionWorkflowEventState":
        normalized_limit = max(1, int(retention_limit))
        return self.with_updates(
            retention_limit=normalized_limit,
            events=self.events[-normalized_limit:],
        )

    def summary(self) -> str:
        latest = self.latest_event
        if latest is None:
            latest_type = "-"
            latest_ticket = "-"
            latest_mission = "-"
        else:
            latest_type = latest.event_type
            latest_ticket = latest.ticket if latest.ticket >= 0 else "-"
            latest_mission = latest.mission_key or "-"
        return (
            f"workflow_backend=events={self.record_count} "
            f"retain={self.retention_limit} latest={latest_type} "
            f"latest_ticket={latest_ticket} latest_mission={latest_mission} "
            f"last_command={self.last_command} "
            f"last_message={self.last_message or '-'}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "retention_limit": self.retention_limit,
            "next_event_id": self.next_event_id,
            "events": [event.to_dict() for event in self.events],
            "last_command": self.last_command,
            "last_message": self.last_message,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionWorkflowEventState":
        retention_limit = max(1, int(data.get("retention_limit", 100)))
        events = tuple(
            MissionWorkflowEvent.from_dict(item)
            for item in data.get("events", [])
            if isinstance(item, dict)
        )
        events = events[-retention_limit:]
        next_event_id = max(
            int(data.get("next_event_id", 0)),
            max((event.event_id for event in events), default=-1) + 1,
        )
        return cls(
            retention_limit=retention_limit,
            next_event_id=next_event_id,
            events=events,
            last_command=str(data.get("last_command", "BOOT")),
            last_message=str(data.get("last_message", "")),
            updated_at=float(data.get("updated_at", 0.0)),
        )


def build_initial_workflow_event_state(
    retention_limit: int,
) -> MissionWorkflowEventState:
    return MissionWorkflowEventState(
        retention_limit=max(1, int(retention_limit)),
        next_event_id=0,
        events=(),
        last_command="BOOT",
        last_message="workflow_backend_ready",
        updated_at=time.time(),
    )


def sanitize_workflow_event_state_for_runtime(
    state: MissionWorkflowEventState,
    *,
    retention_limit: int,
) -> MissionWorkflowEventState:
    return state.archive_to_limit(retention_limit).with_updates(
        last_command="BOOT",
        last_message="workflow_backend_ready",
        updated_at=time.time(),
    )


class MissionWorkflowEventStateStore:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    @classmethod
    def default_path(cls) -> Path:
        env_path = os.environ.get(
            "GO2W_MISSION_WORKFLOW_EVENTS_FILE", ""
        ).strip()
        if env_path:
            return Path(env_path).expanduser()
        return Path.home() / ".local" / "state" / "go2w" / "mission_workflow_events.json"

    def load(self) -> MissionWorkflowEventState | None:
        if not self.state_file.exists():
            return None
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        try:
            return MissionWorkflowEventState.from_dict(raw)
        except (TypeError, ValueError):
            return None

    def save(self, state: MissionWorkflowEventState) -> None:
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
