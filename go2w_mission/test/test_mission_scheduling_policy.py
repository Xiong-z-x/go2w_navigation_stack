from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import threading
import time

from go2w_mission import mission_api as mission_api_module
from go2w_mission.mission_api import MissionApiRuntime
from go2w_mission.mission_scheduler import MissionScheduleGate
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
        self.final_result_code: str = ""

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


def _wait_until(predicate, *, timeout_sec: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _build_runtime(monkeypatch, tmp_path: Path):
    graph_file = tmp_path / "mission_queue.geojson"
    graph_file.write_text("{}", encoding="utf-8")

    runtime = object.__new__(MissionApiRuntime)
    runtime.node = _FakeNode()
    runtime.compute_route_client = SimpleNamespace(wait_for_server=lambda timeout_sec: True)
    runtime.navigate_to_pose_client = SimpleNamespace(wait_for_server=lambda timeout_sec: True)
    runtime.stair_exec_client = SimpleNamespace(wait_for_server=lambda timeout_sec: True)
    runtime.state_store = SimpleNamespace(load=lambda: None, save=lambda checkpoint: None)
    runtime.mission_retry_limit = 0
    runtime.mission_retry_backoff_sec = 0.0
    runtime.mission_recovery_enabled = False
    runtime.flat_behavior_tree = "success"
    runtime.mission_scheduler = MissionScheduleGate(capacity=2)
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
            MissionSegment(
                segment_type="stair",
                edge_ids=(500,),
                connector_id="stair_a",
                floor_from="F1",
                floor_to="F2",
            ),
        ],
    )

    def fake_feedback(state: str, current_segment_index: int, current_segment_type: str, active_owner: str, progress: float):
        return {
            "state": state,
            "current_segment_index": current_segment_index,
            "current_segment_type": current_segment_type,
            "active_owner": active_owner,
            "progress": progress,
        }

    monkeypatch.setattr(runtime, "_feedback", fake_feedback)

    def fake_finish(goal_handle, *, success: bool, result_code: str, message: str, segment_count: int, segment_summary: str):
        if success:
            goal_handle.succeed()
        elif result_code == "MISSION_CANCELED":
            goal_handle.canceled()
        else:
            goal_handle.abort()
        return {
            "success": success,
            "result_code": result_code,
            "message": message,
            "segment_count": segment_count,
            "segment_summary": segment_summary,
        }

    monkeypatch.setattr(runtime, "_finish", fake_finish)
    monkeypatch.setattr(
        runtime,
        "_compute_route_edge_ids",
        lambda goal_handle, goal_spec: {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "route_computed",
            "edge_ids": [10, 500],
        },
    )

    return runtime, graph_file


def _make_goal_handle(graph_file: Path, *, start_id: int, goal_id: int) -> _FakeGoalHandle:
    request = SimpleNamespace(
        start_id=start_id,
        goal_id=goal_id,
        graph_file=str(graph_file),
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
    )
    return _FakeGoalHandle(request)


def test_mission_schedule_gate_enforces_fifo_capacity_and_cancellation() -> None:
    gate = MissionScheduleGate(capacity=2)

    first = gate.reserve()
    second = gate.reserve()
    third = gate.reserve()

    assert first.accepted is True
    assert first.queue_position == 1
    assert first.queued is False

    assert second.accepted is True
    assert second.queue_position == 2
    assert second.queued is True

    assert third.accepted is False
    assert third.rejected_reason == "queue_full"

    assert gate.wait_for_turn(first.ticket, lambda: False, poll_timeout_sec=0.01) is True
    snapshot = gate.snapshot()
    assert snapshot.active_ticket == first.ticket
    assert snapshot.queued_tickets == (second.ticket,)

    cancel_event = threading.Event()
    second_result: dict[str, bool] = {}

    def wait_second() -> None:
        second_result["value"] = gate.wait_for_turn(
            second.ticket,
            cancel_event.is_set,
            poll_timeout_sec=0.01,
        )

    thread = threading.Thread(target=wait_second, daemon=True)
    thread.start()
    time.sleep(0.05)
    cancel_event.set()
    thread.join(timeout=2.0)

    assert second_result["value"] is False
    assert second.ticket not in gate.snapshot().queued_tickets

    gate.release(first.ticket)


