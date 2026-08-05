"""Unit tests for colloquy.hardware.female.Female's pure-arithmetic
movement methods and simple state/logic helpers.

Female.__init__ is NOT inert: it reaches into `owner.u2d2.dxls[self.name]`
and `owner.arduino` at construction time (and builds a real DXLOrigin,
Drives, Search, TurnBackAndForth, Neopixels, Test child tree), so
constructing a real Female with a stub owner is expensive/impossible to
fake cleanly. Instead, per conftest.py's documented pattern, these tests
call the target methods **unbound** against small hand-built doubles
that expose only the attributes each method body actually touches.
"""
from types import SimpleNamespace

from colloquy.hardware.female import Female


def make_movable_female(origin_value, motion_range=2000, position_memory=None):
    """Build a fake exposing exactly what turn_to_max_position/
    turn_to_min_position/turn_to_origin/toggle_position touch:
    ._dxl_origin.get(), ._motion_range, .dxl.goal_position.write(value),
    ._position_memory. Records every written goal position in
    `written` so tests can assert on the exact computed value.

    toggle_position()'s body calls self.turn_to_max_position()/
    self.turn_to_min_position() (not the module-level functions), so the
    fake also needs bound-looking attributes for those two methods; they
    are wired to invoke the real unbound Female methods against this same
    fake, keeping a single source of truth for the arithmetic."""
    written = []
    fake = SimpleNamespace(
        _dxl_origin=SimpleNamespace(get=lambda: origin_value),
        _motion_range=motion_range,
        dxl=SimpleNamespace(
            goal_position=SimpleNamespace(write=lambda v: written.append(v))
        ),
        _position_memory=position_memory,
    )
    fake.written = written
    fake.turn_to_max_position = lambda: Female.turn_to_max_position(fake)
    fake.turn_to_min_position = lambda: Female.turn_to_min_position(fake)
    return fake


def test_turn_to_max_position_writes_origin_plus_half_motion_range():
    fake = make_movable_female(origin_value=1000, motion_range=2000)

    Female.turn_to_max_position(fake)

    assert fake.written == [1000 + 2000 // 2]
    assert fake._position_memory == "max"


def test_turn_to_min_position_writes_origin_minus_half_motion_range():
    fake = make_movable_female(origin_value=1000, motion_range=2000)

    Female.turn_to_min_position(fake)

    assert fake.written == [1000 - 2000 // 2]
    assert fake._position_memory == "min"


def test_turn_to_max_position_uses_current_dxl_origin_and_motion_range():
    fake = make_movable_female(origin_value=500, motion_range=300)

    Female.turn_to_max_position(fake)

    assert fake.written == [500 + 300 // 2]
    assert fake._position_memory == "max"


def test_turn_to_min_position_uses_current_dxl_origin_and_motion_range():
    fake = make_movable_female(origin_value=500, motion_range=300)

    Female.turn_to_min_position(fake)

    assert fake.written == [500 - 300 // 2]
    assert fake._position_memory == "min"


def test_turn_to_origin_writes_raw_origin_value_and_leaves_memory_untouched():
    fake = make_movable_female(origin_value=1234, position_memory="max")

    Female.turn_to_origin(fake)

    assert fake.written == [1234]
    # turn_to_origin has no _position_memory assignment in its body.
    assert fake._position_memory == "max"


def test_toggle_position_from_none_goes_to_max():
    fake = make_movable_female(origin_value=1000, motion_range=2000, position_memory=None)

    Female.toggle_position(fake)

    assert fake._position_memory == "max"
    assert fake.written == [1000 + 2000 // 2]


def test_toggle_position_from_max_goes_to_min():
    fake = make_movable_female(origin_value=1000, motion_range=2000, position_memory="max")

    Female.toggle_position(fake)

    assert fake._position_memory == "min"
    assert fake.written == [1000 - 2000 // 2]


def test_toggle_position_from_min_goes_to_max():
    fake = make_movable_female(origin_value=1000, motion_range=2000, position_memory="min")

    Female.toggle_position(fake)

    assert fake._position_memory == "max"
    assert fake.written == [1000 + 2000 // 2]


def test_toggle_position_full_cycle_from_fresh_fake():
    fake = make_movable_female(origin_value=1000, motion_range=2000, position_memory=None)

    Female.toggle_position(fake)  # None -> max
    Female.toggle_position(fake)  # max -> min
    Female.toggle_position(fake)  # min -> max

    assert fake._position_memory == "max"
    assert fake.written == [
        1000 + 2000 // 2,
        1000 - 2000 // 2,
        1000 + 2000 // 2,
    ]


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
