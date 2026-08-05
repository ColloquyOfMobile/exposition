"""Unit tests for colloquy.virtual_hardware.virtual_dxl.VirtualDXL - the
in-memory stand-in for one physical Dynamixel register set, driven by
VirtualPacketHandler's read/write*TxRx methods when running simulated.

VirtualDXL.__init__ only touches its own _dict/attrs - no serial/thread
side effects - so constructing it against a stub_factory owner is safe.
set("goal position", ...) is the one path that spawns a background Thread
(only when torque is enabled); tests either keep goal == position (so the
spawned thread's run() returns on its first check) or replace Thread with
a fake so the "reuse the existing thread" branch can be exercised without
any real threading.
"""
from pathlib import Path

from colloquy.virtual_hardware.virtual_dxl import VirtualDXL


def make_dxl(stub_factory, dxl_id=1):
    # set("goal position", ...) builds the spawned Thread's name from
    # self.path, which walks up through owner.path - give the stub one.
    return VirtualDXL(owner=stub_factory(path=Path("owner")), dxl_id=dxl_id)


def test_name_includes_dxl_id():
    dxl = VirtualDXL(owner=None, dxl_id=3)

    assert dxl.name == "virtual_dxl_3"


def test_defaults(stub_factory):
    dxl = make_dxl(stub_factory)

    assert dxl.get("position") == 0
    assert dxl.get("goal position") == 0
    assert dxl.get("torque enabled") == 0
    assert dxl.get("temperature") == 25
    assert dxl.position == 0


def test_set_non_goal_position_label_just_stores_the_value(stub_factory):
    dxl = make_dxl(stub_factory)

    dxl.set("torque enabled", 1)

    assert dxl.get("torque enabled") == 1
    assert dxl._thread is None


def test_position_property_reflects_dict(stub_factory):
    dxl = make_dxl(stub_factory)

    dxl._dict["position"] = 500

    assert dxl.position == 500


def test_set_goal_position_raises_when_torque_disabled(stub_factory):
    dxl = make_dxl(stub_factory)

    try:
        dxl.set("goal position", 500)
    except NotImplementedError:
        pass
    else:
        assert False, "expected NotImplementedError"

    # The dict is still updated before the torque check fires.
    assert dxl.get("goal position") == 500


def test_set_goal_position_starts_a_thread_when_torque_enabled(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl._dict["torque enabled"] = 1

    dxl.set("goal position", 0)  # goal == current position -> run() returns fast
    dxl._thread.join(timeout=1)

    assert dxl._thread is not None
    assert not dxl._thread.is_alive()
    assert dxl.get("position") == 0


def test_set_goal_position_reuses_existing_thread_while_alive(stub_factory, monkeypatch):
    dxl = make_dxl(stub_factory)
    dxl._dict["torque enabled"] = 1

    class FakeThread:
        def __init__(self, target, name, daemon):
            self.target = target

        def start(self):
            pass

        def is_alive(self):
            return True

    monkeypatch.setattr("colloquy.virtual_hardware.virtual_dxl.Thread", FakeThread)

    dxl.set("goal position", 500)
    first_thread = dxl._thread
    dxl.set("goal position", 900)

    # Still updates the target value, but doesn't spawn a second thread.
    assert dxl.get("goal position") == 900
    assert dxl._thread is first_thread


def test_run_steps_position_up_toward_goal(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl._dict["position"] = 0
    dxl._dict["goal position"] = 25

    dxl.run()

    assert dxl.get("position") == 10


def test_run_steps_position_down_toward_goal(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl._dict["position"] = 50
    dxl._dict["goal position"] = 25

    dxl.run()

    assert dxl.get("position") == 40


def test_run_returns_immediately_when_already_within_two_steps_of_goal(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl._dict["position"] = 25
    dxl._dict["goal position"] = 25

    dxl.run()

    assert dxl.get("position") == 25
