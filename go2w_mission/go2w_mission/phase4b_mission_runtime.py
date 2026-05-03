from __future__ import annotations

from dataclasses import dataclass
import argparse
import math
from pathlib import Path
import sys
import time

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph
from go2w_mission.phase4b_mission_segments import (
    MissionSegment,
    build_mission_segments,
    classify_stair_result,
)
from go2w_mission.mission_pose import pose_stamped_from_xy_yaw


@dataclass(frozen=True)
class StairGoalSpec:
    connector_id: str
    edge_id: int
    direction: str
    expected_duration_sec: float
    force_fail: bool
    force_timeout: bool


@dataclass(frozen=True)
class FlatGoalSpec:
    frame_id: str
    x: float
    y: float
    yaw: float = 0.0


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def build_stair_goal_from_segment(
    segment: MissionSegment,
    *,
    mode: str,
    expected_duration_sec: float,
) -> StairGoalSpec:
    return StairGoalSpec(
        connector_id=segment.connector_id,
        edge_id=segment.edge_ids[0],
        direction=f"{segment.floor_from}_to_{segment.floor_to}",
        expected_duration_sec=expected_duration_sec,
        force_fail=mode == "failure",
        force_timeout=mode in {"timeout", "cancel"},
    )


def build_flat_goal_from_segment(
    graph: Phase4ARouteGraph,
    segment: MissionSegment,
    *,
    frame_id: str,
) -> FlatGoalSpec:
    last_edge = graph.edges[segment.edge_ids[-1]]
    target = graph.nodes[last_edge.end_id]
    yaw = float(target.properties.get("yaw", _edge_heading_yaw(last_edge)))
    return FlatGoalSpec(frame_id=frame_id, x=target.x, y=target.y, yaw=yaw)


def _edge_heading_yaw(edge) -> float:
    if len(edge.coordinates) >= 2:
        start_x, start_y = edge.coordinates[-2]
        end_x, end_y = edge.coordinates[-1]
        return math.atan2(end_y - start_y, end_x - start_x)
    return 0.0


def _to_pose_stamped(spec: FlatGoalSpec):
    return pose_stamped_from_xy_yaw(
        frame_id=spec.frame_id,
        x=spec.x,
        y=spec.y,
        yaw=spec.yaw,
    )


def final_result_for_timeout(mode: str) -> str:
    return "MISSION_TIMEOUT" if mode == "timeout" else "MISSION_FAILED"


def final_result_for_flat_timeout(mode: str) -> str:
    return "MISSION_TIMEOUT" if mode == "flat_timeout" else "MISSION_FAILED"


def _spin_until(node, future, timeout_sec: float) -> bool:
    import rclpy

    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    return future.done()


