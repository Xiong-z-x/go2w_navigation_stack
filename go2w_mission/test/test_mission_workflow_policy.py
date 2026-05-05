from __future__ import annotations

from pathlib import Path
import threading

from go2w_mission.mission_api import MissionApiRuntime
from go2w_mission.mission_orchestrator import (
    PAUSED_MODE,
    build_initial_orchestrator_state,
)
from go2w_mission.mission_queue_replay import (
    QUEUED_STATE,
    MissionQueueRecord,
    MissionQueueReplayState,
    build_initial_queue_replay_state,
)
from go2w_mission.mission_task_history import (
    MissionTaskHistoryRecord,
    MissionTaskHistoryState,
    build_initial_task_history_state,
)
from go2w_mission.mission_workflow_policy import (
    build_mission_workflow_snapshot,
)


def _queue_record(*, state: str = QUEUED_STATE) -> MissionQueueRecord:
    return MissionQueueRecord(
        mission_key="100->202:map:graph:deadbeef",
        ticket=7,
        queue_position=1,
        priority=3,
        state=state,
        start_id=100,
        goal_id=202,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
        last_command="ADMIT",
        last_message="ticket=7 queued=True",
        admitted_at=1000.0,
        updated_at=1000.0,
    )


def _history_record() -> MissionTaskHistoryRecord:
    return MissionTaskHistoryRecord(
        run_id="100->202:map:graph:deadbeef:7:1000000",
        mission_key="100->202:map:graph:deadbeef",
        ticket=7,
        queue_position=1,
        priority=3,
        state="SUCCEEDED",
        result_code="MISSION_SUCCEEDED",
        message="mission_succeeded",
        start_id=100,
        goal_id=202,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
        segment_count=3,
        segment_summary="flat:10;stair:500;flat:11",
        admitted_at=1000.0,
        activated_at=1001.0,
        completed_at=1002.0,
        last_command="COMPLETE",
        last_message="mission_succeeded",
        updated_at=1002.0,
    )


def _minimal_runtime() -> MissionApiRuntime:
    runtime = object.__new__(MissionApiRuntime)
    runtime.orchestrator_state = build_initial_orchestrator_state(2)
    runtime._orchestrator_state_lock = threading.Lock()
    runtime.queue_replay_state = build_initial_queue_replay_state(2)
    runtime._queue_replay_lock = threading.Lock()
    runtime.task_history_state = build_initial_task_history_state(50)
    runtime._task_history_lock = threading.Lock()
    return runtime


def test_workflow_snapshot_reports_open_idle_policy() -> None:
    snapshot = build_mission_workflow_snapshot(
        build_initial_orchestrator_state(2),
        build_initial_queue_replay_state(2),
        build_initial_task_history_state(50),
    )

    assert snapshot.mode == "OPEN"
    assert snapshot.mission_state == "IDLE"
    assert snapshot.queue_state == "EMPTY"
    assert snapshot.history_state == "EMPTY"
    assert snapshot.available_commands == (
        "status",
        "workflow",
        "history",
        "pause",
    )
    assert (
        "workflow=mode=OPEN mission=IDLE queue=EMPTY history=EMPTY"
        in snapshot.summary()
    )


def test_workflow_snapshot_reports_paused_active_replay_history_policy() -> None:
    orchestrator_state = build_initial_orchestrator_state(2).with_updates(
        mode=PAUSED_MODE,
        active_mission_key="100->202:map:graph:deadbeef",
        active_ticket=7,
        queued_tickets=(8,),
    )
    queue_state = MissionQueueReplayState(
        queue_replay_pending=True,
        queue_capacity=2,
        next_ticket=9,
        records=(_queue_record(),),
        last_command="BOOT",
        last_message="queue_replay_pending",
        updated_at=1000.0,
    )
    history_state = MissionTaskHistoryState(
        retention_limit=50,
        records=(_history_record(),),
        last_command="COMPLETE",
        last_message="mission_succeeded",
        updated_at=1002.0,
    )

    snapshot = build_mission_workflow_snapshot(
        orchestrator_state,
        queue_state,
        history_state,
    )

    assert snapshot.mode == "PAUSED"
    assert snapshot.mission_state == "ACTIVE"
    assert snapshot.queue_state == "REPLAY_PENDING"
    assert snapshot.history_state == "READY"
    assert snapshot.available_commands == (
        "status",
        "workflow",
        "history",
        "resume",
        "cancel_active",
        "replay_queue",
        "archive_history",
    )
    assert "active_ticket=7" in snapshot.summary()
    assert "queued=[8]" in snapshot.summary()


def test_mission_control_workflow_command_returns_policy_summary() -> None:
    runtime = _minimal_runtime()

    result = runtime.handle_orchestrator_command("workflow", "")

    assert result["accepted"] is True
    assert result["mode"] == "OPEN"
    assert result["message"] == "workflow_snapshot"
    assert (
        "workflow=mode=OPEN mission=IDLE queue=EMPTY history=EMPTY"
        in result["state_summary"]
    )
    assert "available=[status,workflow,history,pause]" in result["state_summary"]
    assert "queue_replay=" in result["state_summary"]
    assert "task_history=" in result["state_summary"]
