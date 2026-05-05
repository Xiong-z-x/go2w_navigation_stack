from __future__ import annotations

from pathlib import Path
import threading
from types import SimpleNamespace

from go2w_mission import mission_api as mission_api_module
from go2w_mission.mission_api import MissionApiRuntime
from go2w_mission.mission_assignment import evaluate_mission_assignment
from go2w_mission.mission_orchestrator import build_initial_orchestrator_state
from go2w_mission.mission_queue_replay import build_initial_queue_replay_state
from go2w_mission.mission_scheduler import MissionScheduleGate
from go2w_mission.mission_task_history import build_initial_task_history_state
from go2w_mission.phase4b_mission_segments import MissionSegment


class _FakeLogger:
    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.warning_messages: list[str] = []

    def info(self, message: str) -> None:
        self.info_messages.append(message)

    def warning(self, message: str) -> None:
        self.warning_messages.append(message)


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
    graph_file = tmp_path / "assignment.geojson"
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


def _make_goal_handle(
    graph_file: Path,
    *,
    assigned_robot_id: str = "",
) -> _FakeGoalHandle:
    request = SimpleNamespace(
        start_id=100,
        goal_id=202,
        graph_file=str(graph_file),
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
        priority=0,
        assigned_robot_id=assigned_robot_id,
    )
    return _FakeGoalHandle(request)


def test_assignment_policy_accepts_blank_as_local_default() -> None:
    decision = evaluate_mission_assignment(
        local_robot_id="go2w_alpha",
        requested_robot_id="",
    )

    assert decision.accepted is True
    assert decision.local_robot_id == "go2w_alpha"
    assert decision.assigned_robot_id == "go2w_alpha"
    assert decision.message == "mission_assigned_local"
    assert decision.summary() == (
        "assignment=local_robot=go2w_alpha assigned_robot=go2w_alpha "
        "accepted=true"
    )


def test_assignment_policy_rejects_goal_for_other_robot() -> None:
    decision = evaluate_mission_assignment(
        local_robot_id="go2w_alpha",
        requested_robot_id="go2w_beta",
    )

    assert decision.accepted is False
    assert decision.local_robot_id == "go2w_alpha"
    assert decision.assigned_robot_id == "go2w_beta"
    assert decision.message == "mission_assigned_to_other_robot:go2w_beta"
    assert "accepted=false" in decision.summary()


def test_mission_api_rejects_goal_assigned_to_other_robot_before_queueing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    goal = _make_goal_handle(graph_file, assigned_robot_id="go2w_beta")

    result = runtime.execute(goal)

    assert result["success"] is False
    assert result["result_code"] == "MISSION_ASSIGNMENT_REJECTED"
    assert result["message"] == "mission_assigned_to_other_robot:go2w_beta"
    assert runtime.mission_scheduler.snapshot().active_ticket is None
    assert runtime.queue_replay_state.record_count == 0
    assert runtime.task_history_state.record_count == 0


def test_mission_api_records_assignment_in_terminal_history(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    goal = _make_goal_handle(graph_file, assigned_robot_id="go2w_alpha")

    result = runtime.execute(goal)

    assert result["result_code"] == "MISSION_SUCCEEDED"
    assert runtime.task_history_state.record_count == 1
    latest = runtime.task_history_state.latest_record
    assert latest is not None
    assert latest.assigned_robot_id == "go2w_alpha"
    status = runtime.handle_orchestrator_command("status", "")
    assert "assignment=local_robot=go2w_alpha" in status["state_summary"]
    assert "latest_robot=go2w_alpha" in status["state_summary"]