class Phase4BMissionRuntime:
    def __init__(
        self,
        *,
        node,
        graph_file: Path,
        start_id: int,
        goal_id: int,
        mode: str,
        expected_duration_sec: float,
        result_timeout_sec: float,
        compute_route_action: str,
        flat_nav_action: str,
        flat_mode: str,
        flat_result_timeout_sec: float,
        route_frame_id: str,
    ) -> None:
        from nav2_msgs.action import ComputeRoute, NavigateToPose
        from rclpy.action import ActionClient

        from go2w_control.action import StairExec

        self.node = node
        self.graph = Phase4ARouteGraph.from_file(graph_file)
        self.start_id = start_id
        self.goal_id = goal_id
        self.mode = mode
        self.expected_duration_sec = expected_duration_sec
        self.result_timeout_sec = result_timeout_sec
        self.flat_mode = flat_mode
        self.flat_result_timeout_sec = flat_result_timeout_sec
        self.route_frame_id = route_frame_id
        self.compute_route_type = ComputeRoute
        self.navigate_to_pose_type = NavigateToPose
        self.stair_exec_type = StairExec
        self.compute_route_client = ActionClient(node, ComputeRoute, compute_route_action)
        self.navigate_to_pose_client = ActionClient(node, NavigateToPose, flat_nav_action)
        self.stair_exec_client = ActionClient(node, StairExec, "/stair_exec")

    def run(self) -> int:
        print_kv("phase4b_state", "ROUTE_REQUESTED")
        edge_ids = self._compute_route_edge_ids()
        if not edge_ids:
            print_kv("phase4b_final_result", "ROUTE_UNAVAILABLE")
            return 2
        print_kv("phase4b_state", "ROUTE_COMPUTED")

        mismatches = self.graph.geometry_mismatches()
        if mismatches:
            print_kv("phase4b_graph_geometry", "FAIL")
            print_kv("phase4b_final_result", "CONNECTOR_UNAVAILABLE")
            return 2

        try:
            segments = build_mission_segments(self.graph, edge_ids)
        except ValueError as exc:
            print_kv("phase4b_segment_error", str(exc))
            print_kv("phase4b_final_result", "CONNECTOR_UNAVAILABLE")
            return 2
        if not any(segment.segment_type == "stair" for segment in segments):
            print_kv("phase4b_final_result", "CONNECTOR_UNAVAILABLE")
            return 2

        print_kv("phase4b_state", "SEGMENTS_READY")
        print_kv("phase4b_segments", _format_segments(segments))
        return self._execute_segments(segments)

    def _compute_route_edge_ids(self) -> list[int]:
        if not self.compute_route_client.wait_for_server(timeout_sec=5.0):
            print_kv("phase4b_route_action_server", "FAIL_UNAVAILABLE")
            return []
        goal = self.compute_route_type.Goal()
        goal.start_id = self.start_id
        goal.goal_id = self.goal_id
        goal.use_start = False
        goal.use_poses = False
        send_future = self.compute_route_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            print_kv("phase4b_route_goal_response", "FAIL_TIMEOUT")
            return []
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print_kv("phase4b_route_goal_accepted", "False")
            return []
        result_future = goal_handle.get_result_async()
        if not _spin_until(self.node, result_future, 10.0):
            print_kv("phase4b_route_result", "FAIL_TIMEOUT")
            return []
        wrapped = result_future.result()
        edge_ids = [int(edge.edgeid) for edge in wrapped.result.route.edges]
        print_kv("phase4b_route_edge_ids", ",".join(str(edge_id) for edge_id in edge_ids))
        return edge_ids

    def _execute_segments(self, segments: list[MissionSegment]) -> int:
        for index, segment in enumerate(segments):
            print_kv("phase4b_segment_index", index)
            print_kv("phase4b_segment_type", segment.segment_type)
            if segment.segment_type == "flat":
                result = self._execute_flat_segment(segment)
                if result != "MISSION_SUCCEEDED":
                    print_kv("phase4b_final_result", result)
                    return 0 if result in {"MISSION_CANCELED", "MISSION_TIMEOUT"} else 2
                continue
            result = self._execute_stair_segment(segment)
            if result != "MISSION_SUCCEEDED":
                print_kv("phase4b_final_result", result)
                return 0 if result in {"MISSION_CANCELED", "MISSION_TIMEOUT"} else 2
        print_kv("phase4b_final_result", "MISSION_SUCCEEDED")
        return 0

    def _execute_flat_segment(self, segment: MissionSegment) -> str:
        from action_msgs.msg import GoalStatus

        if not self.navigate_to_pose_client.wait_for_server(timeout_sec=5.0):
            return "FLAT_NAV_UNAVAILABLE"
        print_kv("phase4c_state", "FLAT_SEGMENT_ACTIVE")
        print_kv(
            "phase4c_flat_edges",
            ",".join(str(edge_id) for edge_id in segment.edge_ids),
        )
        goal = self.navigate_to_pose_type.Goal()
        spec = build_flat_goal_from_segment(
            self.graph,
            segment,
            frame_id=self.route_frame_id,
        )
        goal.pose = _to_pose_stamped(spec)
        if self.flat_mode == "flat_failure":
            goal.behavior_tree = "failure"
        elif self.flat_mode == "flat_timeout":
            goal.behavior_tree = "timeout"
        else:
            goal.behavior_tree = "success"

        send_future = self.navigate_to_pose_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            return "FLAT_NAV_FAILED"
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return "FLAT_NAV_FAILED"
        if self.flat_mode == "flat_cancel":
            time.sleep(0.2)
            cancel_future = goal_handle.cancel_goal_async()
            if not _spin_until(self.node, cancel_future, 5.0):
                return "FLAT_NAV_FAILED"
            print_kv("phase4c_flat_cancel", "REQUESTED")
        result_future = goal_handle.get_result_async()
        if not _spin_until(self.node, result_future, self.flat_result_timeout_sec):
            goal_handle.cancel_goal_async()
            return final_result_for_flat_timeout(self.flat_mode)
        wrapped = result_future.result()
        print_kv("phase4c_flat_action_status", wrapped.status)
        if wrapped.status == GoalStatus.STATUS_SUCCEEDED:
            print_kv("phase4c_state", "FLAT_SEGMENT_SUCCEEDED")
            return "MISSION_SUCCEEDED"
        if wrapped.status == GoalStatus.STATUS_CANCELED:
            return "MISSION_CANCELED"
        return "FLAT_NAV_FAILED"

    def _execute_stair_segment(self, segment: MissionSegment) -> str:
        from action_msgs.msg import GoalStatus

        if not self.stair_exec_client.wait_for_server(timeout_sec=5.0):
            return "MISSION_FAILED"
        print_kv("phase4b_state", "STAIR_SEGMENT_ACTIVE")
        spec = build_stair_goal_from_segment(
            segment,
            mode=self.mode,
            expected_duration_sec=self.expected_duration_sec,
        )
        goal = self.stair_exec_type.Goal()
        goal.connector_id = spec.connector_id
        goal.edge_id = spec.edge_id
        goal.direction = spec.direction
        goal.expected_duration_sec = spec.expected_duration_sec
        goal.force_fail = spec.force_fail
        goal.force_timeout = spec.force_timeout

        send_future = self.stair_exec_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            return "MISSION_FAILED"
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return "MISSION_FAILED"
        if self.mode == "cancel":
            time.sleep(0.3)
            cancel_future = goal_handle.cancel_goal_async()
            if not _spin_until(self.node, cancel_future, 5.0):
                return "MISSION_FAILED"
            print_kv("phase4b_stair_cancel", "REQUESTED")
        result_future = goal_handle.get_result_async()
        if not _spin_until(self.node, result_future, self.result_timeout_sec):
            goal_handle.cancel_goal_async()
            return final_result_for_timeout(self.mode)
        wrapped = result_future.result()
        result = wrapped.result
        print_kv("phase4b_stair_action_status", wrapped.status)
        print_kv("phase4b_stair_result_code", result.result_code)
        if wrapped.status == GoalStatus.STATUS_CANCELED:
            return "MISSION_CANCELED"
        if result.result_code == "SUCCEEDED":
            print_kv("phase4b_state", "STAIR_SEGMENT_SUCCEEDED")
        return classify_stair_result(result.result_code)


