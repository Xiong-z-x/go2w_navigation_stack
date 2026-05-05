from __future__ import annotations

from pathlib import Path
import threading
from types import SimpleNamespace

from go2w_mission import mission_api as mission_api_module
from go2w_mission.mission_api import MissionApiRuntime
from go2w_mission.mission_orchestrator import build_initial_orchestrator_state
from go2w_mission.mission_queue_replay import build_initial_queue_replay_state
from go2w_mission.mission_scheduler import MissionScheduleGate
from go2w_mission.mission_task_history import build_initial_task_history_state
from go2w_mission.mission_workflow_backend import (
    MissionWorkflowEvent,
    MissionWorkflowEventStateStore,
    build_initial_workflow_event_state,
)
from go2w_mission.phase4b_mission_segments import MissionSegment


class _FakeLogger:
    def info(self, _message: str) -> None:
        return

    def warning(self, _message: str) -> None:
        return


class _FakeNode:
    def __init__(self) -> None:
        self._logger = _FakeLogger()

    def get_logger(self) -> _FakeLogger:
        return self._logger


class _FakeGoalHandle:
    def __init__(self, request) -> None:
        self.request = request
        self.is_cancel_requested = False
        self.feedback_states: list[str] = []
        self.final_result_code = ""

    def publish_feedback(self, feedback) -> None:
        self.feedback_states.append(str(feedback["state"]))

    def succeed(self) -> None:
        self.final_result_code = "SUCCEEDED"

    def abort(self) -> None:
        self.final_result_code = "ABORTED"

    def canceled(self) -> None:
        self.final_result_code = "CANCELED"


class _FakeGraph:
    def geometry_mismatches(self) -> list[str]:
        return []


def _build_runtime(monkeypatch, tmp_path: Path) -> tuple[MissionApiRuntime, Path]:
    graph_file = tmp_path / "workflow_backend.geojson"
    graph_file.write_text("{}", encoding="utf-8")

    runtime = object.__new__(MissionApiRuntime)
    runtime.node = _FakeNode()
    runtime.mission_robot_id = "go2w_alpha"
    runtime.compute_route_client = SimpleNamespace(wait_for_server=lambda timeout_sec: True)
    runtime.navigate_to_pose_client = SimpleNamespace(wait_for_server=lambda timeout_sec: True)
    runtime.stair_exec_client = SimpleNamespace(wait_for_server=lambda timeout_sec: True)
    runtime.state_store = SimpleNamespace(load=lambda: None, save=lambda checkpoint: None)
    runtime.mission_retry_limit = 0
    runtime.mission_retry_backoff_sec = 0.0
    runtime.mission_recovery_enabled = False
    runtime.flat_behavior_tree = "success"
    runtime.mission_scheduler = MissionScheduleGate(capacity=2)
    runtime.queue_replay_state_store = SimpleNamespace(save=lambda state: None)
    runtime.queue_replay_state = build_initial_queue_replay_state(2)
    runtime._queue_replay_lock = threading.Lock()
    runtime.task_history_state_store = SimpleNamespace(save=lambda state: None)
    runtime.task_history_state = build_initial_task_history_state(50)
    runtime._task_history_lock = threading.Lock()
    runtime._task_history_context = None
    runtime.workflow_event_state_store = SimpleNamespace(save=lambda state: None)
    runtime.workflow_event_state = build_initial_workflow_event_state(10)
    runtime._workflow_event_lock = threading.Lock()
    runtime.orchestrator_state_store = SimpleNamespace(save=lambda state: None)
    runtime.orchestrator_state = build_initial_orchestrator_state(2)
    runtime._orchestrator_state_lock = threading.Lock()
    runtime._operator_cancel_active = threading.Event()
    runtime._mission_lock = threading.Lock()

    monkeypatch.setattr(
        mission_api_module.Phase4ARouteGraph,
        "from_file",
        lambda graph_path: _FakeGraph(),
    )
    monkeypatch.setattr(
        mission_api_module,
        "build_mission_segments",
        lambda graph, edge_ids: [
            MissionSegment(segment_type="flat", edge_ids=(10,)),
        ],
    )
    monkeypatch.setattr(
        runtime,
        "_compute_route_edge_ids",
        lambda goal_handle, goal_spec: {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "route_computed",
            "edge_ids": [10],
        },
    )
    monkeypatch.setattr(
        runtime,
        "_execute_segments",
        lambda *args, **kwargs: {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "mission_succeeded",
            "current_segment_index": 0,
            "current_segment_type": "flat",
            "active_owner": "flat",
            "next_segment_index": 1,
            "retry_count": 0,
        },
    )
    monkeypatch.setattr(
        runtime,
        "_feedback",
        lambda state, current_segment_index, current_segment_type, active_owner, progress: {
            "state": state,
            "current_segment_index": current_segment_index,
            "current_segment_type": current_segment_type,
            "active_owner": active_owner,
            "progress": progress,
        },
    )

    def fake_finish(
        goal_handle,
        *,
        success: bool,
        result_code: str,
        message: str,
        segment_count: int,
        segment_summary: str,
    ):
        if success:
            goal_handle.succeed()
        elif result_code == "MISSION_CANCELED":
            goal_handle.canceled()
        else:
            goal_handle.abort()
        runtime._append_task_history_record(
            success=success,
            result_code=result_code,
            message=message,
            segment_count=segment_count,
            segment_summary=segment_summary,
        )
        return {
            "success": success,
            "result_code": result_code,
            "message": message,
            "segment_count": segment_count,
            "segment_summary": segment_summary,
        }

    monkeypatch.setattr(runtime, "_finish", fake_finish)
    return runtime, graph_file


