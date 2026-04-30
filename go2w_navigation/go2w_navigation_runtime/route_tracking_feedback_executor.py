from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
import time


@dataclass(frozen=True)
class RouteTrackingFeedbackSample:
    last_node_id: int
    next_node_id: int
    current_edge_id: int
    operations_triggered: tuple[str, ...] = ()


def build_feedback_sequence(*, include_operation: bool) -> list[RouteTrackingFeedbackSample]:
    stair_operations = ("stair_exec",) if include_operation else ()
    return [
        RouteTrackingFeedbackSample(last_node_id=100, next_node_id=101, current_edge_id=300),
        RouteTrackingFeedbackSample(last_node_id=101, next_node_id=102, current_edge_id=301),
        RouteTrackingFeedbackSample(
            last_node_id=102,
            next_node_id=200,
            current_edge_id=500,
            operations_triggered=stair_operations,
        ),
        RouteTrackingFeedbackSample(last_node_id=200, next_node_id=201, current_edge_id=400),
        RouteTrackingFeedbackSample(last_node_id=201, next_node_id=202, current_edge_id=401),
    ]


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-name", default="/compute_and_track_route")
    parser.add_argument("--drop-operation", action="store_true")
    parser.add_argument("--feedback-period-sec", type=float, default=0.05)
    return parser.parse_known_args(argv)


def _duration_msg(elapsed_sec: float):
    from builtin_interfaces.msg import Duration

    duration = Duration()
    duration.sec = int(elapsed_sec)
    duration.nanosec = int((elapsed_sec - duration.sec) * 1_000_000_000)
    return duration


def main(argv: list[str] | None = None) -> None:
    import rclpy
    from nav2_msgs.action import ComputeAndTrackRoute
    from rclpy.action import ActionServer, CancelResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.node import Node

    raw_argv = sys.argv[1:] if argv is None else argv
    args, ros_args = parse_args(raw_argv)

    class RouteTrackingFeedbackExecutorNode(Node):
        def __init__(self) -> None:
            super().__init__("go2w_route_tracking_feedback_executor")
            self._callback_group = ReentrantCallbackGroup()
            self._server = ActionServer(
                self,
                ComputeAndTrackRoute,
                args.action_name,
                self._execute_callback,
                callback_group=self._callback_group,
                cancel_callback=self._cancel_callback,
            )

        def _cancel_callback(self, _cancel_request):
            return CancelResponse.ACCEPT

        def _execute_callback(self, goal_handle):
            _ = goal_handle.request
            started = time.monotonic()
            for sample in build_feedback_sequence(include_operation=not args.drop_operation):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    return ComputeAndTrackRoute.Result()
                feedback = ComputeAndTrackRoute.Feedback()
                feedback.last_node_id = sample.last_node_id
                feedback.next_node_id = sample.next_node_id
                feedback.current_edge_id = sample.current_edge_id
                feedback.operations_triggered = list(sample.operations_triggered)
                feedback.route.header.frame_id = "map"
                feedback.path.header.frame_id = "map"
                goal_handle.publish_feedback(feedback)
                time.sleep(args.feedback_period_sec)

            goal_handle.succeed()
            result = ComputeAndTrackRoute.Result()
            result.execution_duration = _duration_msg(time.monotonic() - started)
            return result

    rclpy.init(args=[sys.argv[0], *ros_args])
    node = RouteTrackingFeedbackExecutorNode()
    executor = MultiThreadedExecutor()
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


if __name__ == "__main__":
    main()
