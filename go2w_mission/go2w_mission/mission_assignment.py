from __future__ import annotations

from dataclasses import dataclass


DEFAULT_MISSION_ROBOT_ID = "go2w_local"


def normalize_robot_id(robot_id: str) -> str:
    normalized = str(robot_id).strip()
    return normalized or DEFAULT_MISSION_ROBOT_ID


@dataclass(frozen=True)
class MissionAssignmentDecision:
    accepted: bool
    local_robot_id: str
    assigned_robot_id: str
    message: str

    def summary(self) -> str:
        accepted = "true" if self.accepted else "false"
        return (
            f"assignment=local_robot={self.local_robot_id} "
            f"assigned_robot={self.assigned_robot_id} accepted={accepted}"
        )


def evaluate_mission_assignment(
    *,
    local_robot_id: str,
    requested_robot_id: str,
) -> MissionAssignmentDecision:
    local = normalize_robot_id(local_robot_id)
    requested = str(requested_robot_id).strip()
    assigned = requested or local
    if assigned != local:
        return MissionAssignmentDecision(
            accepted=False,
            local_robot_id=local,
            assigned_robot_id=assigned,
            message=f"mission_assigned_to_other_robot:{assigned}",
        )
    return MissionAssignmentDecision(
        accepted=True,
        local_robot_id=local,
        assigned_robot_id=assigned,
        message="mission_assigned_local",
    )
