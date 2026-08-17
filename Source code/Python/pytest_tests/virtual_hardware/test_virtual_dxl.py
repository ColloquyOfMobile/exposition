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


def test_a_goal_written_with_torque_off_is_held_not_refused(stub_factory):
    # A real servo accepts the value and holds still; it used to raise
    # NotImplementedError from inside the write, killing whichever thread
    # happened to be writing. DXL.init_hardware() writes registers in
    # exactly this order - torque off, configure, torque on.
    dxl = make_dxl(stub_factory)

    dxl.set("goal position", 500)

    assert dxl.get("goal position") == 500
    assert dxl.get("position") == 0, "torque is off, so nothing moves"
    assert dxl._thread is None


def test_enabling_torque_moves_to_a_goal_written_earlier(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl.set("goal position", 200)

    dxl.set("torque enabled", 1)
    dxl._thread.join(timeout=5)

    assert dxl.get("position") == 200


def test_cutting_torque_stops_a_move_in_progress(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl.set("torque enabled", 1)
    dxl.set("goal position", 100000)  # far enough to still be moving

    dxl.set("torque enabled", 0)
    dxl._thread.join(timeout=5)

    assert not dxl._thread.is_alive()
    assert dxl.get("position") < 100000


def test_set_goal_position_starts_a_thread_when_torque_enabled(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl._dict["torque enabled"] = 1

    dxl.set("goal position", 40)
    dxl._thread.join(timeout=5)

    assert dxl._thread is not None
    assert not dxl._thread.is_alive()
    assert dxl.get("position") == 40


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


def test_run_reaches_the_goal_exactly_going_up(stub_factory):
    # Exactly, not "within two steps": DXL.is_moving() compares against a
    # threshold of 20 units, and a fast profile makes a single step bigger
    # than that - a servo that stopped short would read as moving forever.
    dxl = make_dxl(stub_factory)
    dxl._dict["torque enabled"] = 1
    dxl._dict["position"] = 0
    dxl._dict["goal position"] = 25

    dxl.run()

    assert dxl.get("position") == 25


def test_run_reaches_the_goal_exactly_going_down(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl._dict["torque enabled"] = 1
    dxl._dict["position"] = 50
    dxl._dict["goal position"] = 25

    dxl.run()

    assert dxl.get("position") == 25


def test_run_returns_immediately_when_already_there(stub_factory):
    dxl = make_dxl(stub_factory)
    dxl._dict["torque enabled"] = 1
    dxl._dict["position"] = 25
    dxl._dict["goal position"] = 25

    dxl.run()

    assert dxl.get("position") == 25


def test_speed_follows_the_profile_velocity_register(stub_factory):
    # 0.229 rev/min per unit, 4096 units per revolution: the value
    # DXL.init_hardware() writes (20) is ~313 units/s, so a body's
    # 2000-unit sweep takes ~6.4s and the bar's 10000-unit crossing ~32s.
    dxl = make_dxl(stub_factory)

    dxl.set("profile velocity", 20)
    assert 310 < dxl.speed < 315

    dxl.set("profile velocity", 40)
    assert 620 < dxl.speed < 630


def test_profile_velocity_zero_means_as_fast_as_possible(stub_factory):
    # Not "don't move" - that is what the register means on real hardware.
    dxl = make_dxl(stub_factory)

    dxl.set("profile velocity", 0)

    assert dxl.speed == dxl._MAX_UNITS_PER_SECOND