def _format_segments(segments: list[MissionSegment]) -> str:
    formatted = []
    for segment in segments:
        edges = "|".join(str(edge_id) for edge_id in segment.edge_ids)
        formatted.append(f"{segment.segment_type}:{edges}")
    return ";".join(formatted)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph-file", required=True)
    parser.add_argument("--start-id", type=int, default=100)
    parser.add_argument("--goal-id", type=int, default=202)
    parser.add_argument(
        "--mode",
        choices=("success", "failure", "cancel", "timeout"),
        default="success",
    )
    parser.add_argument("--expected-duration-sec", type=float, default=0.3)
    parser.add_argument("--result-timeout-sec", type=float, default=4.0)
    parser.add_argument("--compute-route-action", default="/compute_route")
    parser.add_argument("--flat-nav-action", default="/navigate_to_pose")
    parser.add_argument(
        "--flat-mode",
        choices=("success", "flat_failure", "flat_cancel", "flat_timeout"),
        default="success",
    )
    parser.add_argument("--flat-result-timeout-sec", type=float, default=4.0)
    parser.add_argument("--route-frame-id", default="map")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import rclpy
    from rclpy.node import Node

    args = parse_args(sys.argv[1:] if argv is None else argv)
    rclpy.init()
    node = Node("go2w_phase4b_mission_runtime")
    try:
        runtime = Phase4BMissionRuntime(
            node=node,
            graph_file=Path(args.graph_file),
            start_id=args.start_id,
            goal_id=args.goal_id,
            mode=args.mode,
            expected_duration_sec=args.expected_duration_sec,
            result_timeout_sec=args.result_timeout_sec,
            compute_route_action=args.compute_route_action,
            flat_nav_action=args.flat_nav_action,
            flat_mode=args.flat_mode,
            flat_result_timeout_sec=args.flat_result_timeout_sec,
            route_frame_id=args.route_frame_id,
        )
        return runtime.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
