from __future__ import annotations

from dataclasses import dataclass

from go2w_control_runtime.motion_profiles import motion_mode_for_owner


VALID_OWNERS = frozenset({"flat", "stair"})


@dataclass(frozen=True)
class CommandDecision:
    source: str
    active_owner: str
    forward: bool
    reason: str


class CommandGateCore:
    def __init__(self, initial_owner: str = "flat") -> None:
        if initial_owner not in VALID_OWNERS:
            raise ValueError(f"invalid initial owner: {initial_owner}")
        self.active_owner = initial_owner
        self.active_mode = motion_mode_for_owner(initial_owner)
        self.last_rejected_owner = ""

    def set_owner(self, owner: str) -> bool:
        normalized = owner.strip().lower()
        if normalized not in VALID_OWNERS:
            self.last_rejected_owner = owner
            return False
        self.active_owner = normalized
        self.active_mode = motion_mode_for_owner(normalized)
        self.last_rejected_owner = ""
        return True

    def should_forward(self, source: str) -> bool:
        return self.evaluate(source).forward

    def evaluate(self, source: str) -> CommandDecision:
        normalized = source.strip().lower()
        if normalized == self.active_owner:
            return CommandDecision(
                source=normalized,
                active_owner=self.active_owner,
                forward=True,
                reason="active_owner",
            )
        return CommandDecision(
            source=normalized,
            active_owner=self.active_owner,
            forward=False,
            reason=f"muted_by_owner:{self.active_owner}",
        )


def main() -> None:
    import rclpy
    from geometry_msgs.msg import Twist
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from std_msgs.msg import String

    class CommandGateNode(Node):
        def __init__(self) -> None:
            super().__init__("go2w_command_gate")
            self._core = CommandGateCore()
            self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
            self._owner_pub = self.create_publisher(
                String,
                "/go2w/control/active_owner",
                10,
            )
            self._mode_pub = self.create_publisher(
                String,
                "/go2w/control/active_mode",
                10,
            )
            self._decision_pub = self.create_publisher(
                String,
                "/go2w/control/command_gate_events",
                10,
            )
            self.create_subscription(
                String,
                "/go2w/control/command_owner",
                self._on_owner,
                10,
            )
            self.create_subscription(
                Twist,
                "/go2w/control/flat_cmd_vel",
                lambda msg: self._on_cmd("flat", msg),
                10,
            )
            self.create_subscription(
                Twist,
                "/go2w/control/stair_cmd_vel",
                lambda msg: self._on_cmd("stair", msg),
                10,
            )
            self._publish_owner()
            self._publish_mode()
            self.get_logger().info(
                "go2w_command_gate_state: "
                f"owner={self._core.active_owner} mode={self._core.active_mode}"
            )

        def _on_owner(self, msg: String) -> None:
            if not self._core.set_owner(msg.data):
                self._publish_event(f"owner_rejected:{msg.data}")
                return
            self._publish_owner()
            self._publish_mode()
            self._publish_event(f"owner_active:{self._core.active_owner}")
            self.get_logger().info(
                "go2w_command_gate_state: "
                f"owner={self._core.active_owner} mode={self._core.active_mode}"
            )

        def _on_cmd(self, source: str, msg: Twist) -> None:
            decision = self._core.evaluate(source)
            self._publish_event(f"{decision.source}:{decision.reason}")
            if decision.forward:
                self._cmd_pub.publish(msg)

        def _publish_owner(self) -> None:
            msg = String()
            msg.data = self._core.active_owner
            self._owner_pub.publish(msg)

        def _publish_mode(self) -> None:
            msg = String()
            msg.data = self._core.active_mode
            self._mode_pub.publish(msg)

        def _publish_event(self, value: str) -> None:
            msg = String()
            msg.data = value
            self._decision_pub.publish(msg)

    rclpy.init()
    node = CommandGateNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