def test_mission_api_queues_one_goal_and_rejects_the_third(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    first_release = threading.Event()
    first_started = threading.Event()
    execution_calls = {"count": 0}
    execution_lock = threading.Lock()

    def fake_execute_segments(
        goal_handle,
        graph,
        goal_spec,
        segments,
        *,
        mission_key: str,
        segment_summary: str,
        start_index: int,
        route_edge_ids: tuple[int, ...],
    ):
        with execution_lock:
            call_index = execution_calls["count"]
            execution_calls["count"] += 1
        if call_index == 0:
            first_started.set()
            assert first_release.wait(timeout=5.0)
        return {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "mission_succeeded",
            "current_segment_index": len(segments) - 1 if segments else 0,
            "current_segment_type": segments[-1].segment_type if segments else "",
            "active_owner": "flat",
            "next_segment_index": len(segments),
            "retry_count": 0,
        }

    monkeypatch.setattr(runtime, "_execute_segments", fake_execute_segments)

    first_goal = _make_goal_handle(graph_file, start_id=100, goal_id=202)
    second_goal = _make_goal_handle(graph_file, start_id=101, goal_id=203)
    third_goal = _make_goal_handle(graph_file, start_id=102, goal_id=204)

    first_result: dict[str, object] = {}
    second_result: dict[str, object] = {}

    def run_first() -> None:
        first_result["value"] = runtime.execute(first_goal)

    def run_second() -> None:
        second_result["value"] = runtime.execute(second_goal)

    first_thread = threading.Thread(target=run_first, daemon=True)
    first_thread.start()

    assert first_started.wait(timeout=2.0)

    second_thread = threading.Thread(target=run_second, daemon=True)
    second_thread.start()
    assert _wait_until(lambda: "QUEUED" in second_goal.feedback_states)

    third_result = runtime.execute(third_goal)

    assert third_result["result_code"] == "MISSION_BUSY"
    assert third_result["message"] == "mission_queue_full"
    assert second_goal.feedback_states[0] == "QUEUED"

    first_release.set()
    first_thread.join(timeout=5.0)
    second_thread.join(timeout=5.0)

    assert "value" in first_result
    assert "value" in second_result
    assert first_result["value"]["result_code"] == "MISSION_SUCCEEDED"
    assert second_result["value"]["result_code"] == "MISSION_SUCCEEDED"
    assert second_goal.feedback_states[1] == "SCHEDULED"
    assert execution_calls["count"] == 2


def test_mission_api_cancels_a_queued_goal_before_activation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    first_release = threading.Event()
    first_started = threading.Event()
    execution_calls = {"count": 0}
    execution_lock = threading.Lock()

    def fake_execute_segments(
        goal_handle,
        graph,
        goal_spec,
        segments,
        *,
        mission_key: str,
        segment_summary: str,
        start_index: int,
        route_edge_ids: tuple[int, ...],
    ):
        with execution_lock:
            call_index = execution_calls["count"]
            execution_calls["count"] += 1
        if call_index == 0:
            first_started.set()
            assert first_release.wait(timeout=5.0)
        return {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "mission_succeeded",
            "current_segment_index": len(segments) - 1 if segments else 0,
            "current_segment_type": segments[-1].segment_type if segments else "",
            "active_owner": "flat",
            "next_segment_index": len(segments),
            "retry_count": 0,
        }

    monkeypatch.setattr(runtime, "_execute_segments", fake_execute_segments)

    first_goal = _make_goal_handle(graph_file, start_id=100, goal_id=202)
    second_goal = _make_goal_handle(graph_file, start_id=101, goal_id=203)

    first_result: dict[str, object] = {}
    second_result: dict[str, object] = {}

    def run_first() -> None:
        first_result["value"] = runtime.execute(first_goal)

    def run_second() -> None:
        second_result["value"] = runtime.execute(second_goal)

    first_thread = threading.Thread(target=run_first, daemon=True)
    first_thread.start()
    assert first_started.wait(timeout=2.0)

    second_thread = threading.Thread(target=run_second, daemon=True)
    second_thread.start()
    assert _wait_until(lambda: "QUEUED" in second_goal.feedback_states)

    second_goal.is_cancel_requested = True
    assert _wait_until(lambda: "value" in second_result)

    first_release.set()
    first_thread.join(timeout=5.0)
    second_thread.join(timeout=5.0)

    assert "value" in first_result
    assert first_result["value"]["result_code"] == "MISSION_SUCCEEDED"
    assert second_result["value"]["result_code"] == "MISSION_CANCELED"
    assert second_result["value"]["message"] == "mission_queue_canceled"
    assert execution_calls["count"] == 1
