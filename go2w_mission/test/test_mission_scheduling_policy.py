from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import threading
import time

from go2w_mission import mission_api as mission_api_module
from go2w_mission.mission_api import MissionApiRuntime
from go2w_mission.mission_orchestrator import (
    MissionOrchestratorState,
    MissionOrchestratorStateStore,
    build_initial_orchestrator_state,
)
from go2w_mission.mission_queue_replay import (
    QUEUED_STATE,
    MissionQueueRecord,
    MissionQueueReplayState,
    MissionQueueReplayStateStore,
    build_initial_queue_replay_state,
)
from go2w_mission.mission_scheduler import MissionScheduleGate
from go2w_mission.mission_task_history import (
    MissionTaskHistoryRecord,
    MissionTaskHistoryState,
    MissionTaskHistoryStateStore,
    build_initial_task_history_state,
)
from go2w_mission.mission_recovery import build_mission_key
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


def _install_fake_run_mission_module(monkeypatch) -> None:
    class _Result:
        def __init__(self) -> None:
            self.success = False
            self.result_code = ""
            self.message = ""
            self.segment_count = 0
            self.segment_summary = ""

    class _Feedback:
        def __init__(self) -> None:
            self.state = ""
            self.current_segment_index = 0
            self.current_segment_type = ""
            self.active_owner = ""
            self.progress = 0.0

    action_module = ModuleType("go2w_mission.action")
    action_module.RunMission = SimpleNamespace(
        Result=_Result,
        Feedback=_Feedback,
    )
    monkeypatch.setitem(sys.modules, "go2w_mission.action", action_module)


