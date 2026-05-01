from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import sys
import time
from typing import Iterable

from go2w_mission.phase4a_route_graph import Phase4ARouteGraph
from go2w_mission.phase4d_route_tracking_observer import RouteTrackingObservation


@dataclass(frozen=True)
class RoutePoseSample:
    node_id: int
    x: float
    y: float
    hold_sec: float


def build_route_pose_samples(
    graph: Phase4ARouteGraph,
    node_ids: Iterable[int],
    *,
    hold_sec: float,
) -> list[RoutePoseSample]:
    samples: list[RoutePoseSample] = []
    for node_id in node_ids:
        node = graph.nodes[int(node_id)]
        samples.append(
            RoutePoseSample(
                node_id=int(node_id),
                x=float(node.x),
                y=float(node.y),
                hold_sec=float(hold_sec),
            )
        )
    return samples


def _parse_node_ids(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def _parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph-file", required=True)
    parser.add_argument("--action-name", default="/compute_and_track_route")
    parser.add_argument("--start-id", type=int, default=100)
    parser.add_argument("--goal-id", type=int, default=202)
    parser.add_argument("--stair-edge-id", type=int, default=500)
    parser.add_argument("--trajectory-node-ids", default="100,101,102,200,201,202")
    parser.add_argument("--sample-hold-sec", type=float, default=0.35)
    parser.add_argument("--result-timeout-sec", type=float, default=30.0)
    parser.add_argument("--route-frame-id", default="map")
    parser.add_argument("--odom-frame-id", default="odom")
    parser.add_argument("--base-frame-id", default="base_link")
    return parser.parse_known_args(argv)


def _spin_until(node, future, timeout_sec: float) -> bool:
    import rclpy

    deadline = time.monotonic() + timeout_sec
    while rclpy.ok() and not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    return future.done()


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def _make_transform(node, parent_frame: str, child_frame: str, x: float, y: float):
    from geometry_msgs.msg import TransformStamped

    transform = TransformStamped()
    transform.header.stamp = node.get_clock().now().to_msg()
    transform.header.frame_id = parent_frame
    transform.child_frame_id = child_frame
    transform.transform.translation.x = float(x)
    transform.transform.translation.y = float(y)
    transform.transform.translation.z = 0.0
    transform.transform.rotation.w = 1.0
    return transform


class LiveRouteTrackingProbeRuntime:
    def __init__(
        self,
        *,
        node,
        graph_file: Path,
        action_name: str,
        start_id: int,
        goal_id: int,
        stair_edge_id: int,
        trajectory_node_ids: list[int],
        sample_hold_sec: float,
        result_timeout_sec: float,
        route_frame_id: str,
        odom_frame_id: str,
        base_frame_id: str,
    ) -> None:
        from nav2_msgs.action import ComputeAndTrackRoute
        from rclpy.action import ActionClient
        from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

        self.node = node
        self.graph = Phase4ARouteGraph.from_file(graph_file)
        self.samples = build_route_pose_samples(
            self.graph,
            trajectory_node_ids,
            hold_sec=sample_hold_sec,
        )
        self.action_type = ComputeAndTrackRoute
        self.client = ActionClient(node, ComputeAndTrackRoute, action_name)
        self.observation = RouteTrackingObservation(stair_edge_id=stair_edge_id)
        self.result_timeout_sec = result_timeout_sec
        self.start_id = start_id
        self.goal_id = goal_id
        self.route_frame_id = route_frame_id
        self.odom_frame_id = odom_frame_id
        self.base_frame_id = base_frame_id
        self._static_broadcaster = StaticTransformBroadcaster(node)
        self._dynamic_broadcaster = TransformBroadcaster(node)
        self._feedback_edges: list[int] = []
        self._goal_handle = None

    def run(self) -> int:
        if not self.client.wait_for_server(timeout_sec=30.0):
            print_kv("phase5a_final_result", "ROUTE_TRACKING_UNAVAILABLE")
            return 2

        self._publish_static_chain()
        self._warmup_pose()

        goal = self.action_type.Goal()
        goal.start_id = self.start_id
        goal.goal_id = self.goal_id
        goal.use_start = False
        goal.use_poses = False

        send_future = self.client.send_goal_async(goal, feedback_callback=self._on_feedback)
        if not _spin_until(self.node, send_future, 10.0):
            print_kv("phase5a_final_result", "ROUTE_TRACKING_GOAL_TIMEOUT")
            return 2

        self._goal_handle = send_future.result()
        if self._goal_handle is None or not self._goal_handle.accepted:
            print_kv("phase5a_final_result", "ROUTE_TRACKING_GOAL_REJECTED")
            return 2

        deadline = time.monotonic() + self.result_timeout_sec
        while time.monotonic() < deadline:
            for sample in self.samples:
                self._publish_dynamic_pose(sample)
                if self.observation.stair_edge_detected:
                    self._cancel_goal()
                    return self._report("PASS")
                if not self._spin_once_short():
                    break
                time.sleep(sample.hold_sec)
            if self.observation.stair_edge_detected:
                self._cancel_goal()
                return self._report("PASS")

        self._cancel_goal()
        return self._report("STAIR_EDGE_NOT_OBSERVED")

    def _spin_once_short(self) -> bool:
        import rclpy

        if not rclpy.ok():
            return False
        rclpy.spin_once(self.node, timeout_sec=0.05)
        return True

    def _publish_static_chain(self) -> None:
        self._static_broadcaster.sendTransform(
            [_make_transform(self.node, self.route_frame_id, self.odom_frame_id, 0.0, 0.0)]
        )

    def _warmup_pose(self) -> None:
        if not self.samples:
            return
        for _ in range(10):
            self._publish_dynamic_pose(self.samples[0])
            self._spin_once_short()
            time.sleep(0.05)

    def _publish_dynamic_pose(self, sample: RoutePoseSample) -> None:
        self._dynamic_broadcaster.sendTransform(
            _make_transform(self.node, self.odom_frame_id, self.base_frame_id, sample.x, sample.y)
        )

    def _on_feedback(self, feedback_msg) -> None:
        feedback = feedback_msg.feedback
        current_edge_id = int(feedback.current_edge_id)
        self._feedback_edges.append(current_edge_id)
        self.observation.record_feedback(
            current_edge_id=current_edge_id,
            operations=tuple(feedback.operations_triggered),
        )
        print_kv("phase5a_feedback_edge", current_edge_id)
        if feedback.operations_triggered:
            print_kv("phase5a_feedback_operations", ",".join(feedback.operations_triggered))

    def _cancel_goal(self) -> None:
        if self._goal_handle is None:
            return
        cancel_future = self._goal_handle.cancel_goal_async()
        _spin_until(self.node, cancel_future, 3.0)

    def _report(self, result: str) -> int:
        print_kv("phase5a_feedback_count", self.observation.feedback_count)
        print_kv(
            "phase5a_route_feedback_seen",
            "PASS" if self.observation.feedback_seen else "FAIL",
        )
        print_kv(
            "phase5a_stair_edge_detected",
            "PASS" if self.observation.stair_edge_detected else "FAIL",
        )
        if self._feedback_edges:
            print_kv(
                "phase5a_feedback_edges",
                ",".join(str(edge_id) for edge_id in self._feedback_edges),
            )
        print_kv("phase5a_live_route_tracking_result", result)
        print_kv("phase5a_final_result", result)
        return 0 if result == "PASS" else 2


def main(argv: list[str] | None = None) -> int:
    import rclpy
    from rclpy.node import Node

    raw_argv = sys.argv[1:] if argv is None else argv
    args, ros_args = _parse_args(raw_argv)

    rclpy.init(args=[sys.argv[0], *ros_args])
    node = Node("go2w_phase5a_live_route_tracking")
    try:
        runtime = LiveRouteTrackingProbeRuntime(
            node=node,
            graph_file=Path(args.graph_file),
            action_name=args.action_name,
            start_id=args.start_id,
            goal_id=args.goal_id,
            stair_edge_id=args.stair_edge_id,
            trajectory_node_ids=_parse_node_ids(args.trajectory_node_ids),
            sample_hold_sec=args.sample_hold_sec,
            result_timeout_sec=args.result_timeout_sec,
            route_frame_id=args.route_frame_id,
            odom_frame_id=args.odom_frame_id,
            base_frame_id=args.base_frame_id,
        )
        return runtime.run()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
