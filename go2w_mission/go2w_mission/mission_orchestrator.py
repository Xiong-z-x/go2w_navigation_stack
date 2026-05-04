from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


OPEN_MODE = "OPEN"
PAUSED_MODE = "PAUSED"


def normalize_orchestrator_mode(mode: str) -> str:
    normalized = str(mode).strip().upper()
    if normalized not in {OPEN_MODE, PAUSED_MODE}:
        return OPEN_MODE
    return normalized


@dataclass(frozen=True)
class MissionOrchestratorState:
    mode: str
    pause_reason: str
    active_mission_key: str
    active_ticket: int
    queue_capacity: int
    queued_tickets: tuple[int, ...]
    last_command: str
    last_message: str
    updated_at: float
    queued_priorities: tuple[tuple[int, int], ...] = ()

    def with_updates(self, **changes: Any) -> "MissionOrchestratorState":
        return replace(self, **changes)

    @property
    def paused(self) -> bool:
        return self.mode == PAUSED_MODE

    def summary(self) -> str:
        queued = ",".join(str(ticket) for ticket in self.queued_tickets) or "-"
        priorities = ",".join(
            f"{ticket}:{priority}"
            for ticket, priority in self.queued_priorities
        ) or "-"
        active_ticket = self.active_ticket if self.active_ticket >= 0 else "-"
        active_mission = self.active_mission_key or "-"
        pause_reason = self.pause_reason or "-"
        return (
            f"mode={self.mode} active_ticket={active_ticket} "
            f"active_mission={active_mission} queued=[{queued}] priorities=[{priorities}] "
            f"capacity={self.queue_capacity} pause_reason={pause_reason} "
            f"last_command={self.last_command} last_message={self.last_message or '-'}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "pause_reason": self.pause_reason,
            "active_mission_key": self.active_mission_key,
            "active_ticket": self.active_ticket,
            "queue_capacity": self.queue_capacity,
            "queued_tickets": list(self.queued_tickets),
            "queued_priorities": [
                {"ticket": ticket, "priority": priority}
                for ticket, priority in self.queued_priorities
            ],
            "last_command": self.last_command,
            "last_message": self.last_message,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionOrchestratorState":
        return cls(
            mode=normalize_orchestrator_mode(data.get("mode", OPEN_MODE)),
            pause_reason=str(data.get("pause_reason", "")),
            active_mission_key=str(data.get("active_mission_key", "")),
            active_ticket=int(data.get("active_ticket", -1)),
            queue_capacity=max(1, int(data.get("queue_capacity", 1))),
            queued_tickets=tuple(
                int(ticket) for ticket in data.get("queued_tickets", [])
            ),
            queued_priorities=tuple(
                (
                    int(item.get("ticket", -1)),
                    int(item.get("priority", 0)),
                )
                for item in data.get("queued_priorities", [])
                if isinstance(item, dict)
            ),
            last_command=str(data.get("last_command", "BOOT")),
            last_message=str(data.get("last_message", "")),
            updated_at=float(data.get("updated_at", 0.0)),
        )


def build_initial_orchestrator_state(queue_capacity: int) -> MissionOrchestratorState:
    return MissionOrchestratorState(
        mode=OPEN_MODE,
        pause_reason="",
        active_mission_key="",
        active_ticket=-1,
        queue_capacity=max(1, int(queue_capacity)),
        queued_tickets=(),
        last_command="BOOT",
        last_message="orchestrator_ready",
        updated_at=time.time(),
        queued_priorities=(),
    )


def sanitize_orchestrator_state_for_runtime(
    state: MissionOrchestratorState,
    *,
    queue_capacity: int,
) -> MissionOrchestratorState:
    return state.with_updates(
        active_mission_key="",
        active_ticket=-1,
        queue_capacity=max(1, int(queue_capacity)),
        queued_tickets=(),
        queued_priorities=(),
    )


class MissionOrchestratorStateStore:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    @classmethod
    def default_path(cls) -> Path:
        env_path = os.environ.get(
            "GO2W_MISSION_ORCHESTRATOR_STATE_FILE", ""
        ).strip()
        if env_path:
            return Path(env_path).expanduser()
        return Path.home() / ".local" / "state" / "go2w" / "mission_orchestrator.json"

    def load(self) -> MissionOrchestratorState | None:
        if not self.state_file.exists():
            return None
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        try:
            return MissionOrchestratorState.from_dict(raw)
        except (TypeError, ValueError):
            return None

    def save(self, state: MissionOrchestratorState) -> None:
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
