from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import re
from pathlib import Path
import sys
import threading
import time
from typing import Any

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph
from go2w_mission.phase4b_mission_segments import (
    MissionSegment,
    build_mission_segments,
)
from go2w_mission.mission_pose import pose_stamped_from_xy_yaw
from go2w_mission.mission_assignment import (
    evaluate_mission_assignment,
    normalize_robot_id,
)
from go2w_mission.mission_orchestrator import (
    MissionOrchestratorState,
    MissionOrchestratorStateStore,
    OPEN_MODE,
    PAUSED_MODE,
    build_initial_orchestrator_state,
    sanitize_orchestrator_state_for_runtime,
)
from go2w_mission.mission_queue_replay import (
    ACTIVE_STATE,
    QUEUED_STATE,
    MissionQueueRecord,
    MissionQueueReplayState,
    MissionQueueReplayStateStore,
    build_initial_queue_replay_state,
    sanitize_queue_replay_state_for_runtime,
)
from go2w_mission.mission_task_history import (
    MissionTaskHistoryRecord,
    MissionTaskHistoryState,
    MissionTaskHistoryStateStore,
    build_initial_task_history_state,
    build_mission_run_id,
    mission_history_state_for_result,
    sanitize_task_history_state_for_runtime,
)
from go2w_mission.mission_workflow_backend import (
    MissionWorkflowEvent,
    MissionWorkflowEventState,
    MissionWorkflowEventStateStore,
    build_initial_workflow_event_state,
    sanitize_workflow_event_state_for_runtime,
)
from go2w_mission.mission_workflow_policy import build_mission_workflow_snapshot
from go2w_mission.mission_recovery import (
    MissionCheckpoint,
    MissionStateStore,
    build_mission_key,
    checkpoint_for_goal,
    is_recoverable_result_code,
    should_resume_checkpoint,
)
from go2w_mission.mission_scheduler import MissionScheduleGate
from go2w_mission.mission_scheduler import MissionQueueAdmission


EMPTY_FLAT_BEHAVIOR_TREE_SENTINEL = "__empty__"


@dataclass(frozen=True)
class MissionGoalSpec:
    start_id: int
    goal_id: int
    graph_file: str
    route_frame_id: str
    expected_stair_duration_sec: float
    result_timeout_sec: float
    flat_result_timeout_sec: float
    priority: int = 0
    assigned_robot_id: str = ""


@dataclass(frozen=True)
class MissionTaskHistoryContext:
    run_id: str
    mission_key: str
    ticket: int
    queue_position: int
    priority: int
    assigned_robot_id: str
    start_id: int
    goal_id: int
    graph_file: str
    route_frame_id: str
    admitted_at: float
    activated_at: float

    def with_updates(self, **changes: Any) -> "MissionTaskHistoryContext":
        return replace(self, **changes)


def validate_mission_goal(spec: MissionGoalSpec) -> MissionGoalSpec:
    graph_file = spec.graph_file.strip()
    route_frame_id = spec.route_frame_id.strip()
    if spec.start_id <= 0 or spec.goal_id <= 0:
        raise ValueError("invalid_node_id")
    if spec.start_id == spec.goal_id:
        raise ValueError("same_start_goal")
    if not graph_file:
        raise ValueError("missing_graph_file")
    if not route_frame_id:
        raise ValueError("missing_route_frame")
    if spec.expected_stair_duration_sec <= 0.0:
        raise ValueError("invalid_expected_stair_duration")
    if spec.result_timeout_sec <= 0.0:
        raise ValueError("invalid_result_timeout")
    if spec.flat_result_timeout_sec <= 0.0:
        raise ValueError("invalid_flat_result_timeout")
    return MissionGoalSpec(
        start_id=spec.start_id,
        goal_id=spec.goal_id,
        graph_file=graph_file,
        route_frame_id=route_frame_id,
        expected_stair_duration_sec=spec.expected_stair_duration_sec,
        result_timeout_sec=spec.result_timeout_sec,
        flat_result_timeout_sec=spec.flat_result_timeout_sec,
        priority=int(spec.priority),
        assigned_robot_id=str(spec.assigned_robot_id).strip(),
    )


def classify_mission_result(result_code: str) -> str:
    if result_code == "SUCCEEDED":
        return "MISSION_SUCCEEDED"
    if result_code == "CANCELED":
        return "MISSION_CANCELED"
    return "MISSION_FAILED"


def configure_flat_goal_behavior_tree(goal: Any, behavior_tree: str) -> None:
    goal.behavior_tree = normalize_flat_behavior_tree(behavior_tree)


def normalize_flat_behavior_tree(behavior_tree: str) -> str:
    if str(behavior_tree).strip() == EMPTY_FLAT_BEHAVIOR_TREE_SENTINEL:
        return ""
    return str(behavior_tree)


def summarize_segments(segments: list[MissionSegment]) -> str:
    formatted: list[str] = []
    for segment in segments:
        edges = "|".join(str(edge_id) for edge_id in segment.edge_ids)
        if segment.segment_type == "stair":
            formatted.append(
                f"stair:{edges}:{segment.connector_id}:{segment.floor_from}->{segment.floor_to}"
            )
        else:
            formatted.append(f"{segment.segment_type}:{edges}")
    return ";".join(formatted)


def flat_route_tracking_node_ids(
    graph: Phase4ARouteGraph,
    segment: MissionSegment,
) -> tuple[int, int]:
    first_edge = graph.edges[segment.edge_ids[0]]
    last_edge = graph.edges[segment.edge_ids[-1]]
    return int(first_edge.start_id), int(last_edge.end_id)


