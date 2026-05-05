from __future__ import annotations

from dataclasses import dataclass

from go2w_mission.mission_orchestrator import (
    PAUSED_MODE,
    MissionOrchestratorState,
)
from go2w_mission.mission_queue_replay import MissionQueueReplayState
from go2w_mission.mission_task_history import MissionTaskHistoryState


@dataclass(frozen=True)
class MissionWorkflowSnapshot:
    mode: str
    active_mission_key: str
    active_ticket: int
    queued_tickets: tuple[int, ...]
    queue_replay_pending: bool
    queue_replay_record_count: int
    task_history_record_count: int

    @property
    def mission_state(self) -> str:
        return "ACTIVE" if self.active_mission_key else "IDLE"

    @property
    def queue_state(self) -> str:
        if self.queue_replay_pending:
            return "REPLAY_PENDING"
        if self.queued_tickets:
            return "QUEUED"
        return "EMPTY"

    @property
    def history_state(self) -> str:
        return "READY" if self.task_history_record_count > 0 else "EMPTY"

    @property
    def available_commands(self) -> tuple[str, ...]:
        commands = ["status", "workflow", "workflow_events", "history"]
        if self.mode == PAUSED_MODE:
            commands.append("resume")
        else:
            commands.append("pause")
        if self.active_mission_key:
            commands.append("cancel_active")
        if self.queue_replay_pending and self.queue_replay_record_count > 0:
            commands.append("replay_queue")
        if self.task_history_record_count > 0:
            commands.append("archive_history")
        return tuple(commands)

    def summary(self) -> str:
        active_ticket = self.active_ticket if self.active_ticket >= 0 else "-"
        active_mission = self.active_mission_key or "-"
        queued = ",".join(str(ticket) for ticket in self.queued_tickets) or "-"
        commands = ",".join(self.available_commands) or "-"
        return (
            f"workflow=mode={self.mode} mission={self.mission_state} "
            f"queue={self.queue_state} history={self.history_state} "
            f"active_ticket={active_ticket} active_mission={active_mission} "
            f"queued=[{queued}] available=[{commands}]"
        )


def build_mission_workflow_snapshot(
    orchestrator_state: MissionOrchestratorState,
    queue_replay_state: MissionQueueReplayState,
    task_history_state: MissionTaskHistoryState,
) -> MissionWorkflowSnapshot:
    active_ticket = orchestrator_state.active_ticket
    if active_ticket < 0:
        active_ticket = queue_replay_state.active_ticket

    queued_tickets = tuple(orchestrator_state.queued_tickets)
    if not queued_tickets:
        queued_tickets = tuple(queue_replay_state.queued_tickets)

    return MissionWorkflowSnapshot(
        mode=orchestrator_state.mode,
        active_mission_key=orchestrator_state.active_mission_key,
        active_ticket=active_ticket,
        queued_tickets=queued_tickets,
        queue_replay_pending=queue_replay_state.queue_replay_pending,
        queue_replay_record_count=queue_replay_state.record_count,
        task_history_record_count=task_history_state.record_count,
    )
