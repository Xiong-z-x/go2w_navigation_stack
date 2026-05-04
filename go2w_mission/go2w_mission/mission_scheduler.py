from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import threading
from typing import Callable


@dataclass(frozen=True)
class MissionQueueAdmission:
    accepted: bool
    ticket: int = -1
    queue_position: int = 0
    queued: bool = False
    rejected_reason: str = ""
    priority: int = 0


@dataclass(frozen=True)
class MissionScheduleSnapshot:
    capacity: int
    active_ticket: int | None
    queued_tickets: tuple[int, ...]
    active_priority: int = 0
    queued_priorities: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class MissionQueueEntry:
    ticket: int
    priority: int


class MissionScheduleGate:
    """Bounded FIFO mission scheduler.

    The gate allows one active mission plus a bounded number of waiting missions.
    It does not persist state; it only controls admission order and cancellation
    while queued.
    """

    def __init__(self, *, capacity: int = 2) -> None:
        self._capacity = max(1, int(capacity))
        self._condition = threading.Condition()
        self._queue: deque[MissionQueueEntry] = deque()
        self._active_ticket: int | None = None
        self._active_priority = 0
        self._next_ticket = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    def reserve(self, *, priority: int = 0) -> MissionQueueAdmission:
        with self._condition:
            outstanding = len(self._queue) + (1 if self._active_ticket is not None else 0)
            if outstanding >= self._capacity:
                return MissionQueueAdmission(
                    accepted=False,
                    rejected_reason="queue_full",
                )

            ticket = self._next_ticket
            self._next_ticket += 1
            entry = MissionQueueEntry(ticket=ticket, priority=int(priority))
            self._queue.append(entry)
            ordered_queue = self._ordered_queue_locked()
            queue_position = (
                ordered_queue.index(entry)
                + 1
                + (1 if self._active_ticket is not None else 0)
            )
            self._condition.notify_all()
            return MissionQueueAdmission(
                accepted=True,
                ticket=ticket,
                queue_position=queue_position,
                queued=queue_position > 1,
                priority=entry.priority,
            )

    def restore(
        self,
        *,
        active_ticket: int | None,
        queued_tickets: tuple[int, ...],
        next_ticket: int | None = None,
        ticket_priorities: dict[int, int] | None = None,
        active_priority: int = 0,
    ) -> None:
        with self._condition:
            priorities = ticket_priorities or {}
            filtered_tickets = tuple(
                ticket for ticket in queued_tickets if ticket != active_ticket
            )
            self._queue = deque(
                MissionQueueEntry(
                    ticket=ticket,
                    priority=int(priorities.get(ticket, 0)),
                )
                for ticket in filtered_tickets
            )
            self._active_ticket = active_ticket if active_ticket is not None and active_ticket >= 0 else None
            self._active_priority = int(active_priority) if self._active_ticket is not None else 0
            restored_candidates = [ticket for ticket in filtered_tickets]
            if self._active_ticket is not None:
                restored_candidates.append(self._active_ticket)
            if next_ticket is None:
                if restored_candidates:
                    self._next_ticket = max(self._next_ticket, max(restored_candidates) + 1)
            else:
                self._next_ticket = max(
                    self._next_ticket,
                    int(next_ticket),
                    (max(restored_candidates) + 1) if restored_candidates else 0,
                )
            self._condition.notify_all()

    def wait_for_turn(
        self,
        ticket: int,
        cancel_requested,
        *,
        can_activate=None,
        poll_timeout_sec: float = 0.1,
    ) -> bool:
        if can_activate is None:
            can_activate = lambda: True
        with self._condition:
            while True:
                if self._active_ticket == ticket:
                    return True

                if cancel_requested():
                    removed = self._remove_ticket_locked(ticket)
                    if removed:
                        self._condition.notify_all()
                    return False

                ordered_queue = self._ordered_queue_locked()
                if self._active_ticket is None and ordered_queue and ordered_queue[0].ticket == ticket:
                    if not can_activate():
                        self._condition.wait(timeout=poll_timeout_sec)
                        continue
                    entry = ordered_queue[0]
                    self._remove_ticket_locked(entry.ticket)
                    self._active_ticket = ticket
                    self._active_priority = entry.priority
                    self._condition.notify_all()
                    return True

                self._condition.wait(timeout=poll_timeout_sec)

    def release(self, ticket: int) -> None:
        with self._condition:
            changed = False
            if self._active_ticket == ticket:
                self._active_ticket = None
                self._active_priority = 0
                changed = True
            if self._remove_ticket_locked(ticket):
                changed = True
            if changed:
                self._condition.notify_all()

    def snapshot(self) -> MissionScheduleSnapshot:
        with self._condition:
            return MissionScheduleSnapshot(
                capacity=self._capacity,
                active_ticket=self._active_ticket,
                queued_tickets=tuple(entry.ticket for entry in self._ordered_queue_locked()),
                active_priority=self._active_priority,
                queued_priorities=tuple(
                    (entry.ticket, entry.priority)
                    for entry in self._ordered_queue_locked()
                ),
            )

    def _remove_ticket_locked(self, ticket: int) -> bool:
        for entry in tuple(self._queue):
            if entry.ticket == ticket:
                self._queue.remove(entry)
                return True
        return False

    def _ordered_queue_locked(self) -> tuple[MissionQueueEntry, ...]:
        return tuple(sorted(self._queue, key=lambda entry: (-entry.priority, entry.ticket)))
