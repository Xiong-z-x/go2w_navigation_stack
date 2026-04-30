from __future__ import annotations

from dataclasses import dataclass
import argparse
from pathlib import Path
import sys
import time

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph, RouteEdge


@dataclass(frozen=True)
class StairGoalSpec:
    connector_id: str
    edge_id: int
    direction: str
    expected_duration_sec: float
    force_fail: bool
    force_timeout: bool


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def build_stair_goal_spec(
    edge: RouteEdge,
    *,
    mode: str,
    expected_duration_sec: float,
) -> StairGoalSpec:
    floor_from = str(edge.properties.get("floor_from", "unknown_from"))
    floor_to = str(edge.properties.get("floor_to", "unknown_to"))
    return StairGoalSpec(
        connector_id=str(edge.properties["connector_id"]),
        edge_id=edge.edge_id,
        direction=f"{floor_from}_to_{floor_to}",
        expected_duration_sec=expected_duration_sec,
        force_fail=mode == "failure",
        force_timeout=mode in {"timeout", "cancel"},
    )


def _spin_until(node, future, timeout_sec: float) -> bool:
    import rclpy

    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    return future.done()


def _publish_flat_probe(node, publisher) -> None:
    from geometry_msgs.msg import Twist

    msg = Twist()
    msg.linear.x = 0.02
    for _ in range(3):
        publisher.publish(msg)
        rclpy = sys.modules.get("rclpy")
        if rclpy is not None:
            rclpy.spin_once(node, timeout_sec=0.05)


