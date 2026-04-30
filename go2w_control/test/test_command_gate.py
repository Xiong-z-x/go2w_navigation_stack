from go2w_control_runtime.command_gate import CommandGateCore


def test_default_owner_is_flat() -> None:
    gate = CommandGateCore()

    assert gate.active_owner == "flat"


def test_flat_owner_forwards_only_flat_commands() -> None:
    gate = CommandGateCore()

    assert gate.should_forward("flat") is True
    assert gate.should_forward("stair") is False


def test_stair_owner_forwards_only_stair_commands() -> None:
    gate = CommandGateCore()

    assert gate.set_owner("stair") is True
    assert gate.should_forward("flat") is False
    assert gate.should_forward("stair") is True


def test_invalid_owner_is_rejected_without_state_change() -> None:
    gate = CommandGateCore()

    assert gate.set_owner("flying") is False

    assert gate.active_owner == "flat"
    assert gate.last_rejected_owner == "flying"


def test_muted_source_is_reported() -> None:
    gate = CommandGateCore()

    decision = gate.evaluate("stair")

    assert decision.forward is False
    assert decision.reason == "muted_by_owner:flat"
