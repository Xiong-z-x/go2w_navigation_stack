import argparse
from typing import Any, Optional

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.task import Future


class RvizGoalBridge(Node):
    def __init__(self) -> None:
        super().__init__("go2w_rviz_goal_bridge")
        self._action_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self._goal_subscription = self.create_subscription(
            PoseStamped,
            "/move_base_simple/goal",
            self._goal_callback,
            10,
        )
        self._timer = self.create_timer(0.1, self._process_pending_goal)
        self._pending_goal: Optional[PoseStamped] = None
        self._active_goal_handle: Optional[Any] = None
        self._cancel_future: Optional[Future] = None
        self._send_future: Optional[Future] = None
        self._sequence = 0

    def _goal_callback(self, msg: PoseStamped) -> None:
        self._sequence += 1
        self._pending_goal = msg
        self.get_logger().info(
            f"received_rviz_goal seq={self._sequence} frame={msg.header.frame_id} "
            f"x={float(msg.pose.position.x):.3f} y={float(msg.pose.position.y):.3f}"
        )

    def _process_pending_goal(self) -> None:
        if self._pending_goal is None:
            return

        if not self._action_client.server_is_ready():
            if not self._action_client.wait_for_server(timeout_sec=0.0):
                return

        if self._send_future is not None or self._cancel_future is not None:
            return

        if self._active_goal_handle is not None:
            self.get_logger().info("canceling_active_goal_for_new_rviz_goal")
            self._cancel_future = self._active_goal_handle.cancel_goal_async()
            self._cancel_future.add_done_callback(self._handle_cancel_done)
            return

        goal = NavigateToPose.Goal()
        goal.pose = self._pending_goal
        if not goal.pose.header.frame_id:
            goal.pose.header.frame_id = "odom"
        self._pending_goal = None
        self.get_logger().info(
            f"forwarding_rviz_goal frame={goal.pose.header.frame_id} "
            f"x={float(goal.pose.pose.position.x):.3f} y={float(goal.pose.pose.position.y):.3f}"
        )
        self._send_future = self._action_client.send_goal_async(goal)
        self._send_future.add_done_callback(self._handle_goal_response)

    def _handle_cancel_done(self, future: Future) -> None:
        self._cancel_future = None
        self._active_goal_handle = None
        try:
            future.result()
        except Exception as exc:  # pragma: no cover - ROS action transport failure
            self.get_logger().warning(f"rviz_goal_cancel_failed: {exc}")
            return
        self.get_logger().info("active_goal_canceled")

    def _handle_goal_response(self, future: Future) -> None:
        self._send_future = None
        try:
            goal_handle = future.result()
        except Exception as exc:  # pragma: no cover - ROS action transport failure
            self.get_logger().error(f"rviz_goal_send_failed: {exc}")
            return
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().warning("rviz_goal_rejected")
            return

        self._active_goal_handle = goal_handle
        self.get_logger().info("rviz_goal_accepted")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._handle_result_done)

    def _handle_result_done(self, future: Future) -> None:
        self._active_goal_handle = None
        try:
            wrapped_result = future.result()
        except Exception as exc:  # pragma: no cover - ROS action transport failure
            self.get_logger().error(f"rviz_goal_result_failed: {exc}")
            return
        self.get_logger().info(f"rviz_goal_result_status={wrapped_result.status}")


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Forward RViz SetGoal poses to NavigateToPose.")
    parser.parse_known_args(args=args)
    rclpy.init(args=args)
    node = RvizGoalBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