class MissionApiRuntime:
    def __init__(
        self,
        *,
        node,
        compute_route_action: str,
        flat_nav_action: str,
        stair_exec_action: str,
        mission_state_file: str,
        mission_orchestrator_state_file: str,
        mission_queue_replay_state_file: str,
        mission_task_history_file: str,
        mission_task_history_retention_limit: int,
        mission_workflow_events_file: str,
        mission_workflow_event_retention_limit: int,
        mission_retry_limit: int,
        mission_retry_backoff_sec: float,
        mission_recovery_enabled: bool,
        flat_behavior_tree: str,
        route_tracking_action: str,
        mission_queue_capacity: int,
        mission_robot_id: str,
    ) -> None:
        from nav2_msgs.action import ComputeAndTrackRoute, ComputeRoute, NavigateToPose
        from rclpy.action import ActionClient
        from rclpy.callback_groups import ReentrantCallbackGroup

        from go2w_control.action import StairExec

        self.node = node
        self.compute_route_type = ComputeRoute
        self.compute_and_track_route_type = ComputeAndTrackRoute
        self.navigate_to_pose_type = NavigateToPose
        self.stair_exec_type = StairExec
        self.action_client_callback_group = ReentrantCallbackGroup()
        self.compute_route_client = ActionClient(
            node,
            ComputeRoute,
            compute_route_action,
            callback_group=self.action_client_callback_group,
        )
        self.route_tracking_client = (
            ActionClient(
                node,
                ComputeAndTrackRoute,
                route_tracking_action,
                callback_group=self.action_client_callback_group,
            )
            if route_tracking_action.strip()
            else None
        )
        self.navigate_to_pose_client = ActionClient(
            node,
            NavigateToPose,
            flat_nav_action,
            callback_group=self.action_client_callback_group,
        )
        self.stair_exec_client = ActionClient(
            node,
            StairExec,
            stair_exec_action,
            callback_group=self.action_client_callback_group,
        )
        state_path = (
            Path(mission_state_file).expanduser()
            if mission_state_file.strip()
            else MissionStateStore.default_path()
        )
        self.state_store = MissionStateStore(state_path)
        self.mission_retry_limit = max(0, int(mission_retry_limit))
        self.mission_retry_backoff_sec = max(0.0, float(mission_retry_backoff_sec))
        self.mission_recovery_enabled = bool(mission_recovery_enabled)
        self.flat_behavior_tree = str(flat_behavior_tree)
        self.route_tracking_action = str(route_tracking_action).strip()
        self.mission_robot_id = normalize_robot_id(mission_robot_id)
        self.mission_scheduler = MissionScheduleGate(
            capacity=mission_queue_capacity,
        )
        orchestrator_state_path = (
            Path(mission_orchestrator_state_file).expanduser()
            if mission_orchestrator_state_file.strip()
            else MissionOrchestratorStateStore.default_path()
        )
        self.orchestrator_state_store = MissionOrchestratorStateStore(
            orchestrator_state_path
        )
        loaded_orchestrator_state = self.orchestrator_state_store.load()
        if loaded_orchestrator_state is None:
            self.orchestrator_state = build_initial_orchestrator_state(
                mission_queue_capacity
            )
        else:
            self.orchestrator_state = sanitize_orchestrator_state_for_runtime(
                loaded_orchestrator_state,
                queue_capacity=mission_queue_capacity,
            )
        self._orchestrator_state_lock = threading.Lock()
        self._operator_cancel_active = threading.Event()
        self._save_orchestrator_state(
            self.orchestrator_state.with_updates(
                last_command="BOOT",
                last_message="orchestrator_ready",
                updated_at=time.time(),
            )
        )
        queue_replay_state_path = (
            Path(mission_queue_replay_state_file).expanduser()
            if mission_queue_replay_state_file.strip()
            else MissionQueueReplayStateStore.default_path()
        )
        self.queue_replay_state_store = MissionQueueReplayStateStore(
            queue_replay_state_path
        )
        loaded_queue_replay_state = self.queue_replay_state_store.load()
        if loaded_queue_replay_state is None:
            self.queue_replay_state = build_initial_queue_replay_state(
                mission_queue_capacity
            )
        else:
            self.queue_replay_state = sanitize_queue_replay_state_for_runtime(
                loaded_queue_replay_state,
                queue_capacity=mission_queue_capacity,
            )
        if self.queue_replay_state.record_count > 0:
            self.queue_replay_state = self.queue_replay_state.with_updates(
                queue_replay_pending=True,
                last_command="BOOT",
                last_message="queue_replay_pending",
                updated_at=time.time(),
            )
        self.queue_replay_state_store.save(self.queue_replay_state)
        self._queue_replay_lock = threading.Lock()
        task_history_state_path = (
            Path(mission_task_history_file).expanduser()
            if mission_task_history_file.strip()
            else MissionTaskHistoryStateStore.default_path()
        )
        self.task_history_state_store = MissionTaskHistoryStateStore(
            task_history_state_path
        )
        loaded_task_history_state = self.task_history_state_store.load()
        if loaded_task_history_state is None:
            self.task_history_state = build_initial_task_history_state(
                mission_task_history_retention_limit
            )
        else:
            self.task_history_state = sanitize_task_history_state_for_runtime(
                loaded_task_history_state,
                retention_limit=mission_task_history_retention_limit,
            )
        self._task_history_lock = threading.Lock()
        self._task_history_context: MissionTaskHistoryContext | None = None
        self._save_task_history_state(
            self.task_history_state.with_updates(
                last_command="BOOT",
                last_message="history_ready",
                updated_at=time.time(),
            )
        )
        workflow_event_state_path = (
            Path(mission_workflow_events_file).expanduser()
            if mission_workflow_events_file.strip()
            else MissionWorkflowEventStateStore.default_path()
        )
        self.workflow_event_state_store = MissionWorkflowEventStateStore(
            workflow_event_state_path
        )
        loaded_workflow_event_state = self.workflow_event_state_store.load()
        if loaded_workflow_event_state is None:
            self.workflow_event_state = build_initial_workflow_event_state(
                mission_workflow_event_retention_limit
            )
        else:
            self.workflow_event_state = sanitize_workflow_event_state_for_runtime(
                loaded_workflow_event_state,
                retention_limit=mission_workflow_event_retention_limit,
            )
        self._workflow_event_lock = threading.Lock()
        self._save_workflow_event_state(self.workflow_event_state)
        self._mission_lock = threading.Lock()
        loaded = self.state_store.load()
        if loaded is not None:
            self.node.get_logger().info(
                "mission_state_loaded: "
                f"key={loaded.mission_key} state={loaded.state} "
                f"next_segment_index={loaded.next_segment_index} "
                f"result_code={loaded.result_code}"
            )
            self.node.get_logger().info(
                "mission_orchestrator_loaded: "
                f"{self.orchestrator_state.summary()}"
            )
        self.node.get_logger().info(
            "mission_queue_replay_loaded: "
            f"{self.queue_replay_state.summary()}"
        )
        self.node.get_logger().info(
            "mission_task_history_loaded: "
            f"{self.task_history_state.summary()}"
        )
        self.node.get_logger().info(
            "mission_workflow_events_loaded: "
            f"{self.workflow_event_state.summary()}"
        )

    def _admit_mission_slot(self) -> bool:
        return self._mission_lock.acquire(blocking=False)

    def _release_mission_slot(self) -> None:
        self._mission_lock.release()

    def execute(self, goal_handle) -> Any:
        request = goal_handle.request
        try:
            goal_spec = validate_mission_goal(
                MissionGoalSpec(
                    start_id=int(request.start_id),
                    goal_id=int(request.goal_id),
                    graph_file=str(request.graph_file),
                    route_frame_id=str(request.route_frame_id),
                    expected_stair_duration_sec=float(
                        request.expected_stair_duration_sec
                    ),
                    result_timeout_sec=float(request.result_timeout_sec),
                    flat_result_timeout_sec=float(request.flat_result_timeout_sec),
                    priority=int(getattr(request, "priority", 0)),
                    assigned_robot_id=str(getattr(request, "assigned_robot_id", "")),
                )
            )
        except ValueError as exc:
            return self._finish(
                goal_handle,
                success=False,
                result_code="MISSION_INVALID_GOAL",
                message=str(exc),
                segment_count=0,
                segment_summary="",
            )

        assignment = evaluate_mission_assignment(
            local_robot_id=getattr(self, "mission_robot_id", ""),
            requested_robot_id=goal_spec.assigned_robot_id,
        )
        if not assignment.accepted:
            self.node.get_logger().info(
                "mission_assignment_rejected: "
                f"{assignment.summary()}"
            )
            return self._finish(
                goal_handle,
                success=False,
                result_code="MISSION_ASSIGNMENT_REJECTED",
                message=assignment.message,
                segment_count=0,
                segment_summary="",
            )
        goal_spec = replace(
            goal_spec,
            assigned_robot_id=assignment.assigned_robot_id,
        )

        mission_key = build_mission_key(
            start_id=goal_spec.start_id,
            goal_id=goal_spec.goal_id,
            graph_file=goal_spec.graph_file,
            route_frame_id=goal_spec.route_frame_id,
        )

        if self._orchestrator_is_paused():
            self.node.get_logger().info(
                "mission_paused: "
                f"key={mission_key} state={self.orchestrator_state.summary()}"
            )
            return self._finish(
                goal_handle,
                success=False,
                result_code="MISSION_BUSY",
                message="mission_paused",
                segment_count=0,
                segment_summary="",
            )

        queue_replay_state = self._queue_replay_state_snapshot()
        if queue_replay_state.queue_replay_pending:
            self.node.get_logger().info(
                "mission_queue_replay_pending: "
                f"key={mission_key} state={queue_replay_state.summary()}"
            )
            return self._finish(
                goal_handle,
                success=False,
                result_code="MISSION_BUSY",
                message="mission_queue_replay_pending",
                segment_count=0,
                segment_summary="",
            )

        replay_record = queue_replay_state.find_record(mission_key)
        queue_record = replay_record
        if replay_record is not None:
            admission = MissionQueueAdmission(
                accepted=True,
                ticket=replay_record.ticket,
                queue_position=replay_record.queue_position,
                queued=replay_record.state == QUEUED_STATE,
                priority=replay_record.priority,
            )
            self.node.get_logger().info(
                "mission_queue_replayed: "
                f"key={mission_key} ticket={admission.ticket} "
                f"queue_position={admission.queue_position} "
                f"priority={admission.priority} "
                f"state={replay_record.state}"
            )
        else:
            admission = self.mission_scheduler.reserve(priority=goal_spec.priority)
            if not admission.accepted:
                self.node.get_logger().info(
                    "mission_busy: mission_queue_full"
                )
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_BUSY",
                    message="mission_queue_full",
                    segment_count=0,
                    segment_summary="",
                )
            queue_record = self._queue_record_for_goal(
                mission_key=mission_key,
                ticket=admission.ticket,
                queue_position=admission.queue_position,
                goal_spec=goal_spec,
                state=QUEUED_STATE,
                last_command="ADMIT",
                last_message=(
                    f"ticket={admission.ticket} queued={admission.queued}"
                ),
            )

        mission_lock_acquired = False
        active_mission_registered = False
        try:
            self._save_orchestrator_state(
                self.orchestrator_state.with_updates(
                    last_command="ADMIT",
                    last_message=(
                        f"ticket={admission.ticket} queued={admission.queued}"
                    ),
                    updated_at=time.time(),
                ),
                queue_snapshot=self.mission_scheduler.snapshot(),
            )
            if replay_record is None:
                self._upsert_queue_record(queue_record)
            self._set_task_history_context(
                self._task_history_context_for_queue_record(queue_record)
            )
            self._append_workflow_event(
                "ADMIT",
                f"ticket={admission.ticket} queued={admission.queued}",
                mission_key=mission_key,
                ticket=admission.ticket,
            )
            if admission.queued:
                self.node.get_logger().info(
                    "mission_queued: "
                    f"key={mission_key} ticket={admission.ticket} "
                    f"queue_position={admission.queue_position} "
                    f"priority={admission.priority}"
                )
                goal_handle.publish_feedback(
                    self._feedback("QUEUED", 0, "", "", 0.0)
                )

            if not self.mission_scheduler.wait_for_turn(
                admission.ticket,
                lambda: goal_handle.is_cancel_requested,
                can_activate=lambda: not self._orchestrator_is_paused(),
                poll_timeout_sec=0.1,
            ):
                self._remove_queue_record(
                    mission_key,
                    last_command="CANCEL",
                    last_message="mission_queue_canceled",
                )
                self.node.get_logger().info(
                    "mission_queue_canceled: "
                    f"key={mission_key} ticket={admission.ticket}"
                )
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_CANCELED",
                    message="mission_queue_canceled",
                    segment_count=0,
                    segment_summary="",
                )

            if not self._mission_lock.acquire(blocking=False):
                self.node.get_logger().warning(
                    "mission_internal_lock_busy: "
                    f"key={mission_key} ticket={admission.ticket}"
                )
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_BUSY",
                    message="mission_state_in_use",
                    segment_count=0,
                    segment_summary="",
                )
            mission_lock_acquired = True
            self._register_active_mission(
                mission_key=mission_key,
                ticket=admission.ticket,
                last_command="ACTIVE",
                last_message="mission_active",
            )
            self._append_workflow_event(
                "ACTIVE",
                "mission_active",
                mission_key=mission_key,
                ticket=admission.ticket,
            )
            active_mission_registered = True
            self._touch_task_history_context(activated_at=time.time())
            self._upsert_queue_record(
                self._queue_record_for_goal(
                    mission_key=mission_key,
                    ticket=admission.ticket,
                    queue_position=admission.queue_position,
                    goal_spec=goal_spec,
                    state=ACTIVE_STATE,
                    last_command="ACTIVE",
                    last_message="mission_active",
                )
            )

            if self._mission_cancel_requested(goal_handle):
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_CANCELED",
                    message="mission_operator_canceled",
                    segment_count=0,
                    segment_summary="",
                )

            goal_handle.publish_feedback(
                self._feedback("SCHEDULED", 0, "", "", 0.0)
            )

            if not Path(goal_spec.graph_file).exists():
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_INVALID_GOAL",
                    message=f"graph_missing:{goal_spec.graph_file}",
                    segment_count=0,
                    segment_summary="",
                )

            try:
                graph = Phase4ARouteGraph.from_file(goal_spec.graph_file)
            except (OSError, ValueError, KeyError) as exc:
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_INVALID_GOAL",
                    message=f"graph_load_failed:{exc}",
                    segment_count=0,
                    segment_summary="",
                )

            mismatches = graph.geometry_mismatches()
            if mismatches:
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_INVALID_GOAL",
                    message="graph_geometry_mismatch",
                    segment_count=0,
                    segment_summary="",
                )

            existing_checkpoint = self.state_store.load()
            if (
                existing_checkpoint is not None
                and existing_checkpoint.mission_key != mission_key
                and existing_checkpoint.state not in {"SUCCEEDED", "FAILED", "CANCELED"}
            ):
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_BUSY",
                    message="mission_state_in_use",
                    segment_count=0,
                    segment_summary="",
                )

            goal_handle.publish_feedback(
                self._feedback("ROUTE_REQUESTED", 0, "", "", 0.0)
            )
            route_result = self._compute_route_edge_ids(goal_handle, goal_spec)
            if not route_result["success"]:
                state = (
                    "RECOVERABLE"
                    if self.mission_recovery_enabled
                    and is_recoverable_result_code(route_result["result_code"])
                    else "FAILED"
                )
                self._save_checkpoint(
                    checkpoint_for_goal(
                        mission_key=mission_key,
                        state=state,
                        start_id=goal_spec.start_id,
                        goal_id=goal_spec.goal_id,
                        graph_file=goal_spec.graph_file,
                        route_frame_id=goal_spec.route_frame_id,
                        segment_summary="",
                        route_edge_ids=(),
                        next_segment_index=0,
                        current_segment_index=0,
                        current_segment_type="",
                        active_owner="flat",
                        result_code=route_result["result_code"],
                        message=route_result["message"],
                        retry_count=0,
                    )
                )
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code=route_result["result_code"],
                    message=route_result["message"],
                    segment_count=0,
                    segment_summary="",
                )
            route_edge_ids = tuple(route_result["edge_ids"])

            try:
                segments = build_mission_segments(graph, route_edge_ids)
            except ValueError as exc:
                self._save_checkpoint(
                    checkpoint_for_goal(
                        mission_key=mission_key,
                        state="FAILED",
                        start_id=goal_spec.start_id,
                        goal_id=goal_spec.goal_id,
                        graph_file=goal_spec.graph_file,
                        route_frame_id=goal_spec.route_frame_id,
                        segment_summary="",
                        route_edge_ids=route_edge_ids,
                        next_segment_index=0,
                        current_segment_index=0,
                        current_segment_type="",
                        active_owner="flat",
                        result_code="MISSION_CONNECTOR_UNAVAILABLE",
                        message=str(exc),
                        retry_count=0,
                    )
                )
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_CONNECTOR_UNAVAILABLE",
                    message=str(exc),
                    segment_count=0,
                    segment_summary="",
                )
            if not segments:
                self._save_checkpoint(
                    checkpoint_for_goal(
                        mission_key=mission_key,
                        state="FAILED",
                        start_id=goal_spec.start_id,
                        goal_id=goal_spec.goal_id,
                        graph_file=goal_spec.graph_file,
                        route_frame_id=goal_spec.route_frame_id,
                        segment_summary="",
                        route_edge_ids=route_edge_ids,
                        next_segment_index=0,
                        current_segment_index=0,
                        current_segment_type="",
                        active_owner="flat",
                        result_code="MISSION_CONNECTOR_UNAVAILABLE",
                        message="no_segments",
                        retry_count=0,
                    )
                )
                return self._finish(
                    goal_handle,
                    success=False,
                    result_code="MISSION_CONNECTOR_UNAVAILABLE",
                    message="no_segments",
                    segment_count=0,
                    segment_summary="",
                )

            segment_summary = summarize_segments(segments)
            goal_handle.publish_feedback(
                self._feedback("SEGMENTS_READY", 0, "", "", 0.0)
            )
            checkpoint = existing_checkpoint
            resume_from = 0
            if self.mission_recovery_enabled and should_resume_checkpoint(
                checkpoint,
                mission_key=mission_key,
            ):
                if (
                    checkpoint.segment_summary
                    and checkpoint.segment_summary != segment_summary
                ) or tuple(checkpoint.route_edge_ids) != route_edge_ids:
                    return self._finish(
                        goal_handle,
                        success=False,
                        result_code="MISSION_INVALID_GOAL",
                        message="mission_checkpoint_mismatch",
                        segment_count=0,
                        segment_summary="",
                    )
                resume_from = min(max(0, checkpoint.next_segment_index), len(segments))
                self.node.get_logger().info(
                    "mission_recovery_resume: "
                    f"key={mission_key} resume_from={resume_from} "
                    f"state={checkpoint.state} retry_count={checkpoint.retry_count}"
                )
                goal_handle.publish_feedback(
                    self._feedback("RECOVERING", resume_from, "", "", 0.0)
                )

            self._save_checkpoint(
                checkpoint_for_goal(
                    mission_key=mission_key,
                    state="RUNNING",
                    start_id=goal_spec.start_id,
                    goal_id=goal_spec.goal_id,
                    graph_file=goal_spec.graph_file,
                    route_frame_id=goal_spec.route_frame_id,
                    segment_summary=segment_summary,
                    route_edge_ids=route_edge_ids,
                    next_segment_index=resume_from,
                    current_segment_index=max(0, resume_from - 1),
                    current_segment_type="",
                    active_owner="flat",
                    result_code="MISSION_SUCCEEDED",
                    message="mission_running",
                    retry_count=0,
                )
            )
            mission_result = self._execute_segments(
                goal_handle,
                graph,
                goal_spec,
                segments,
                mission_key=mission_key,
                segment_summary=segment_summary,
                start_index=resume_from,
                route_edge_ids=route_edge_ids,
            )
            goal_handle.publish_feedback(
                self._feedback(
                    "MISSION_COMPLETE",
                    len(segments),
                    "",
                    "",
                    1.0 if mission_result["success"] else 0.0,
                )
            )
            if mission_result["success"]:
                self._save_checkpoint(
                    checkpoint_for_goal(
                        mission_key=mission_key,
                        state="SUCCEEDED",
                        start_id=goal_spec.start_id,
                        goal_id=goal_spec.goal_id,
                        graph_file=goal_spec.graph_file,
                        route_frame_id=goal_spec.route_frame_id,
                        segment_summary=segment_summary,
                        route_edge_ids=route_edge_ids,
                        next_segment_index=len(segments),
                        current_segment_index=mission_result["current_segment_index"],
                        current_segment_type=mission_result["current_segment_type"],
                        active_owner=mission_result["active_owner"],
                        result_code=mission_result["result_code"],
                        message=mission_result["message"],
                        retry_count=mission_result["retry_count"],
                    )
                )
            return self._finish(
                goal_handle,
                success=mission_result["success"],
                result_code=mission_result["result_code"],
                message=mission_result["message"],
                segment_count=len(segments),
                segment_summary=segment_summary,
            )
        finally:
            if mission_lock_acquired:
                self._mission_lock.release()
            self.mission_scheduler.release(admission.ticket)
            if active_mission_registered:
                self._clear_active_mission(
                    last_command="COMPLETE",
                    last_message="mission_finished",
                )
                self._remove_queue_record(
                    mission_key,
                    last_command="COMPLETE",
                    last_message="mission_finished",
                )
            else:
                self._save_orchestrator_state(
                    self.orchestrator_state.with_updates(
                        last_command="COMPLETE",
                        last_message="mission_finished",
                        updated_at=time.time(),
                    ),
                    queue_snapshot=self.mission_scheduler.snapshot(),
                )
            self._clear_task_history_context()

    def _save_checkpoint(self, checkpoint: MissionCheckpoint) -> None:
        self.state_store.save(checkpoint)
        self.node.get_logger().info(
            "mission_checkpoint: "
            f"key={checkpoint.mission_key} state={checkpoint.state} "
            f"next_segment_index={checkpoint.next_segment_index} "
            f"current_segment_index={checkpoint.current_segment_index} "
            f"current_segment_type={checkpoint.current_segment_type} "
            f"active_owner={checkpoint.active_owner} "
            f"result_code={checkpoint.result_code} "
            f"retry_count={checkpoint.retry_count}"
        )

    def _orchestrator_state_snapshot(self) -> MissionOrchestratorState:
        with self._orchestrator_state_lock:
            return self.orchestrator_state

    def _orchestrator_is_paused(self) -> bool:
        return self._orchestrator_state_snapshot().paused

    def _save_orchestrator_state(
        self,
        state: MissionOrchestratorState,
        *,
        queue_snapshot=None,
    ) -> MissionOrchestratorState:
        with self._orchestrator_state_lock:
            if queue_snapshot is not None:
                state = state.with_updates(
                    queue_capacity=queue_snapshot.capacity,
                    queued_tickets=tuple(queue_snapshot.queued_tickets),
                    queued_priorities=tuple(queue_snapshot.queued_priorities),
                )
            self.orchestrator_state = state
            self.orchestrator_state_store.save(state)
            return state

    def _queue_replay_state_snapshot(self) -> MissionQueueReplayState:
        with self._queue_replay_lock:
            return self.queue_replay_state

    def _queue_replay_summary(self) -> str:
        return self._queue_replay_state_snapshot().summary()

    def _queue_replay_is_pending(self) -> bool:
        return self._queue_replay_state_snapshot().queue_replay_pending

    def _save_queue_replay_state(
        self,
        state: MissionQueueReplayState,
    ) -> MissionQueueReplayState:
        with self._queue_replay_lock:
            self.queue_replay_state = state
            self.queue_replay_state_store.save(state)
            return state

    def _task_history_state_snapshot(self) -> MissionTaskHistoryState:
        with self._task_history_lock:
            return self.task_history_state

    def _task_history_summary(self) -> str:
        return self._task_history_state_snapshot().summary()

    def _task_history_context_snapshot(
        self,
    ) -> MissionTaskHistoryContext | None:
        with self._task_history_lock:
            return self._task_history_context

    def _set_task_history_context(
        self,
        context: MissionTaskHistoryContext,
    ) -> MissionTaskHistoryContext:
        with self._task_history_lock:
            self._task_history_context = context
            return context

    def _touch_task_history_context(
        self,
        *,
        activated_at: float | None = None,
    ) -> MissionTaskHistoryContext | None:
        with self._task_history_lock:
            if self._task_history_context is None:
                return None
            updates: dict[str, Any] = {}
            if activated_at is not None:
                updates["activated_at"] = float(activated_at)
            if updates:
                self._task_history_context = self._task_history_context.with_updates(
                    **updates
                )
            return self._task_history_context

    def _clear_task_history_context(self) -> None:
        with self._task_history_lock:
            self._task_history_context = None

    def _save_task_history_state(
        self,
        state: MissionTaskHistoryState,
    ) -> MissionTaskHistoryState:
        with self._task_history_lock:
            self.task_history_state = state
            self.task_history_state_store.save(state)
            return state

    def _workflow_event_state_snapshot(self) -> MissionWorkflowEventState:
        if not hasattr(self, "workflow_event_state"):
            return build_initial_workflow_event_state(1)
        with self._workflow_event_lock:
            return self.workflow_event_state

    def _save_workflow_event_state(
        self,
        state: MissionWorkflowEventState,
    ) -> MissionWorkflowEventState:
        with self._workflow_event_lock:
            self.workflow_event_state = state
            self.workflow_event_state_store.save(state)
            return state

    def _append_workflow_event(
        self,
        event_type: str,
        message: str,
        *,
        mission_key: str = "",
        ticket: int = -1,
    ) -> MissionWorkflowEventState | None:
        if not hasattr(self, "workflow_event_state"):
            return None
        mode = self._orchestrator_state_snapshot().mode
        with self._workflow_event_lock:
            event = MissionWorkflowEvent(
                event_id=self.workflow_event_state.next_event_id,
                event_type=event_type,
                mission_key=mission_key,
                ticket=ticket,
                mode=mode,
                message=message,
                created_at=time.time(),
            )
            updated_state = self.workflow_event_state.append_event(event)
            self.workflow_event_state = updated_state
            self.workflow_event_state_store.save(updated_state)
            return updated_state

    def _workflow_events_summary(self) -> str:
        return self._workflow_event_state_snapshot().summary()

    def _task_history_context_for_queue_record(
        self,
        record: MissionQueueRecord,
    ) -> MissionTaskHistoryContext:
        admitted_at = float(record.admitted_at)
        return MissionTaskHistoryContext(
            run_id=build_mission_run_id(
                record.mission_key,
                record.ticket,
                admitted_at,
            ),
            mission_key=record.mission_key,
            ticket=record.ticket,
            queue_position=record.queue_position,
            priority=record.priority,
            assigned_robot_id=record.assigned_robot_id,
            start_id=record.start_id,
            goal_id=record.goal_id,
            graph_file=record.graph_file,
            route_frame_id=record.route_frame_id,
            admitted_at=admitted_at,
            activated_at=0.0,
        )

    def _append_task_history_record(
        self,
        *,
        success: bool,
        result_code: str,
        message: str,
        segment_count: int,
        segment_summary: str,
    ) -> None:
        context = self._task_history_context_snapshot()
        if context is None:
            return
        now = time.time()
        last_command = "CANCEL" if result_code == "MISSION_CANCELED" else "COMPLETE"
        record = MissionTaskHistoryRecord(
            run_id=context.run_id,
            mission_key=context.mission_key,
            ticket=context.ticket,
            queue_position=context.queue_position,
            priority=context.priority,
            assigned_robot_id=context.assigned_robot_id,
            state=mission_history_state_for_result(
                success=success,
                result_code=result_code,
            ),
            result_code=result_code,
            message=message,
            start_id=context.start_id,
            goal_id=context.goal_id,
            graph_file=context.graph_file,
            route_frame_id=context.route_frame_id,
            segment_count=int(segment_count),
            segment_summary=segment_summary,
            admitted_at=context.admitted_at,
            activated_at=context.activated_at,
            completed_at=now,
            last_command=last_command,
            last_message=message,
            updated_at=now,
        )
        updated_state = self._task_history_state_snapshot().append_record(
            record
        ).with_updates(
            last_command=last_command,
            last_message=message,
            updated_at=now,
        )
        self._save_task_history_state(updated_state)
        self._append_workflow_event(
            last_command,
            message,
            mission_key=context.mission_key,
            ticket=context.ticket,
        )

    def _archive_task_history(
        self,
        retain_limit: int,
        *,
        last_command: str,
        last_message: str,
    ) -> MissionTaskHistoryState:
        archived_state = self._task_history_state_snapshot().archive_to_limit(
            retain_limit
        ).with_updates(
            last_command=last_command,
            last_message=last_message,
            updated_at=time.time(),
        )
        return self._save_task_history_state(archived_state)

    def _parse_task_history_retain_limit(self, reason: str) -> int:
        match = re.search(r"retain\s*=\s*(\d+)", str(reason))
        if match is not None:
            return max(1, int(match.group(1)))
        return self._task_history_state_snapshot().retention_limit

    def _queue_record_for_goal(
        self,
        *,
        mission_key: str,
        ticket: int,
        queue_position: int,
        goal_spec: MissionGoalSpec,
        state: str,
        last_command: str,
        last_message: str,
    ) -> MissionQueueRecord:
        now = time.time()
        return MissionQueueRecord(
            mission_key=mission_key,
            ticket=ticket,
            queue_position=queue_position,
            priority=goal_spec.priority,
            assigned_robot_id=goal_spec.assigned_robot_id,
            state=state,
            start_id=goal_spec.start_id,
            goal_id=goal_spec.goal_id,
            graph_file=goal_spec.graph_file,
            route_frame_id=goal_spec.route_frame_id,
            expected_stair_duration_sec=goal_spec.expected_stair_duration_sec,
            result_timeout_sec=goal_spec.result_timeout_sec,
            flat_result_timeout_sec=goal_spec.flat_result_timeout_sec,
            last_command=last_command,
            last_message=last_message,
            admitted_at=now,
            updated_at=now,
        )

    def _upsert_queue_record(
        self,
        record: MissionQueueRecord,
    ) -> MissionQueueReplayState:
        updated_state = self._queue_replay_state_snapshot().upsert_record(
            record
        ).with_updates(
            last_command=record.last_command,
            last_message=record.last_message,
            updated_at=time.time(),
        )
        if not updated_state.records:
            updated_state = updated_state.with_updates(queue_replay_pending=False)
        return self._save_queue_replay_state(updated_state)

    def _remove_queue_record(
        self,
        mission_key: str,
        *,
        last_command: str,
        last_message: str,
    ) -> MissionQueueReplayState:
        current_state = self._queue_replay_state_snapshot()
        pruned_state = current_state.remove_record(mission_key)
        updated_state = pruned_state.with_updates(
            last_command=last_command,
            last_message=last_message,
            updated_at=time.time(),
            queue_replay_pending=current_state.queue_replay_pending
            if pruned_state.records
            else False,
        )
        return self._save_queue_replay_state(updated_state)

    def _restore_queue_replay_scheduler(self) -> None:
        state = self._queue_replay_state_snapshot()
        self.mission_scheduler.restore(
            active_ticket=state.active_ticket if state.active_ticket >= 0 else None,
            queued_tickets=state.queued_tickets,
            next_ticket=state.next_ticket,
            ticket_priorities=state.ticket_priorities(),
            active_priority=state.ticket_priorities().get(state.active_ticket, 0),
        )

    def _combined_state_summary(
        self,
        state: MissionOrchestratorState | None = None,
    ) -> str:
        current_state = state or self._orchestrator_state_snapshot()
        queue_state = self._queue_replay_state_snapshot()
        task_history_state = self._task_history_state_snapshot()
        return (
            f"{self._assignment_summary()} "
            f"{self._workflow_summary(current_state, queue_state, task_history_state)} "
            f"{self._workflow_events_summary()} "
            f"{current_state.summary()} "
            f"queue_replay={queue_state.summary()} "
            f"task_history={task_history_state.summary()}"
        )

    def _assignment_summary(self) -> str:
        return (
            "assignment=local_robot="
            f"{normalize_robot_id(getattr(self, 'mission_robot_id', ''))}"
        )

    def _workflow_summary(
        self,
        state: MissionOrchestratorState | None = None,
        queue_state: MissionQueueReplayState | None = None,
        task_history_state: MissionTaskHistoryState | None = None,
    ) -> str:
        snapshot = build_mission_workflow_snapshot(
            state or self._orchestrator_state_snapshot(),
            queue_state or self._queue_replay_state_snapshot(),
            task_history_state or self._task_history_state_snapshot(),
        )
        return snapshot.summary()

    def _register_active_mission(
        self,
        *,
        mission_key: str,
        ticket: int,
        last_command: str,
        last_message: str,
    ) -> MissionOrchestratorState:
        return self._save_orchestrator_state(
            self.orchestrator_state.with_updates(
                active_mission_key=mission_key,
                active_ticket=ticket,
                last_command=last_command,
                last_message=last_message,
                updated_at=time.time(),
            ),
            queue_snapshot=self.mission_scheduler.snapshot(),
        )

    def _clear_active_mission(
        self,
        *,
        last_command: str,
        last_message: str,
    ) -> MissionOrchestratorState:
        self._operator_cancel_active.clear()
        return self._save_orchestrator_state(
            self.orchestrator_state.with_updates(
                active_mission_key="",
                active_ticket=-1,
                last_command=last_command,
                last_message=last_message,
                updated_at=time.time(),
            ),
            queue_snapshot=self.mission_scheduler.snapshot(),
        )

    def _mission_cancel_requested(self, goal_handle) -> bool:
        return goal_handle.is_cancel_requested or self._operator_cancel_active.is_set()

    def handle_orchestrator_command(self, command: str, reason: str = "") -> dict[str, Any]:
        normalized_command = str(command).strip().lower()
        normalized_reason = str(reason).strip()
        current_state = self._orchestrator_state_snapshot()

        if normalized_command == "status":
            return {
                "accepted": True,
                "mode": current_state.mode,
                "message": "snapshot",
                "state_summary": self._combined_state_summary(current_state),
            }

        if normalized_command == "workflow":
            return {
                "accepted": True,
                "mode": current_state.mode,
                "message": "workflow_snapshot",
                "state_summary": self._combined_state_summary(current_state),
            }

        if normalized_command == "workflow_events":
            return {
                "accepted": True,
                "mode": current_state.mode,
                "message": "workflow_events_snapshot",
                "state_summary": self._combined_state_summary(current_state),
            }

        if normalized_command == "pause":
            updated_state = self._save_orchestrator_state(
                current_state.with_updates(
                    mode=PAUSED_MODE,
                    pause_reason=normalized_reason or "operator_pause",
                    last_command="pause",
                    last_message=normalized_reason or "operator_pause",
                    updated_at=time.time(),
                ),
                queue_snapshot=self.mission_scheduler.snapshot(),
            )
            self._append_workflow_event("CONTROL", "mission_paused")
            return {
                "accepted": True,
                "mode": updated_state.mode,
                "message": "mission_paused",
                "state_summary": self._combined_state_summary(updated_state),
            }

        if normalized_command == "resume":
            updated_state = self._save_orchestrator_state(
                current_state.with_updates(
                    mode=OPEN_MODE,
                    pause_reason="",
                    last_command="resume",
                    last_message=normalized_reason or "operator_resume",
                    updated_at=time.time(),
                ),
                queue_snapshot=self.mission_scheduler.snapshot(),
            )
            self._append_workflow_event("CONTROL", "mission_resumed")
            return {
                "accepted": True,
                "mode": updated_state.mode,
                "message": "mission_resumed",
                "state_summary": self._combined_state_summary(updated_state),
            }

        if normalized_command == "cancel_active":
            if not current_state.active_mission_key:
                return {
                    "accepted": False,
                    "mode": current_state.mode,
                    "message": "no_active_mission",
                    "state_summary": self._combined_state_summary(current_state),
                }
            self._operator_cancel_active.set()
            updated_state = self._save_orchestrator_state(
                current_state.with_updates(
                    last_command="cancel_active",
                    last_message=normalized_reason or "operator_cancel_active",
                    updated_at=time.time(),
                ),
                queue_snapshot=self.mission_scheduler.snapshot(),
            )
            self._append_workflow_event(
                "CONTROL",
                "operator_cancel_active_requested",
                mission_key=current_state.active_mission_key,
                ticket=current_state.active_ticket,
            )
            return {
                "accepted": True,
                "mode": updated_state.mode,
                "message": "operator_cancel_active_requested",
                "state_summary": self._combined_state_summary(updated_state),
            }

        if normalized_command == "replay_queue":
            queue_state = self._queue_replay_state_snapshot()
            if not queue_state.records:
                return {
                    "accepted": False,
                    "mode": current_state.mode,
                    "message": "no_replay_records",
                    "state_summary": self._combined_state_summary(current_state),
                }
            if not queue_state.queue_replay_pending:
                return {
                    "accepted": False,
                    "mode": current_state.mode,
                    "message": "queue_replay_not_pending",
                    "state_summary": self._combined_state_summary(current_state),
                }
            self._restore_queue_replay_scheduler()
            updated_queue_state = self._save_queue_replay_state(
                queue_state.with_updates(
                    queue_replay_pending=False,
                    last_command="replay_queue",
                    last_message=normalized_reason or "queue_replay_acknowledged",
                    updated_at=time.time(),
                )
            )
            updated_state = self._save_orchestrator_state(
                current_state.with_updates(
                    last_command="replay_queue",
                    last_message=normalized_reason or "queue_replay_acknowledged",
                    updated_at=time.time(),
                ),
                queue_snapshot=self.mission_scheduler.snapshot(),
            )
            self._append_workflow_event("CONTROL", "queue_replayed")
            return {
                "accepted": True,
                "mode": updated_state.mode,
                "message": "queue_replayed",
                "state_summary": self._combined_state_summary(updated_state),
            }

        if normalized_command == "history":
            return {
                "accepted": True,
                "mode": current_state.mode,
                "message": "history_snapshot",
                "state_summary": self._combined_state_summary(current_state),
            }

        if normalized_command == "archive_history":
            current_history_state = self._task_history_state_snapshot()
            if current_history_state.record_count == 0:
                return {
                    "accepted": False,
                    "mode": current_state.mode,
                    "message": "no_history_records",
                    "state_summary": self._combined_state_summary(current_state),
                }
            retain_limit = self._parse_task_history_retain_limit(
                normalized_reason
            )
            updated_history_state = self._archive_task_history(
                retain_limit,
                last_command="archive_history",
                last_message=normalized_reason or f"retain={retain_limit}",
            )
            updated_state = self._save_orchestrator_state(
                current_state.with_updates(
                    last_command="archive_history",
                    last_message=normalized_reason or f"retain={retain_limit}",
                    updated_at=time.time(),
                ),
                queue_snapshot=self.mission_scheduler.snapshot(),
            )
            self._append_workflow_event("CONTROL", "history_archived")
            return {
                "accepted": True,
                "mode": updated_state.mode,
                "message": "history_archived",
                "state_summary": self._combined_state_summary(updated_state),
            }

        return {
            "accepted": False,
            "mode": current_state.mode,
            "message": "unsupported_command",
            "state_summary": self._combined_state_summary(current_state),
        }

    def _compute_route_edge_ids(
        self,
        mission_goal_handle,
        goal_spec: MissionGoalSpec,
    ) -> dict[str, Any]:
        from nav2_msgs.action import ComputeRoute
        from action_msgs.msg import GoalStatus

        if not self.compute_route_client.wait_for_server(timeout_sec=5.0):
            return {
                "success": False,
                "result_code": "MISSION_ROUTE_UNAVAILABLE",
                "message": "route_server_unavailable",
                "edge_ids": [],
            }
        goal = ComputeRoute.Goal()
        goal.start_id = goal_spec.start_id
        goal.goal_id = goal_spec.goal_id
        goal.use_start = False
        goal.use_poses = False
        send_future = self.compute_route_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            return {
                "success": False,
                "result_code": "MISSION_TIMEOUT",
                "message": "route_goal_response_timeout",
                "edge_ids": [],
            }
        child_goal_handle = send_future.result()
        if child_goal_handle is None or not child_goal_handle.accepted:
            return {
                "success": False,
                "result_code": "MISSION_ROUTE_UNAVAILABLE",
                "message": "route_goal_rejected",
                "edge_ids": [],
            }
        result_future = child_goal_handle.get_result_async()
        if not _spin_until_or_cancel(
            self.node,
            result_future,
            10.0,
            cancel_requested=lambda: self._mission_cancel_requested(
                mission_goal_handle
            ),
        ) == "DONE":
            child_goal_handle.cancel_goal_async()
            if self._mission_cancel_requested(mission_goal_handle):
                return {
                    "success": False,
                    "result_code": "MISSION_CANCELED",
                    "message": "mission_canceled",
                    "edge_ids": [],
                }
            return {
                "success": False,
                "result_code": "MISSION_TIMEOUT",
                "message": "route_timeout",
                "edge_ids": [],
            }
        wrapped = result_future.result()
        if wrapped.status == GoalStatus.STATUS_CANCELED:
            return {
                "success": False,
                "result_code": "MISSION_CANCELED",
                "message": "mission_canceled",
                "edge_ids": [],
            }
        if wrapped.status != GoalStatus.STATUS_SUCCEEDED:
            return {
                "success": False,
                "result_code": "MISSION_ROUTE_UNAVAILABLE",
                "message": "route_failed",
                "edge_ids": [],
            }
        edge_ids = [int(edge.edgeid) for edge in wrapped.result.route.edges]
        if not edge_ids:
            return {
                "success": False,
                "result_code": "MISSION_ROUTE_UNAVAILABLE",
                "message": "route_empty",
                "edge_ids": [],
            }
        return {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "route_computed",
            "edge_ids": edge_ids,
        }

    def _execute_segments(
        self,
        goal_handle,
        graph: Phase4ARouteGraph,
        goal_spec: MissionGoalSpec,
        segments: list[MissionSegment],
        *,
        mission_key: str,
        segment_summary: str,
        start_index: int,
        route_edge_ids: tuple[int, ...],
    ) -> dict[str, Any]:
        retry_count = 0
        total_segments = len(segments)
        for index in range(start_index, total_segments):
            segment = segments[index]
            owner = "stair" if segment.segment_type == "stair" else "flat"
            active_state = (
                "STAIR_SEGMENT_ACTIVE" if owner == "stair" else "FLAT_SEGMENT_ACTIVE"
            )
            self._save_checkpoint(
                checkpoint_for_goal(
                    mission_key=mission_key,
                    state="SEGMENT_ACTIVE",
                    start_id=goal_spec.start_id,
                    goal_id=goal_spec.goal_id,
                    graph_file=goal_spec.graph_file,
                    route_frame_id=goal_spec.route_frame_id,
                    segment_summary=segment_summary,
                    route_edge_ids=route_edge_ids,
                    next_segment_index=index,
                    current_segment_index=index,
                    current_segment_type=segment.segment_type,
                    active_owner=owner,
                    result_code="MISSION_SUCCEEDED",
                    message="segment_active",
                    retry_count=retry_count,
                )
            )
            goal_handle.publish_feedback(
                self._feedback(
                    active_state,
                    index,
                    segment.segment_type,
                    owner,
                    float(index) / max(1.0, float(total_segments)),
                )
            )

            attempt = 0
            while True:
                if self._mission_cancel_requested(goal_handle):
                    self._save_checkpoint(
                        checkpoint_for_goal(
                            mission_key=mission_key,
                            state="CANCELED",
                            start_id=goal_spec.start_id,
                            goal_id=goal_spec.goal_id,
                            graph_file=goal_spec.graph_file,
                            route_frame_id=goal_spec.route_frame_id,
                            segment_summary=segment_summary,
                            route_edge_ids=route_edge_ids,
                            next_segment_index=index,
                            current_segment_index=index,
                            current_segment_type=segment.segment_type,
                            active_owner=owner,
                            result_code="MISSION_CANCELED",
                            message="mission_canceled",
                            retry_count=retry_count,
                        )
                    )
                    return {
                        "success": False,
                        "result_code": "MISSION_CANCELED",
                        "message": "mission_canceled",
                        "current_segment_index": index,
                        "current_segment_type": segment.segment_type,
                        "active_owner": owner,
                        "next_segment_index": index,
                        "retry_count": retry_count,
                    }

                if segment.segment_type == "flat":
                    result = self._execute_flat_segment(
                        goal_handle,
                        graph,
                        segment,
                        goal_spec,
                    )
                else:
                    result = self._execute_stair_segment(
                        goal_handle,
                        segment,
                        goal_spec,
                    )

                if result["success"]:
                    self._save_checkpoint(
                        checkpoint_for_goal(
                            mission_key=mission_key,
                            state="SEGMENT_COMPLETE",
                            start_id=goal_spec.start_id,
                            goal_id=goal_spec.goal_id,
                            graph_file=goal_spec.graph_file,
                            route_frame_id=goal_spec.route_frame_id,
                            segment_summary=segment_summary,
                            route_edge_ids=route_edge_ids,
                            next_segment_index=index + 1,
                            current_segment_index=index,
                            current_segment_type=segment.segment_type,
                            active_owner="flat",
                            result_code="MISSION_SUCCEEDED",
                            message=result["message"],
                            retry_count=retry_count,
                        )
                    )
                    goal_handle.publish_feedback(
                        self._feedback(
                            "SEGMENT_COMPLETE",
                            index,
                            segment.segment_type,
                            owner,
                            1.0,
                        )
                    )
                    break

                if (
                    result.get("recoverable", False)
                    and self.mission_recovery_enabled
                    and attempt < self.mission_retry_limit
                ):
                    attempt += 1
                    retry_count += 1
                    self._save_checkpoint(
                        checkpoint_for_goal(
                            mission_key=mission_key,
                            state="RECOVERING",
                            start_id=goal_spec.start_id,
                            goal_id=goal_spec.goal_id,
                            graph_file=goal_spec.graph_file,
                            route_frame_id=goal_spec.route_frame_id,
                            segment_summary=segment_summary,
                            route_edge_ids=route_edge_ids,
                            next_segment_index=index,
                            current_segment_index=index,
                            current_segment_type=segment.segment_type,
                            active_owner=owner,
                            result_code=result["result_code"],
                            message=result["message"],
                            retry_count=retry_count,
                        )
                    )
                    self.node.get_logger().info(
                        "mission_recovering: "
                        f"key={mission_key} segment_index={index} "
                        f"attempt={attempt} result_code={result['result_code']}"
                    )
                    time.sleep(self.mission_retry_backoff_sec)
                    continue

                state = "RECOVERABLE" if result.get("recoverable", False) else "FAILED"
                self._save_checkpoint(
                    checkpoint_for_goal(
                        mission_key=mission_key,
                        state=state,
                        start_id=goal_spec.start_id,
                        goal_id=goal_spec.goal_id,
                        graph_file=goal_spec.graph_file,
                        route_frame_id=goal_spec.route_frame_id,
                        segment_summary=segment_summary,
                        route_edge_ids=route_edge_ids,
                        next_segment_index=index,
                        current_segment_index=index,
                        current_segment_type=segment.segment_type,
                        active_owner=owner,
                        result_code=result["result_code"],
                        message=result["message"],
                        retry_count=retry_count,
                    )
                )
                return {
                    "success": False,
                    "result_code": result["result_code"],
                    "message": result["message"],
                    "current_segment_index": index,
                    "current_segment_type": segment.segment_type,
                    "active_owner": owner,
                    "next_segment_index": index,
                    "retry_count": retry_count,
                }
        return {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "mission_succeeded",
            "current_segment_index": max(0, total_segments - 1),
            "current_segment_type": segments[-1].segment_type if segments else "",
            "active_owner": "flat",
            "next_segment_index": total_segments,
            "retry_count": retry_count,
        }

    def _execute_flat_segment(
        self,
        mission_goal_handle,
        graph: Phase4ARouteGraph,
        segment: MissionSegment,
        goal_spec: MissionGoalSpec,
    ) -> dict[str, Any]:
        from go2w_mission.phase4b_mission_runtime import build_flat_goal_from_segment

        if not self.navigate_to_pose_client.wait_for_server(timeout_sec=5.0):
            return {
                "success": False,
                "result_code": "MISSION_FLAT_NAV_UNAVAILABLE",
                "message": "flat_nav_unavailable",
                "recoverable": True,
            }

        goal = self.navigate_to_pose_type.Goal()
        goal.pose = _to_pose_stamped(
            build_flat_goal_from_segment(
                graph,
                segment,
                frame_id=goal_spec.route_frame_id,
            )
        )
        configure_flat_goal_behavior_tree(goal, self.flat_behavior_tree)

        route_tracking_goal_handle = None
        route_tracking_expected_edge_id = None
        route_tracking_edges_seen: list[int] = []
        if self.route_tracking_client is not None:
            route_tracking_result = self._start_flat_route_tracking(
                graph,
                segment,
                goal_spec,
                route_tracking_edges_seen,
            )
            if not route_tracking_result["success"]:
                return route_tracking_result
            route_tracking_goal_handle = route_tracking_result["goal_handle"]
            route_tracking_expected_edge_id = route_tracking_result["expected_edge_id"]

        send_future = self.navigate_to_pose_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            self._cancel_route_tracking_goal(route_tracking_goal_handle)
            return {
                "success": False,
                "result_code": "MISSION_FLAT_FAILED",
                "message": "flat_goal_response_timeout",
                "recoverable": True,
            }
        child_goal_handle = send_future.result()
        if child_goal_handle is None or not child_goal_handle.accepted:
            self._cancel_route_tracking_goal(route_tracking_goal_handle)
            return {
                "success": False,
                "result_code": "MISSION_FLAT_FAILED",
                "message": "flat_goal_rejected",
                "recoverable": True,
            }
        result_future = child_goal_handle.get_result_async()
        wait_status = _spin_until_or_cancel(
            self.node,
            result_future,
            goal_spec.flat_result_timeout_sec,
            cancel_requested=lambda: self._mission_cancel_requested(
                mission_goal_handle
            ),
        )
        if wait_status == "CANCELED":
            self._cancel_route_tracking_goal(route_tracking_goal_handle)
            child_goal_handle.cancel_goal_async()
            return {
                "success": False,
                "result_code": "MISSION_CANCELED",
                "message": "flat_canceled",
                "recoverable": False,
            }
        if wait_status == "TIMEOUT":
            self._cancel_route_tracking_goal(route_tracking_goal_handle)
            child_goal_handle.cancel_goal_async()
            return {
                "success": False,
                "result_code": "MISSION_TIMEOUT",
                "message": "flat_timeout",
                "recoverable": True,
            }
        wrapped = result_future.result()
        from action_msgs.msg import GoalStatus

        if wrapped.status == GoalStatus.STATUS_CANCELED:
            self._cancel_route_tracking_goal(route_tracking_goal_handle)
            return {
                "success": False,
                "result_code": "MISSION_CANCELED",
                "message": "flat_canceled",
                "recoverable": False,
            }
        if wrapped.status != GoalStatus.STATUS_SUCCEEDED:
            self._cancel_route_tracking_goal(route_tracking_goal_handle)
            return {
                "success": False,
                "result_code": "MISSION_FLAT_FAILED",
                "message": "flat_failed",
                "recoverable": True,
            }
        route_tracking_validation = self._finish_flat_route_tracking(
            route_tracking_goal_handle,
            route_tracking_expected_edge_id,
            route_tracking_edges_seen,
        )
        if route_tracking_validation is not None:
            return route_tracking_validation
        return {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "flat_succeeded",
            "recoverable": False,
        }

    def _start_flat_route_tracking(
        self,
        graph: Phase4ARouteGraph,
        segment: MissionSegment,
        goal_spec: MissionGoalSpec,
        edges_seen: list[int],
    ) -> dict[str, Any]:
        if self.route_tracking_client is None:
            return {"success": True, "goal_handle": None, "expected_edge_id": None}
        if not self.route_tracking_client.wait_for_server(timeout_sec=5.0):
            return {
                "success": False,
                "result_code": "MISSION_ROUTE_TRACKING_UNAVAILABLE",
                "message": "route_tracking_unavailable",
                "recoverable": True,
            }

        start_id, goal_id = flat_route_tracking_node_ids(graph, segment)
        goal = self.compute_and_track_route_type.Goal()
        goal.start_id = start_id
        goal.goal_id = goal_id
        goal.use_start = False
        goal.use_poses = False

        def _feedback_callback(feedback_msg):
            edge_id = int(feedback_msg.feedback.current_edge_id)
            edges_seen.append(edge_id)
            self.node.get_logger().info(f"mission_route_tracking_feedback_edge: {edge_id}")
            operations = list(feedback_msg.feedback.operations_triggered)
            if operations:
                self.node.get_logger().info(
                    "mission_route_tracking_feedback_operations: "
                    + ",".join(str(operation) for operation in operations)
                )

        send_future = self.route_tracking_client.send_goal_async(
            goal,
            feedback_callback=_feedback_callback,
        )
        if not _spin_until(self.node, send_future, 10.0):
            return {
                "success": False,
                "result_code": "MISSION_ROUTE_TRACKING_FAILED",
                "message": "route_tracking_goal_response_timeout",
                "recoverable": True,
            }
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return {
                "success": False,
                "result_code": "MISSION_ROUTE_TRACKING_FAILED",
                "message": "route_tracking_goal_rejected",
                "recoverable": True,
            }
        self.node.get_logger().info("mission_route_tracking_goal: ACCEPTED")
        return {
            "success": True,
            "goal_handle": goal_handle,
            "expected_edge_id": int(segment.edge_ids[-1]),
        }

    def _finish_flat_route_tracking(
        self,
        goal_handle,
        expected_edge_id: int | None,
        edges_seen: list[int],
    ) -> dict[str, Any] | None:
        if goal_handle is None or expected_edge_id is None:
            return None
        for _ in range(20):
            import rclpy

            rclpy.spin_once(self.node, timeout_sec=0.1)
            if expected_edge_id in edges_seen:
                break
        self._cancel_route_tracking_goal(goal_handle)
        unique_edges: list[int] = []
        for edge_id in edges_seen:
            if edge_id not in unique_edges:
                unique_edges.append(edge_id)
        self.node.get_logger().info(
            "mission_route_tracking_feedback_edges: "
            + ",".join(str(edge_id) for edge_id in unique_edges)
        )
        self.node.get_logger().info(
            f"mission_route_tracking_expected_edge_id: {expected_edge_id}"
        )
        if expected_edge_id not in edges_seen:
            self.node.get_logger().info("mission_route_tracking_result: FAIL")
            return {
                "success": False,
                "result_code": "MISSION_ROUTE_TRACKING_FAILED",
                "message": "route_tracking_missing_expected_edge",
                "recoverable": True,
            }
        self.node.get_logger().info("mission_route_tracking_result: PASS")
        return None

    def _cancel_route_tracking_goal(self, goal_handle) -> None:
        if goal_handle is None:
            return
        cancel_future = goal_handle.cancel_goal_async()
        _spin_until(self.node, cancel_future, 5.0)

    def _execute_stair_segment(
        self,
        mission_goal_handle,
        segment: MissionSegment,
        goal_spec: MissionGoalSpec,
    ) -> dict[str, Any]:
        from go2w_mission.phase4b_mission_runtime import build_stair_goal_from_segment

        if not self.stair_exec_client.wait_for_server(timeout_sec=5.0):
            return {
                "success": False,
                "result_code": "MISSION_STAIR_UNAVAILABLE",
                "message": "stair_exec_unavailable",
                "recoverable": True,
            }
        goal = self.stair_exec_type.Goal()
        spec = build_stair_goal_from_segment(
            segment,
            mode="success",
            expected_duration_sec=goal_spec.expected_stair_duration_sec,
        )
        goal.connector_id = spec.connector_id
        goal.edge_id = spec.edge_id
        goal.direction = spec.direction
        goal.expected_duration_sec = spec.expected_duration_sec
        goal.force_fail = spec.force_fail
        goal.force_timeout = spec.force_timeout

        send_future = self.stair_exec_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            return {
                "success": False,
                "result_code": "MISSION_STAIR_FAILED",
                "message": "stair_goal_response_timeout",
                "recoverable": True,
            }
        child_goal_handle = send_future.result()
        if child_goal_handle is None or not child_goal_handle.accepted:
            return {
                "success": False,
                "result_code": "MISSION_STAIR_FAILED",
                "message": "stair_goal_rejected",
                "recoverable": True,
            }
        result_future = child_goal_handle.get_result_async()
        wait_status = _spin_until_or_cancel(
            self.node,
            result_future,
            goal_spec.result_timeout_sec,
            cancel_requested=lambda: self._mission_cancel_requested(
                mission_goal_handle
            ),
        )
        if wait_status == "CANCELED":
            child_goal_handle.cancel_goal_async()
            return {
                "success": False,
                "result_code": "MISSION_CANCELED",
                "message": "stair_canceled",
                "recoverable": False,
            }
        if wait_status == "TIMEOUT":
            child_goal_handle.cancel_goal_async()
            return {
                "success": False,
                "result_code": "MISSION_TIMEOUT",
                "message": "stair_timeout",
                "recoverable": True,
            }
        wrapped = result_future.result()
        result = wrapped.result
        from action_msgs.msg import GoalStatus

        if wrapped.status == GoalStatus.STATUS_CANCELED:
            return {
                "success": False,
                "result_code": "MISSION_CANCELED",
                "message": "stair_canceled",
                "recoverable": False,
            }
        if result.result_code != "SUCCEEDED":
            return {
                "success": False,
                "result_code": "MISSION_STAIR_FAILED",
                "message": result.message,
                "recoverable": True,
            }
        return {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "stair_succeeded",
            "recoverable": False,
        }

    def _feedback(
        self,
        state: str,
        current_segment_index: int,
        current_segment_type: str,
        active_owner: str,
        progress: float,
    ):
        from go2w_mission.action import RunMission

        feedback = RunMission.Feedback()
        feedback.state = state
        feedback.current_segment_index = int(current_segment_index)
        feedback.current_segment_type = current_segment_type
        feedback.active_owner = active_owner
        feedback.progress = float(progress)
        return feedback

    def _finish(
        self,
        goal_handle,
        *,
        success: bool,
        result_code: str,
        message: str,
        segment_count: int,
        segment_summary: str,
    ):
        from go2w_mission.action import RunMission

        if success:
            goal_handle.succeed()
        elif result_code == "MISSION_CANCELED":
            goal_handle.canceled()
        else:
            goal_handle.abort()

        result = RunMission.Result()
        result.success = success
        result.result_code = result_code
        result.message = message
        result.segment_count = int(segment_count)
        result.segment_summary = segment_summary
        try:
            self._append_task_history_record(
                success=success,
                result_code=result_code,
                message=message,
                segment_count=segment_count,
                segment_summary=segment_summary,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self.node.get_logger().warning(
                "mission_task_history_save_failed: "
                f"{exc}"
            )
        return result


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    def _parse_bool(value: str) -> bool:
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--graph-file", required=True)
    parser.add_argument("--start-id", type=int, default=100)
    parser.add_argument("--goal-id", type=int, default=202)
    parser.add_argument("--route-frame-id", default="map")
    parser.add_argument("--expected-stair-duration-sec", type=float, default=0.3)
    parser.add_argument("--result-timeout-sec", type=float, default=4.0)
    parser.add_argument("--flat-result-timeout-sec", type=float, default=4.0)
    parser.add_argument("--compute-route-action", default="/compute_route")
    parser.add_argument("--flat-nav-action", default="/navigate_to_pose")
    parser.add_argument("--stair-exec-action", default="/stair_exec")
    parser.add_argument("--mission-state-file", default="")
    parser.add_argument("--mission-orchestrator-state-file", default="")
    parser.add_argument("--mission-queue-replay-state-file", default="")
    parser.add_argument("--mission-task-history-file", default="")
    parser.add_argument("--mission-workflow-events-file", default="")
    parser.add_argument(
        "--mission-task-history-retention-limit",
        type=int,
        default=50,
    )
    parser.add_argument(
        "--mission-workflow-event-retention-limit",
        type=int,
        default=100,
    )
    parser.add_argument("--mission-retry-limit", type=int, default=2)
    parser.add_argument("--mission-retry-backoff-sec", type=float, default=0.5)
    parser.add_argument("--mission-recovery-enabled", type=_parse_bool, default=True)
    parser.add_argument("--flat-behavior-tree", default="success")
    parser.add_argument("--route-tracking-action", default="")
    parser.add_argument("--mission-queue-capacity", type=int, default=2)
    parser.add_argument("--mission-robot-id", default="go2w_local")
    parser.add_argument("--action-name", default="/go2w/mission/run")
    parser.add_argument(
        "--mission-control-service-name",
        default="/go2w/mission/control",
    )
    return parser.parse_known_args(argv)


def main(argv: list[str] | None = None) -> int:
    import rclpy
    from rclpy.action import ActionServer, CancelResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.node import Node

    from go2w_mission.action import RunMission
    from go2w_mission.srv import MissionControl

    args, ros_args = parse_args(sys.argv[1:] if argv is None else argv)

    class MissionApiNode(Node):
        def __init__(self) -> None:
            super().__init__("go2w_mission_api")
            self._runtime = MissionApiRuntime(
                node=self,
                compute_route_action=args.compute_route_action,
                flat_nav_action=args.flat_nav_action,
                stair_exec_action=args.stair_exec_action,
                mission_state_file=args.mission_state_file,
                mission_orchestrator_state_file=args.mission_orchestrator_state_file,
                mission_queue_replay_state_file=args.mission_queue_replay_state_file,
                mission_task_history_file=args.mission_task_history_file,
                mission_task_history_retention_limit=(
                    args.mission_task_history_retention_limit
                ),
                mission_workflow_events_file=args.mission_workflow_events_file,
                mission_workflow_event_retention_limit=(
                    args.mission_workflow_event_retention_limit
                ),
                mission_retry_limit=args.mission_retry_limit,
                mission_retry_backoff_sec=args.mission_retry_backoff_sec,
                mission_recovery_enabled=args.mission_recovery_enabled,
                flat_behavior_tree=args.flat_behavior_tree,
                route_tracking_action=args.route_tracking_action,
                mission_queue_capacity=args.mission_queue_capacity,
                mission_robot_id=args.mission_robot_id,
            )
            self._callback_group = ReentrantCallbackGroup()
            self._server = ActionServer(
                self,
                RunMission,
                args.action_name,
                self._execute_callback,
                callback_group=self._callback_group,
                cancel_callback=self._cancel_callback,
            )
            self._control_service = self.create_service(
                MissionControl,
                args.mission_control_service_name,
                self._control_callback,
                callback_group=self._callback_group,
            )

        def _cancel_callback(self, _cancel_request):
            return CancelResponse.ACCEPT

        def _execute_callback(self, goal_handle):
            return self._runtime.execute(goal_handle)

        def _control_callback(self, request, response):
            result = self._runtime.handle_orchestrator_command(
                request.command,
                request.reason,
            )
            response.accepted = bool(result["accepted"])
            response.mode = str(result["mode"])
            response.message = str(result["message"])
            response.state_summary = str(result["state_summary"])
            return response

    rclpy.init(args=[sys.argv[0], *ros_args])
    node = MissionApiNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


def _spin_until(node, future, timeout_sec: float) -> bool:
    import rclpy
    import time

    deadline = time.monotonic() + timeout_sec
    while (
        rclpy.ok()
        and future is not None
        and not future.done()
        and time.monotonic() < deadline
    ):
        rclpy.spin_once(node, timeout_sec=0.05)
    return future.done()


def _spin_until_or_cancel(
    node,
    future,
    timeout_sec: float,
    *,
    cancel_requested=None,
) -> str:
    import rclpy
    import time

    deadline = time.monotonic() + timeout_sec
    while (
        rclpy.ok()
        and future is not None
        and not future.done()
        and time.monotonic() < deadline
    ):
        if cancel_requested is not None and cancel_requested():
            return "CANCELED"
        rclpy.spin_once(node, timeout_sec=0.05)
    if cancel_requested is not None and cancel_requested():
        return "CANCELED"
    if future.done():
        return "DONE"
    return "TIMEOUT"


def _to_pose_stamped(spec):
    return pose_stamped_from_xy_yaw(
        frame_id=spec.frame_id,
        x=spec.x,
        y=spec.y,
        yaw=float(getattr(spec, "yaw", 0.0)),
    )
