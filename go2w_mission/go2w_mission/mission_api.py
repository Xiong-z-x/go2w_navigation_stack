from __future__ import annotations

import argparse
from dataclasses import dataclass
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
from go2w_mission.mission_recovery import (
    MissionCheckpoint,
    MissionStateStore,
    build_mission_key,
    checkpoint_for_goal,
    is_recoverable_result_code,
    should_resume_checkpoint,
)


@dataclass(frozen=True)
class MissionGoalSpec:
    start_id: int
    goal_id: int
    graph_file: str
    route_frame_id: str
    expected_stair_duration_sec: float
    result_timeout_sec: float
    flat_result_timeout_sec: float


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
    )


def classify_mission_result(result_code: str) -> str:
    if result_code == "SUCCEEDED":
        return "MISSION_SUCCEEDED"
    if result_code == "CANCELED":
        return "MISSION_CANCELED"
    return "MISSION_FAILED"


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


class MissionApiRuntime:
    def __init__(
        self,
        *,
        node,
        compute_route_action: str,
        flat_nav_action: str,
        stair_exec_action: str,
        mission_state_file: str,
        mission_retry_limit: int,
        mission_retry_backoff_sec: float,
        mission_recovery_enabled: bool,
    ) -> None:
        from nav2_msgs.action import ComputeRoute, NavigateToPose
        from rclpy.action import ActionClient

        from go2w_control.action import StairExec

        self.node = node
        self.compute_route_type = ComputeRoute
        self.navigate_to_pose_type = NavigateToPose
        self.stair_exec_type = StairExec
        self.compute_route_client = ActionClient(node, ComputeRoute, compute_route_action)
        self.navigate_to_pose_client = ActionClient(node, NavigateToPose, flat_nav_action)
        self.stair_exec_client = ActionClient(node, StairExec, stair_exec_action)
        state_path = (
            Path(mission_state_file).expanduser()
            if mission_state_file.strip()
            else MissionStateStore.default_path()
        )
        self.state_store = MissionStateStore(state_path)
        self.mission_retry_limit = max(0, int(mission_retry_limit))
        self.mission_retry_backoff_sec = max(0.0, float(mission_retry_backoff_sec))
        self.mission_recovery_enabled = bool(mission_recovery_enabled)
        self._mission_lock = threading.Lock()
        loaded = self.state_store.load()
        if loaded is not None:
            self.node.get_logger().info(
                "mission_state_loaded: "
                f"key={loaded.mission_key} state={loaded.state} "
                f"next_segment_index={loaded.next_segment_index} "
                f"result_code={loaded.result_code}"
            )

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

        mission_key = build_mission_key(
            start_id=goal_spec.start_id,
            goal_id=goal_spec.goal_id,
            graph_file=goal_spec.graph_file,
            route_frame_id=goal_spec.route_frame_id,
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

        goal_handle.publish_feedback(self._feedback("ROUTE_REQUESTED", 0, "", "", 0.0))
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
            mission_goal_handle,
            result_future,
            10.0,
        ) == "DONE":
            child_goal_handle.cancel_goal_async()
            if mission_goal_handle.is_cancel_requested:
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
                if goal_handle.is_cancel_requested:
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
        goal.behavior_tree = "success"

        send_future = self.navigate_to_pose_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            return {
                "success": False,
                "result_code": "MISSION_FLAT_FAILED",
                "message": "flat_goal_response_timeout",
                "recoverable": True,
            }
        child_goal_handle = send_future.result()
        if child_goal_handle is None or not child_goal_handle.accepted:
            return {
                "success": False,
                "result_code": "MISSION_FLAT_FAILED",
                "message": "flat_goal_rejected",
                "recoverable": True,
            }
        result_future = child_goal_handle.get_result_async()
        wait_status = _spin_until_or_cancel(
            self.node,
            mission_goal_handle,
            result_future,
            goal_spec.flat_result_timeout_sec,
        )
        if wait_status == "CANCELED":
            child_goal_handle.cancel_goal_async()
            return {
                "success": False,
                "result_code": "MISSION_CANCELED",
                "message": "flat_canceled",
                "recoverable": False,
            }
        if wait_status == "TIMEOUT":
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
            return {
                "success": False,
                "result_code": "MISSION_CANCELED",
                "message": "flat_canceled",
                "recoverable": False,
            }
        if wrapped.status != GoalStatus.STATUS_SUCCEEDED:
            return {
                "success": False,
                "result_code": "MISSION_FLAT_FAILED",
                "message": "flat_failed",
                "recoverable": True,
            }
        return {
            "success": True,
            "result_code": "MISSION_SUCCEEDED",
            "message": "flat_succeeded",
            "recoverable": False,
        }

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
            mission_goal_handle,
            result_future,
            goal_spec.result_timeout_sec,
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
    parser.add_argument("--mission-retry-limit", type=int, default=2)
    parser.add_argument("--mission-retry-backoff-sec", type=float, default=0.5)
    parser.add_argument("--mission-recovery-enabled", type=_parse_bool, default=True)
    parser.add_argument("--action-name", default="/go2w/mission/run")
    return parser.parse_known_args(argv)


def main(argv: list[str] | None = None) -> int:
    import rclpy
    from rclpy.action import ActionServer, CancelResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.node import Node

    from go2w_mission.action import RunMission

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
                mission_retry_limit=args.mission_retry_limit,
                mission_retry_backoff_sec=args.mission_retry_backoff_sec,
                mission_recovery_enabled=args.mission_recovery_enabled,
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

        def _cancel_callback(self, _cancel_request):
            return CancelResponse.ACCEPT

        def _execute_callback(self, goal_handle):
            return self._runtime.execute(goal_handle)

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
    import time

    deadline = time.monotonic() + timeout_sec
    while future is not None and not future.done() and time.monotonic() < deadline:
        time.sleep(0.05)
    return future.done()


def _spin_until_or_cancel(node, goal_handle, future, timeout_sec: float) -> str:
    import time

    deadline = time.monotonic() + timeout_sec
    while future is not None and not future.done() and time.monotonic() < deadline:
        if goal_handle.is_cancel_requested:
            return "CANCELED"
        time.sleep(0.05)
    if goal_handle.is_cancel_requested:
        return "CANCELED"
    if future.done():
        return "DONE"
    return "TIMEOUT"


def _to_pose_stamped(spec):
    from geometry_msgs.msg import PoseStamped

    pose = PoseStamped()
    pose.header.frame_id = spec.frame_id
    pose.pose.position.x = spec.x
    pose.pose.position.y = spec.y
    pose.pose.orientation.w = 1.0
    return pose
