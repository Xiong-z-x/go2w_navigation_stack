from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
import time


@dataclass
class RouteTrackingObservation:
    stair_edge_id: int
    feedback_seen: bool = False
    stair_edge_detected: bool = False
    operation_triggered: str = ""
    feedback_count: int = 0

    def record_feedback(self, *, current_edge_id: int, operations: tuple[str, ...]) -> None:
        self.feedback_seen = True
        self.feedback_count += 1
        if current_edge_id == self.stair_edge_id:
            self.stair_edge_detected = True
            if "stair_exec" in operations:
                self.operation_triggered = "stair_exec"

    def final_result(self, *, require_operation: bool) -> str:
        if not self.feedback_seen:
            return "ROUTE_TRACKING_FEEDBACK_MISSING"
        if not self.stair_edge_detected:
            return "STAIR_EDGE_NOT_OBSERVED"
        if require_operation and self.operation_triggered != "stair_exec":
            return "ROUTE_OPERATION_NOT_OBSERVED"
        return "PASS"


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def _spin_until(node, future, timeout_sec: float) -> bool:
    import rclpy

    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    return future.done()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-name", default="/compute_and_track_route")
    parser.add_argument("--start-id", type=int, default=100)
    parser.add_argument("--goal-id", type=int, default=202)
    parser.add_argument("--stair-edge-id", type=int, default=500)
    parser.add_argument("--result-timeout-sec", type=float, default=5.0)
    parser.add_argument("--allow-missing-operation", action="store_true")
    return parser.parse_args(argv)


class RouteTrackingObserverRuntime:
    def __init__(
        self,
        *,
        node,
        action_name: str,
        start_id: int,
        goal_id: int,
        stair_edge_id: int,
        result_timeout_sec: float,
        require_operation: bool,
    ) -> None:
        from nav2_msgs.action import ComputeAndTrackRoute
        from rclpy.action import ActionClient

        self.node = node
        self.action_type = ComputeAndTrackRoute
        self.client = ActionClient(node, ComputeAndTrackRoute, action_name)
        self.start_id = start_id
        self.goal_id = goal_id
        self.result_timeout_sec = result_timeout_sec
        self.require_operation = require_operation
        self.observation = RouteTrackingObservation(stair_edge_id=stair_edge_id)

    def run(self) -> int:
        if not self.client.wait_for_server(timeout_sec=5.0):
            print_kv("phase4d_final_result", "ROUTE_TRACKING_UNAVAILABLE")
            return 2

        goal = self.action_type.Goal()
        goal.start_id = self.start_id
        goal.goal_id = self.goal_id
        goal.use_start = False
        goal.use_poses = False
        send_future = self.client.send_goal_async(goal, feedback_callback=self._on_feedback)
        if not _spin_until(self.node, send_future, 10.0):
            print_kv("phase4d_final_result", "ROUTE_TRACKING_GOAL_TIMEOUT")
            return 2
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            print_kv("phase4d_final_result", "ROUTE_TRACKING_GOAL_REJECTED")
            return 2

        result_future = goal_handle.get_result_async()
        if not _spin_until(self.node, result_future, self.result_timeout_sec):
            goal_handle.cancel_goal_async()
            print_kv("phase4d_final_result", "ROUTE_TRACKING_TIMEOUT")
            return 2

        return self._report()

    def _on_feedback(self, feedback_msg) -> None:
        feedback = feedback_msg.feedback
        self.observation.record_feedback(
            current_edge_id=int(feedback.current_edge_id),
            operations=tuple(feedback.operations_triggered),
        )
        print_kv("phase4d_feedback_edge", int(feedback.current_edge_id))
        if feedback.operations_triggered:
            print_kv("phase4d_feedback_operations", ",".join(feedback.operations_triggered))

    def _report(self) -> int:
        final_result = self.observation.final_result(require_operation=self.require_operation)
        print_kv("phase4d_feedback_count", self.observation.feedback_count)
        print_kv(
            "phase4d_route_feedback_seen",
            "PASS" if self.observation.feedback_seen else "FAIL",
        )
        print_kv(
            "phase4d_stair_edge_detected",
            "PASS" if self.observation.stair_edge_detected else "FAIL",
        )
        if self.observation.operation_triggered:
            print_kv("phase4d_operation_triggered", self.observation.operation_triggered)
        print_kv("phase4d_route_tracking_result", final_result)
        if final_result == "PASS":
            return 0
        print_kv("phase4d_final_result", final_result)
        return 2


def main(argv: list[str] | None = None) -> int:
    import rclpy
    from rclpy.node import Node

    args = parse_args(sys.argv[1:] if argv is None else argv)
    rclpy.init()
    node = Node("go2w_phase4d_route_tracking_observer")
    try:
        runtime = RouteTrackingObserverRuntime(
            node=node,
            action_name=args.action_name,
            start_id=args.start_id,
            goal_id=args.goal_id,
            stair_edge_id=args.stair_edge_id,
            result_timeout_sec=args.result_timeout_sec,
            require_operation=not args.allow_missing_operation,
        )
        return runtime.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