class Phase4AHandoffDemo:
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
    ) -> None:
        from geometry_msgs.msg import Twist
        from nav2_msgs.action import ComputeRoute
        from rclpy.action import ActionClient

        from go2w_control.action import StairExec

        self.node = node
        self.graph = Phase4ARouteGraph.from_file(graph_file)
        self.start_id = start_id
        self.goal_id = goal_id
        self.mode = mode
        self.expected_duration_sec = expected_duration_sec
        self.result_timeout_sec = result_timeout_sec
        self.compute_route_type = ComputeRoute
        self.stair_exec_type = StairExec
        self.compute_route_client = ActionClient(node, ComputeRoute, "/compute_route")
        self.stair_exec_client = ActionClient(node, StairExec, "/stair_exec")
        self.flat_cmd_pub = node.create_publisher(
            Twist,
            "/go2w/control/flat_cmd_vel",
            10,
        )

    def run(self) -> int:
        mismatches = self.graph.geometry_mismatches()
        if mismatches:
            print_kv("route_graph_geometry", "FAIL")
            print_kv("route_graph_mismatches", ",".join(mismatches))
            return 2
        print_kv("route_graph_geometry", "PASS")

        edge_ids = self._compute_route_edge_ids()
        if not edge_ids:
            return 2

        stair_edges = self.graph.stair_edges_for_ids(edge_ids)
        if not stair_edges:
            print_kv("stair_edge_detected", "FAIL")
            return 2
        stair_edge = stair_edges[0]
        print_kv("stair_edge_detected", stair_edge.edge_id)
        print_kv("stair_connector_id", stair_edge.properties["connector_id"])

        _publish_flat_probe(self.node, self.flat_cmd_pub)
        spec = build_stair_goal_spec(
            stair_edge,
            mode=self.mode,
            expected_duration_sec=self.expected_duration_sec,
        )
        return self._execute_stair(spec)

    def _compute_route_edge_ids(self) -> list[int]:
        if not self.compute_route_client.wait_for_server(timeout_sec=10.0):
            print_kv("compute_route_action_server", "FAIL_UNAVAILABLE")
            return []

        goal = self.compute_route_type.Goal()
        goal.start_id = self.start_id
        goal.goal_id = self.goal_id
        goal.use_start = False
        goal.use_poses = False
        send_future = self.compute_route_client.send_goal_async(goal)
        if not _spin_until(self.node, send_future, 10.0):
            print_kv("compute_route_goal_response", "FAIL_TIMEOUT")
            return []
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print_kv("compute_route_goal_accepted", "False")
            return []
        print_kv("compute_route_goal_accepted", "True")

        result_future = goal_handle.get_result_async()
        if not _spin_until(self.node, result_future, 10.0):
            print_kv("compute_route_result", "FAIL_TIMEOUT")
            return []
        wrapped = result_future.result()
        edge_ids = [int(edge.edgeid) for edge in wrapped.result.route.edges]
        print_kv("compute_route_action_status", wrapped.status)
        print_kv("compute_route_edge_ids", ",".join(str(edge_id) for edge_id in edge_ids))
        return edge_ids

    def _execute_stair(self, spec: StairGoalSpec) -> int:
        if not self.stair_exec_client.wait_for_server(timeout_sec=10.0):
            print_kv("stair_exec_action_server", "FAIL_UNAVAILABLE")
            return 2
        print_kv("stair_exec_action_server", "AVAILABLE")

        goal = self.stair_exec_type.Goal()
        goal.connector_id = spec.connector_id
        goal.edge_id = spec.edge_id
        goal.direction = spec.direction
        goal.expected_duration_sec = spec.expected_duration_sec
        goal.force_fail = spec.force_fail
        goal.force_timeout = spec.force_timeout

        send_future = self.stair_exec_client.send_goal_async(
            goal,
            feedback_callback=self._feedback_callback,
        )
        if not _spin_until(self.node, send_future, 10.0):
            print_kv("stair_exec_goal_response", "FAIL_TIMEOUT")
            return 2
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print_kv("stair_exec_goal_accepted", "False")
            return 2
        print_kv("stair_exec_goal_accepted", "True")

        if self.mode == "cancel":
            time.sleep(0.3)
            cancel_future = goal_handle.cancel_goal_async()
            if not _spin_until(self.node, cancel_future, 5.0):
                print_kv("stair_exec_cancel", "FAIL_TIMEOUT")
                return 2
            print_kv("stair_exec_cancel", "REQUESTED")

        result_future = goal_handle.get_result_async()
        if not _spin_until(self.node, result_future, self.result_timeout_sec):
            print_kv("stair_exec_timeout", "PASS")
            goal_handle.cancel_goal_async()
            return 0 if self.mode == "timeout" else 2

        wrapped = result_future.result()
        result = wrapped.result
        print_kv("stair_exec_action_status", wrapped.status)
        print_kv("stair_exec_result_code", result.result_code)
        print_kv("stair_exec_success", result.success)

        expected_code = {
            "success": "SUCCEEDED",
            "failure": "FAILED",
            "cancel": "CANCELED",
        }.get(self.mode)
        if expected_code is None:
            print_kv("phase4a_handoff_result", "FAIL_UNEXPECTED_TIMEOUT_RESULT")
            return 2
        if result.result_code != expected_code:
            print_kv("phase4a_handoff_result", "FAIL_UNEXPECTED_RESULT_CODE")
            return 2
        print_kv("phase4a_handoff_result", "PASS")
        return 0

    def _feedback_callback(self, msg) -> None:
        feedback = msg.feedback
        print_kv("stair_exec_feedback_phase", feedback.phase)
        print_kv("stair_exec_feedback_owner", feedback.owner)


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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import rclpy
    from rclpy.node import Node

    args = parse_args(sys.argv[1:] if argv is None else argv)
    rclpy.init()
    node = Node("go2w_phase4a_handoff_demo")
    try:
        demo = Phase4AHandoffDemo(
            node=node,
            graph_file=Path(args.graph_file),
            start_id=args.start_id,
            goal_id=args.goal_id,
            mode=args.mode,
            expected_duration_sec=args.expected_duration_sec,
            result_timeout_sec=args.result_timeout_sec,
        )
        return demo.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