def _make_goal_handle(graph_file: Path) -> _FakeGoalHandle:
    request = SimpleNamespace(
        start_id=100,
        goal_id=202,
        graph_file=str(graph_file),
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
        priority=2,
        assigned_robot_id="go2w_alpha",
    )
    return _FakeGoalHandle(request)


def test_workflow_event_store_round_trips_and_retains_latest_events(
    tmp_path: Path,
) -> None:
    store = MissionWorkflowEventStateStore(tmp_path / "workflow_events.json")
    state = build_initial_workflow_event_state(2)
    for index, event_type in enumerate(("ADMIT", "ACTIVE", "COMPLETE")):
        state = state.append_event(
            MissionWorkflowEvent(
                event_id=index,
                event_type=event_type,
                mission_key="100->202:map:graph:deadbeef",
                ticket=7,
                mode="OPEN",
                message=event_type.lower(),
                created_at=1000.0 + index,
            )
        )

    store.save(state)
    loaded = store.load()

    assert loaded is not None
    assert loaded.record_count == 2
    assert loaded.latest_event is not None
    assert loaded.latest_event.event_type == "COMPLETE"
    assert [event.event_type for event in loaded.events] == ["ACTIVE", "COMPLETE"]
    assert "workflow_backend=events=2 retain=2" in loaded.summary()
    assert "latest=COMPLETE" in loaded.summary()


def test_mission_api_records_workflow_lifecycle_events(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    result = runtime.execute(_make_goal_handle(graph_file))

    assert result["result_code"] == "MISSION_SUCCEEDED"
    event_types = [event.event_type for event in runtime.workflow_event_state.events]
    assert event_types == ["ADMIT", "ACTIVE", "COMPLETE"]
    assert runtime.workflow_event_state.latest_event is not None
    assert runtime.workflow_event_state.latest_event.message == "mission_succeeded"


def test_mission_control_workflow_events_command_returns_backend_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    runtime.execute(_make_goal_handle(graph_file))

    result = runtime.handle_orchestrator_command("workflow_events", "")

    assert result["accepted"] is True
    assert result["message"] == "workflow_events_snapshot"
    assert "workflow_backend=events=3" in result["state_summary"]
    assert "latest=COMPLETE" in result["state_summary"]