def _wait_until(predicate, *, timeout_sec: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _build_runtime(monkeypatch, tmp_path: Path, *, fake_finish: bool = True):
    if not fake_finish:
        _install_fake_run_mission_module(monkeypatch)
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
    runtime.queue_replay_state_store = SimpleNamespace(
        save=lambda state: None,
    )
    runtime.queue_replay_state = build_initial_queue_replay_state(2)
    runtime._queue_replay_lock = threading.Lock()
    runtime.task_history_state_store = SimpleNamespace(
        save=lambda state: None,
    )
    runtime.task_history_state = build_initial_task_history_state(50)
    runtime._task_history_lock = threading.Lock()
    runtime._task_history_context = None
    runtime.orchestrator_state_store = SimpleNamespace(
        save=lambda state: None,
    )
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

    if fake_finish:
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


def _make_goal_handle(
    graph_file: Path,
    *,
    start_id: int,
    goal_id: int,
    priority: int = 0,
) -> _FakeGoalHandle:
    request = SimpleNamespace(
        start_id=start_id,
        goal_id=goal_id,
        graph_file=str(graph_file),
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
        priority=priority,
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


def test_mission_schedule_gate_prioritizes_waiting_goals_without_preemption() -> None:
    gate = MissionScheduleGate(capacity=3)

    active = gate.reserve(priority=0)
    assert gate.wait_for_turn(active.ticket, lambda: False, poll_timeout_sec=0.01)

    low = gate.reserve(priority=1)
    high = gate.reserve(priority=5)

    snapshot = gate.snapshot()
    assert snapshot.active_ticket == active.ticket
    assert snapshot.queued_tickets == (high.ticket, low.ticket)
    assert snapshot.queued_priorities == ((high.ticket, 5), (low.ticket, 1))

    gate.release(active.ticket)

    high_deadline = time.monotonic() + 0.2
    assert gate.wait_for_turn(
        high.ticket,
        lambda: time.monotonic() > high_deadline,
        poll_timeout_sec=0.01,
    )
    assert gate.snapshot().active_ticket == high.ticket

    gate.release(high.ticket)

    low_deadline = time.monotonic() + 0.2
    assert gate.wait_for_turn(
        low.ticket,
        lambda: time.monotonic() > low_deadline,
        poll_timeout_sec=0.01,
    )
    assert gate.snapshot().active_ticket == low.ticket


def test_mission_schedule_gate_keeps_fifo_for_equal_priority() -> None:
    gate = MissionScheduleGate(capacity=3)

    active = gate.reserve(priority=0)
    assert gate.wait_for_turn(active.ticket, lambda: False, poll_timeout_sec=0.01)

    first_waiting = gate.reserve(priority=3)
    second_waiting = gate.reserve(priority=3)

    snapshot = gate.snapshot()
    assert snapshot.queued_tickets == (first_waiting.ticket, second_waiting.ticket)
    assert snapshot.queued_priorities == (
        (first_waiting.ticket, 3),
        (second_waiting.ticket, 3),
    )


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


def test_mission_api_prioritizes_high_priority_queued_goal_after_active_releases(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    runtime.mission_scheduler = MissionScheduleGate(capacity=3)
    runtime.queue_replay_state = build_initial_queue_replay_state(3)
    runtime.orchestrator_state = build_initial_orchestrator_state(3)
    first_release = threading.Event()
    first_started = threading.Event()
    activation_order: list[int] = []
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
            activation_order.append(int(goal_handle.request.start_id))
            call_index = len(activation_order) - 1
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

    first_goal = _make_goal_handle(
        graph_file,
        start_id=100,
        goal_id=202,
        priority=0,
    )
    low_goal = _make_goal_handle(
        graph_file,
        start_id=101,
        goal_id=203,
        priority=1,
    )
    high_goal = _make_goal_handle(
        graph_file,
        start_id=102,
        goal_id=204,
        priority=5,
    )

    first_result: dict[str, object] = {}
    low_result: dict[str, object] = {}
    high_result: dict[str, object] = {}

    def run_first() -> None:
        first_result["value"] = runtime.execute(first_goal)

    def run_low() -> None:
        low_result["value"] = runtime.execute(low_goal)

    def run_high() -> None:
        high_result["value"] = runtime.execute(high_goal)

    first_thread = threading.Thread(target=run_first, daemon=True)
    first_thread.start()
    assert first_started.wait(timeout=2.0)

    low_thread = threading.Thread(target=run_low, daemon=True)
    high_thread = threading.Thread(target=run_high, daemon=True)
    low_thread.start()
    assert _wait_until(lambda: "QUEUED" in low_goal.feedback_states)
    high_thread.start()
    assert _wait_until(lambda: "QUEUED" in high_goal.feedback_states)

    first_release.set()
    first_thread.join(timeout=5.0)
    high_thread.join(timeout=5.0)
    low_thread.join(timeout=5.0)

    assert first_result["value"]["result_code"] == "MISSION_SUCCEEDED"
    assert high_result["value"]["result_code"] == "MISSION_SUCCEEDED"
    assert low_result["value"]["result_code"] == "MISSION_SUCCEEDED"
    assert activation_order == [100, 102, 101]
    assert high_goal.feedback_states[1] == "SCHEDULED"
    assert low_goal.feedback_states[1] == "SCHEDULED"


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


def test_mission_orchestrator_state_store_round_trips_snapshot(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "mission_orchestrator.json"
    store = MissionOrchestratorStateStore(state_file)
    state = MissionOrchestratorState(
        mode="PAUSED",
        pause_reason="operator_hold",
        active_mission_key="100->202:map:graph:deadbeef",
        active_ticket=7,
        queue_capacity=2,
        queued_tickets=(8,),
        last_command="pause",
        last_message="operator_hold",
        updated_at=1234.5,
    )

    store.save(state)
    loaded = store.load()

    assert loaded == state
    assert loaded is not None
    assert loaded.paused is True
    assert "mode=PAUSED" in loaded.summary()


def test_mission_api_pause_blocks_new_admissions_until_resume(
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

    pause_result = runtime.handle_orchestrator_command("pause", "operator_hold")
    assert pause_result["accepted"] is True
    assert pause_result["mode"] == "PAUSED"
    assert pause_result["message"] == "mission_paused"

    third_result = runtime.execute(third_goal)
    assert third_result["result_code"] == "MISSION_BUSY"
    assert third_result["message"] == "mission_paused"

    first_release.set()
    first_thread.join(timeout=5.0)

    time.sleep(0.2)
    assert "SCHEDULED" not in second_goal.feedback_states

    resume_result = runtime.handle_orchestrator_command("resume", "operator_resume")
    assert resume_result["accepted"] is True
    assert resume_result["mode"] == "OPEN"
    assert resume_result["message"] == "mission_resumed"

    assert _wait_until(lambda: "SCHEDULED" in second_goal.feedback_states)
    second_thread.join(timeout=5.0)

    assert "value" in first_result
    assert "value" in second_result
    assert first_result["value"]["result_code"] == "MISSION_SUCCEEDED"
    assert second_result["value"]["result_code"] == "MISSION_SUCCEEDED"
    assert execution_calls["count"] == 2


def test_mission_api_operator_cancel_active_goal(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    active_started = threading.Event()

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
        active_started.set()
        assert _wait_until(lambda: runtime._operator_cancel_active.is_set())
        return {
            "success": False,
            "result_code": "MISSION_CANCELED",
            "message": "mission_operator_canceled",
            "current_segment_index": 0,
            "current_segment_type": "flat",
            "active_owner": "flat",
            "next_segment_index": 0,
            "retry_count": 0,
        }

    monkeypatch.setattr(runtime, "_execute_segments", fake_execute_segments)

    goal = _make_goal_handle(graph_file, start_id=100, goal_id=202, priority=6)
    result_box: dict[str, object] = {}

    def run_goal() -> None:
        result_box["value"] = runtime.execute(goal)

    thread = threading.Thread(target=run_goal, daemon=True)
    thread.start()

    assert active_started.wait(timeout=2.0)

    cancel_result = runtime.handle_orchestrator_command(
        "cancel_active",
        "operator_stop",
    )
    assert cancel_result["accepted"] is True
    assert cancel_result["message"] == "operator_cancel_active_requested"
    assert "mode=OPEN" in cancel_result["state_summary"]

    thread.join(timeout=5.0)
    assert "value" in result_box
    assert result_box["value"]["result_code"] == "MISSION_CANCELED"
    assert result_box["value"]["message"] == "mission_operator_canceled"


def test_queue_replay_store_round_trips_records(tmp_path: Path) -> None:
    state_file = tmp_path / "mission_queue_replay.json"
    store = MissionQueueReplayStateStore(state_file)
    record = MissionQueueRecord(
        mission_key="100->202:map:graph:deadbeef",
        ticket=0,
        queue_position=1,
        priority=7,
        state=QUEUED_STATE,
        start_id=100,
        goal_id=202,
        graph_file="go2w_navigation/graphs/phase3c_hospital_multifloor_route.geojson",
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
        last_command="ADMIT",
        last_message="ticket=0 queued=True",
        admitted_at=1234.5,
        updated_at=1234.5,
    )
    state = MissionQueueReplayState(
        queue_replay_pending=True,
        queue_capacity=2,
        next_ticket=1,
        records=(record,),
        last_command="BOOT",
        last_message="queue_replay_pending",
        updated_at=1234.5,
    )

    store.save(state)
    loaded = store.load()

    assert loaded == state
    assert loaded is not None
    assert loaded.summary().startswith("replay=PENDING")
    assert "priorities=[0:7]" in loaded.summary()

    store.clear()
    assert store.load() is None


def test_mission_api_replay_queue_restores_pending_record(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path)
    mission_key = build_mission_key(
        start_id=100,
        goal_id=202,
        graph_file=str(graph_file),
        route_frame_id="map",
    )
    record = MissionQueueRecord(
        mission_key=mission_key,
        ticket=0,
        queue_position=1,
        priority=4,
        state=QUEUED_STATE,
        start_id=100,
        goal_id=202,
        graph_file=str(graph_file),
        route_frame_id="map",
        expected_stair_duration_sec=0.3,
        result_timeout_sec=4.0,
        flat_result_timeout_sec=4.0,
        last_command="ADMIT",
        last_message="ticket=0 queued=True",
        admitted_at=1234.5,
        updated_at=1234.5,
    )
    runtime.queue_replay_state = MissionQueueReplayState(
        queue_replay_pending=True,
        queue_capacity=2,
        next_ticket=1,
        records=(record,),
        last_command="BOOT",
        last_message="queue_replay_pending",
        updated_at=1234.5,
    )

    reserve_calls = {"count": 0}
    original_reserve = runtime.mission_scheduler.reserve

    def reserve_spy():
        reserve_calls["count"] += 1
        return original_reserve()

    runtime.mission_scheduler.reserve = reserve_spy

    execute_calls = {"count": 0}

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
        execute_calls["count"] += 1
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

    pending_goal = _make_goal_handle(graph_file, start_id=100, goal_id=202)
    pending_result = runtime.execute(pending_goal)

    assert pending_result["result_code"] == "MISSION_BUSY"
    assert pending_result["message"] == "mission_queue_replay_pending"

    replay_result = runtime.handle_orchestrator_command("replay_queue", "operator_replay")
    assert replay_result["accepted"] is True
    assert replay_result["message"] == "queue_replayed"
    assert "replay=ACKED" in replay_result["state_summary"]
    assert "priorities=[0:4]" in replay_result["state_summary"]
    assert runtime.queue_replay_state.queue_replay_pending is False
    assert runtime.mission_scheduler.snapshot().queued_tickets == (0,)
    assert runtime.mission_scheduler.snapshot().queued_priorities == ((0, 4),)

    replayed_goal = _make_goal_handle(graph_file, start_id=100, goal_id=202)
    replayed_result = runtime.execute(replayed_goal)

    assert reserve_calls["count"] == 0
    assert execute_calls["count"] == 1
    assert replayed_result["result_code"] == "MISSION_SUCCEEDED"
    assert replayed_result["message"] == "mission_succeeded"
    assert runtime.queue_replay_state.record_count == 0


def test_mission_task_history_store_round_trips_and_archives(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "mission_task_history.json"
    store = MissionTaskHistoryStateStore(state_file)
    record_one = MissionTaskHistoryRecord(
        run_id="100->202:map:graph:deadbeef:0:1000",
        mission_key="100->202:map:graph:deadbeef",
        ticket=0,
        queue_position=1,
        priority=2,
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
        last_message="mission_finished",
        updated_at=1002.0,
    )
    record_two = record_one.with_updates(
        run_id="101->203:map:graph:deadbeef:1:2000",
        mission_key="101->203:map:graph:deadbeef",
        ticket=1,
        queue_position=2,
        state="FAILED",
        result_code="MISSION_ROUTE_UNAVAILABLE",
        message="route_goal_rejected",
        start_id=101,
        goal_id=203,
        admitted_at=2000.0,
        activated_at=2001.0,
        completed_at=2002.0,
        last_message="route_goal_rejected",
        updated_at=2002.0,
    )
    state = MissionTaskHistoryState(
        retention_limit=2,
        records=(record_one, record_two),
        last_command="COMPLETE",
        last_message="mission_finished",
        updated_at=2002.0,
    )

    store.save(state)
    loaded = store.load()

    assert loaded == state
    assert loaded is not None
    assert loaded.summary().startswith("history=records=2 retain=2")
    assert "latest_priority=2" in loaded.summary()

    trimmed = loaded.archive_to_limit(1)
    assert trimmed.record_count == 1
    assert trimmed.latest_record is not None
    assert trimmed.latest_record.run_id == record_two.run_id

    store.save(trimmed)
    loaded_trimmed = store.load()
    assert loaded_trimmed is not None
    assert loaded_trimmed.record_count == 1
    assert loaded_trimmed.latest_record is not None
    assert loaded_trimmed.latest_record.run_id == record_two.run_id


def test_mission_api_records_terminal_task_history_and_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path, fake_finish=False)

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

    goal = _make_goal_handle(graph_file, start_id=100, goal_id=202, priority=6)
    result = runtime.execute(goal)
    mission_key = build_mission_key(
        start_id=100,
        goal_id=202,
        graph_file=str(graph_file),
        route_frame_id="map",
    )

    assert result.success is True
    assert result.result_code == "MISSION_SUCCEEDED"
    assert runtime.task_history_state.record_count == 1
    assert runtime.task_history_state.latest_record is not None
    assert runtime.task_history_state.latest_record.mission_key == mission_key
    assert runtime.task_history_state.latest_record.result_code == "MISSION_SUCCEEDED"
    assert runtime.task_history_state.latest_record.state == "SUCCEEDED"
    assert runtime.task_history_state.latest_record.priority == 6

    history_result = runtime.handle_orchestrator_command("history", "operator_review")
    assert history_result["accepted"] is True
    assert history_result["message"] == "history_snapshot"
    assert "history=records=1" in history_result["state_summary"]
    assert "latest_result=MISSION_SUCCEEDED" in history_result["state_summary"]
    assert "latest_priority=6" in history_result["state_summary"]


def test_mission_api_archive_history_trims_old_records(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime, graph_file = _build_runtime(monkeypatch, tmp_path, fake_finish=False)
    record_one = MissionTaskHistoryRecord(
        run_id="100->202:map:graph:deadbeef:0:1000",
        mission_key="100->202:map:graph:deadbeef",
        ticket=0,
        queue_position=1,
        priority=0,
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
        last_message="mission_finished",
        updated_at=1002.0,
    )
    record_two = record_one.with_updates(
        run_id="101->203:map:graph:deadbeef:1:2000",
        mission_key="101->203:map:graph:deadbeef",
        ticket=1,
        queue_position=2,
        priority=3,
        state="FAILED",
        result_code="MISSION_ROUTE_UNAVAILABLE",
        message="route_goal_rejected",
        start_id=101,
        goal_id=203,
        admitted_at=2000.0,
        activated_at=2001.0,
        completed_at=2002.0,
        last_message="route_goal_rejected",
        updated_at=2002.0,
    )
    record_three = record_two.with_updates(
        run_id="102->204:map:graph:deadbeef:2:3000",
        mission_key="102->204:map:graph:deadbeef",
        ticket=2,
        queue_position=3,
        priority=5,
        state="CANCELED",
        result_code="MISSION_CANCELED",
        message="mission_canceled",
        start_id=102,
        goal_id=204,
        admitted_at=3000.0,
        activated_at=3001.0,
        completed_at=3002.0,
        last_command="CANCEL",
        last_message="mission_canceled",
        updated_at=3002.0,
    )
    runtime.task_history_state = MissionTaskHistoryState(
        retention_limit=50,
        records=(record_one, record_two, record_three),
        last_command="COMPLETE",
        last_message="mission_finished",
        updated_at=3002.0,
    )

    archive_result = runtime.handle_orchestrator_command("archive_history", "retain=2")
    assert archive_result["accepted"] is True
    assert archive_result["message"] == "history_archived"
    assert runtime.task_history_state.record_count == 2
    assert runtime.task_history_state.latest_record is not None
    assert runtime.task_history_state.latest_record.run_id == record_three.run_id
    assert "history=records=2 retain=2" in archive_result["state_summary"]
