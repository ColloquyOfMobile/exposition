"""Unit tests for colloquy.hardware.female.Female's pure-arithmetic
movement methods and simple state/logic helpers.

Female.__init__ is NOT inert: it reaches into `owner.u2d2.dxls[self.name]`
and `owner.arduino` at construction time (and builds a real DXLOrigin,
Angle, Drives, Search, TurnBackAndForth, Neopixels, Test child tree), so
constructing a real Female with a stub owner is expensive/impossible to
fake cleanly. Instead, per conftest.py's documented pattern, these tests
call the target methods **unbound** against small hand-built doubles
that expose only the attributes each method body actually touches.

Her movement methods now say degrees and the Angle node turns those into
servo units, so the double carries a **real** Angle (it is inert to
construct - a ValueSetter2 that builds its children lazily, and two
property lookups) over a fake dxl. That is deliberate: the assertions
below are in servo units, so they pin the whole path from "half a sweep"
to what is written to the register, reduction included.
"""
from types import SimpleNamespace

from colloquy.hardware.angle import Angle
from colloquy.hardware.angle.conversion import REDUCTIONS
from colloquy.hardware.female import Female

# What Female.__init__ gives her: 58.594 degrees end to end, which is the
# 2000 servo units she was given before this layer existed, through her
# 1:3 reduction.
SWEEP = 58.594


def make_movable_female(stub_factory, origin_value, sweep=SWEEP, position_memory=None):
    """Build a fake exposing exactly what turn_to_max_position/
    turn_to_min_position/turn_to_origin/toggle_position touch: .sweep,
    .angle (a real Angle over a fake dxl and a fake origin), and
    ._position_memory. Records every written goal position in `written`,
    in servo units, so tests can assert on the exact computed value.

    toggle_position()'s body calls self.turn_to_max_position()/
    self.turn_to_min_position() (not the module-level functions), so the
    fake also needs bound-looking attributes for those two methods; they
    are wired to invoke the real unbound Female methods against this same
    fake, keeping a single source of truth for the arithmetic."""
    written = []
    body = stub_factory(
        dxl_origin=SimpleNamespace(get=lambda: origin_value),
        dxl=SimpleNamespace(
            goal_position=SimpleNamespace(write=lambda v: written.append(v))
        ),
    )
    fake = SimpleNamespace(
        sweep=sweep,
        angle=Angle(owner=body, reduction=REDUCTIONS["female"]),
        _position_memory=position_memory,
    )
    fake.written = written
    fake.turn_to_max_position = lambda: Female.turn_to_max_position(fake)
    fake.turn_to_min_position = lambda: Female.turn_to_min_position(fake)
    return fake


def test_turn_to_max_position_writes_half_a_sweep_past_the_origin(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=1000)

    Female.turn_to_max_position(fake)

    # Half of 58.594 degrees, through the 1:3 reduction, is the same 1000
    # servo units she was given before - the conversion is faithful, not a
    # re-tuning.
    assert fake.written == [2000]
    assert fake._position_memory == "max"


def test_turn_to_min_position_writes_half_a_sweep_the_other_way(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=1000)

    Female.turn_to_min_position(fake)

    assert fake.written == [0]
    assert fake._position_memory == "min"


def test_the_sweep_is_measured_from_wherever_the_origin_is(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=500, sweep=20)

    Female.turn_to_max_position(fake)
    Female.turn_to_min_position(fake)

    # 10 degrees either side: 341 units through the reduction.
    assert fake.written == [841, 159]


def test_a_negative_result_is_written_as_a_negative_number(stub_factory):
    # Extended position mode, and her origin is 100 on the rig today: the
    # bottom of her sweep is genuinely below the servo's zero.
    fake = make_movable_female(stub_factory, origin_value=100)

    Female.turn_to_min_position(fake)

    assert fake.written == [-900]


def test_turn_to_takes_an_angle_in_degrees(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=1000)

    Female.turn_to(fake, 20)

    assert fake.written == [1683]


def test_turn_to_origin_writes_the_origin_and_leaves_memory_untouched(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=1234, position_memory="max")

    Female.turn_to_origin(fake)

    assert fake.written == [1234]
    # turn_to_origin has no _position_memory assignment in its body.
    assert fake._position_memory == "max"


def test_toggle_position_from_none_goes_to_max(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=1000, position_memory=None)

    Female.toggle_position(fake)

    assert fake._position_memory == "max"
    assert fake.written == [2000]


def test_toggle_position_from_max_goes_to_min(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=1000, position_memory="max")

    Female.toggle_position(fake)

    assert fake._position_memory == "min"
    assert fake.written == [0]


def test_toggle_position_from_min_goes_to_max(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=1000, position_memory="min")

    Female.toggle_position(fake)

    assert fake._position_memory == "max"
    assert fake.written == [2000]


def test_toggle_position_full_cycle_from_fresh_fake(stub_factory):
    fake = make_movable_female(stub_factory, origin_value=1000, position_memory=None)

    Female.toggle_position(fake)  # None -> max
    Female.toggle_position(fake)  # max -> min
    Female.toggle_position(fake)  # min -> max

    assert fake._position_memory == "max"
    assert fake.written == [2000, 0, 2000]


def test_the_sweep_is_read_from_params_so_the_page_can_change_it():
    # A property, not a value held at construction: a range edited on the
    # params page takes effect on the next sway rather than at the next
    # restart.
    fake = SimpleNamespace(
        name="female1",
        params={"female1": {"motion range": 40}},
    )

    assert Female.sweep.fget(fake) == 40

    fake.params["female1"]["motion range"] = 20

    assert Female.sweep.fget(fake) == 20


def make_satisfaction_female(o_satisfied, p_satisfied):
    """Build a fake exposing exactly what is_satisfied() touches:
    .drives.o_drive.is_satisfied / .drives.p_drive.is_satisfied."""
    return SimpleNamespace(
        drives=SimpleNamespace(
            o_drive=SimpleNamespace(is_satisfied=o_satisfied),
            p_drive=SimpleNamespace(is_satisfied=p_satisfied),
        )
    )


def test_is_satisfied_true_when_both_drives_satisfied():
    fake = make_satisfaction_female(o_satisfied=True, p_satisfied=True)

    assert Female.is_satisfied(fake) is True


def test_is_satisfied_true_when_only_o_drive_satisfied():
    fake = make_satisfaction_female(o_satisfied=True, p_satisfied=False)

    assert Female.is_satisfied(fake) is True


def test_is_satisfied_true_when_only_p_drive_satisfied():
    fake = make_satisfaction_female(o_satisfied=False, p_satisfied=True)

    assert Female.is_satisfied(fake) is True


def test_is_satisfied_false_when_neither_drive_satisfied():
    fake = make_satisfaction_female(o_satisfied=False, p_satisfied=False)

    assert Female.is_satisfied(fake) is False
