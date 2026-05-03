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


@dataclass(frozen=True)
class MissionScheduleSnapshot:
    capacity: int
    active_ticket: int | None
    queued_tickets: tuple[int, ...]


class MissionScheduleGate:
    """Bounded FIFO mission scheduler.

    The gate allows one active mission plus a bounded number of waiting missions.
    It does not persist state; it only controls admission order and cancellation
    while queued.
    """

    def __init__(self, *, capacity: int = 2) -> None:
        self._capacity = max(1, int(capacity))
        self._condition = threading.Condition()
        self._queue: deque[int] = deque()
        self._active_ticket: int | None = None
        self._next_ticket = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    def reserve(self) -> MissionQueueAdmission:
        with self._condition:
            outstanding = len(self._queue) + (1 if self._active_ticket is not None else 0)
            if outstanding >= self._capacity:
                return MissionQueueAdmission(
                    accepted=False,
                    rejected_reason="queue_full",
                )

            ticket = self._next_ticket
            self._next_ticket += 1
            self._queue.append(ticket)
            queue_position = len(self._queue) + (1 if self._active_ticket is not None else 0)
            self._condition.notify_all()
            return MissionQueueAdmission(
                accepted=True,
                ticket=ticket,
                queue_position=queue_position,
                queued=queue_position > 1,
            )

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

                if self._active_ticket is None and self._queue and self._queue[0] == ticket:
                    if not can_activate():
                        self._condition.wait(timeout=poll_timeout_sec)
                        continue
                    self._queue.popleft()
                    self._active_ticket = ticket
                    self._condition.notify_all()
                    return True

                self._condition.wait(timeout=poll_timeout_sec)

    def release(self, ticket: int) -> None:
        with self._condition:
            changed = False
            if self._active_ticket == ticket:
                self._active_ticket = None
                changed = True
            if ticket in self._queue:
                self._queue.remove(ticket)
                changed = True
            if changed:
                self._condition.notify_all()

    def snapshot(self) -> MissionScheduleSnapshot:
        with self._condition:
            return MissionScheduleSnapshot(
                capacity=self._capacity,
                active_ticket=self._active_ticket,
                queued_tickets=tuple(self._queue),
            )

    def _remove_ticket_locked(self, ticket: int) -> bool:
        try:
            self._queue.remove(ticket)
        except ValueError:
            return False
        return True
