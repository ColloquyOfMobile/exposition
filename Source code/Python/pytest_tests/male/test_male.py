"""Unit tests for colloquy.hardware.male.Male's pure-arithmetic movement
methods, simple state/logic helpers, and blink-pattern dispatch.

Male.__init__ is NOT inert: it reaches into `owner.u2d2.dxls[self.name]`,
`owner.arduino`, `self.colloquy.light_patterns`, builds a real DXLOrigin,
LightSensor x4, Drives (itself needing `owner.params["drive start
values"]`), Search, TurnBackAndForth, Neopixels - so constructing a real
Male with a stub owner is expensive/impossible to fake cleanly. Instead,
per conftest.py's documented pattern (and mirroring
pytest_tests/female/test_female.py's approach for the sibling class),
these tests call the target methods **unbound** against small hand-built
doubles that expose only the attributes each method body actually
touches.
"""
from collections import deque
from types import SimpleNamespace

from colloquy import Colloquy
from colloquy.hardware.male import Male


def _light_patterns():
    # Same technique as pytest_tests/test_light_patterns.py: light_patterns
    # is a pure @property that doesn't touch self beyond being called on
    # an instance.
    return Colloquy.light_patterns.fget(SimpleNamespace())


# --- get_blink_pattern() -------------------------------------------------


def _deques_for(male_name):
    """Mirrors Male.__init__'s exact construction of _light_pattern_deques
    (lines 20-23 of hardware/male/__init__.py):

        for k, v in self.colloquy.light_patterns[self.name].items():
            self._light_pattern_deques[k] = deque(v, maxlen=len(v))
    """
    patterns = _light_patterns()[male_name]
    return {k: deque(v, maxlen=len(v)) for k, v in patterns.items()}


def test_light_pattern_deque_construction_matches_init_logic():
    # Cross-check: confirms Male.__init__ would build exactly 4 deques per
    # male, keyed by the same 4 tuples which_is_frustated() can return.
    deques = _deques_for("male1")

    assert set(deques.keys()) == {tuple(), ("O",), ("P",), ("O", "P")}
    patterns = _light_patterns()["male1"]
    for k, v in patterns.items():
        assert list(deques[k]) == list(v)
        assert deques[k].maxlen == len(v) == 10


def make_blinking_male(male_name, which_is_frustated_return):
    deques = _deques_for(male_name)
    fake = SimpleNamespace(
        _light_pattern_deques=deques,
        drives=SimpleNamespace(
            which_is_frustated=lambda: which_is_frustated_return
        ),
    )
    return fake, deques


def test_get_blink_pattern_returns_neither_pattern_when_which_is_frustated_empty():
    fake, deques = make_blinking_male("male1", tuple())

    assert Male.get_blink_pattern(fake) is deques[tuple()]


def test_get_blink_pattern_returns_o_pattern():
    fake, deques = make_blinking_male("male1", ("O",))

    assert Male.get_blink_pattern(fake) is deques[("O",)]


def test_get_blink_pattern_returns_p_pattern():
    fake, deques = make_blinking_male("male1", ("P",))

    assert Male.get_blink_pattern(fake) is deques[("P",)]


def test_get_blink_pattern_returns_both_pattern():
    fake, deques = make_blinking_male("male1", ("O", "P"))

    assert Male.get_blink_pattern(fake) is deques[("O", "P")]


def test_get_blink_pattern_works_for_male2_too():
    fake, deques = make_blinking_male("male2", ("O",))

    assert Male.get_blink_pattern(fake) is deques[("O",)]


# --- set_current_position_as_dxl_origin() --------------------------------


def test_set_current_position_as_dxl_origin_reads_position_and_sets_origin():
    recorded = []
    fake = SimpleNamespace(
        dxl_origin=SimpleNamespace(set=lambda v: recorded.append(v)),
        dxl=SimpleNamespace(position=SimpleNamespace(read=lambda: 555)),
    )

    Male.set_current_position_as_dxl_origin(fake)

    assert recorded == [555]


# --- turn_to_max_position / turn_to_min_position / turn_to_origin /
# toggle_position ---------------------------------------------------------


def make_movable_male(origin_value, motion_range=2000, position_memory=None):
    """Build a fake exposing exactly what turn_to_max_position/
    turn_to_min_position/turn_to_origin/toggle_position touch:
    ._dxl_origin.get(), ._motion_range, .dxl.goal_position.write(value),
    ._position_memory. Records every written goal position in
    `written` so tests can assert on the exact computed value.

    toggle_position()'s body calls self.turn_to_max_position()/
    self.turn_to_min_position() (not the module-level functions), so the
    fake also needs bound-looking attributes for those two methods; they
    are wired to invoke the real unbound Male methods against this same
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
    fake.turn_to_max_position = lambda: Male.turn_to_max_position(fake)
    fake.turn_to_min_position = lambda: Male.turn_to_min_position(fake)
    return fake


def test_turn_to_max_position_writes_origin_plus_half_motion_range():
    fake = make_movable_male(origin_value=1000, motion_range=2000)

    Male.turn_to_max_position(fake)

    assert fake.written == [1000 + 2000 // 2]
    assert fake._position_memory == "max"


def test_turn_to_min_position_writes_origin_minus_half_motion_range():
    fake = make_movable_male(origin_value=1000, motion_range=2000)

    Male.turn_to_min_position(fake)

    assert fake.written == [1000 - 2000 // 2]
    assert fake._position_memory == "min"


def test_turn_to_max_position_uses_current_dxl_origin_and_motion_range():
    fake = make_movable_male(origin_value=500, motion_range=300)

    Male.turn_to_max_position(fake)

    assert fake.written == [500 + 300 // 2]
    assert fake._position_memory == "max"


def test_turn_to_min_position_uses_current_dxl_origin_and_motion_range():
    fake = make_movable_male(origin_value=500, motion_range=300)

    Male.turn_to_min_position(fake)

    assert fake.written == [500 - 300 // 2]
    assert fake._position_memory == "min"


def test_turn_to_origin_writes_raw_origin_value_and_leaves_memory_untouched():
    fake = make_movable_male(origin_value=1234, position_memory="max")

    Male.turn_to_origin(fake)

    assert fake.written == [1234]
    # turn_to_origin has no _position_memory assignment in its body.
    assert fake._position_memory == "max"


def test_toggle_position_from_none_goes_to_max():
    fake = make_movable_male(origin_value=1000, motion_range=2000, position_memory=None)

    Male.toggle_position(fake)

    assert fake._position_memory == "max"
    assert fake.written == [1000 + 2000 // 2]


def test_toggle_position_from_max_goes_to_min():
    fake = make_movable_male(origin_value=1000, motion_range=2000, position_memory="max")

    Male.toggle_position(fake)

    assert fake._position_memory == "min"
    assert fake.written == [1000 - 2000 // 2]


def test_toggle_position_from_min_goes_to_max():
    fake = make_movable_male(origin_value=1000, motion_range=2000, position_memory="min")

    Male.toggle_position(fake)

    assert fake._position_memory == "max"
    assert fake.written == [1000 + 2000 // 2]


def test_toggle_position_full_cycle_from_fresh_fake():
    fake = make_movable_male(origin_value=1000, motion_range=2000, position_memory=None)

    Male.toggle_position(fake)  # None -> max
    Male.toggle_position(fake)  # max -> min
    Male.toggle_position(fake)  # min -> max

    assert fake._position_memory == "max"
    assert fake.written == [
        1000 + 2000 // 2,
        1000 - 2000 // 2,
        1000 + 2000 // 2,
    ]


# --- is_satisfied() -------------------------------------------------------


def make_satisfaction_male(o_satisfied, p_satisfied):
    """Build a fake exposing exactly what is_satisfied() touches:
    .drives.o_drive.is_satisfied / .drives.p_drive.is_satisfied."""
    return SimpleNamespace(
        drives=SimpleNamespace(
            o_drive=SimpleNamespace(is_satisfied=o_satisfied),
            p_drive=SimpleNamespace(is_satisfied=p_satisfied),
        )
    )


def test_is_satisfied_true_when_both_drives_satisfied():
    fake = make_satisfaction_male(o_satisfied=True, p_satisfied=True)

    assert Male.is_satisfied(fake) is True


def test_is_satisfied_true_when_only_o_drive_satisfied():
    fake = make_satisfaction_male(o_satisfied=True, p_satisfied=False)

    assert Male.is_satisfied(fake) is True


def test_is_satisfied_true_when_only_p_drive_satisfied():
    fake = make_satisfaction_male(o_satisfied=False, p_satisfied=True)

    assert Male.is_satisfied(fake) is True


def test_is_satisfied_false_when_neither_drive_satisfied():
    fake = make_satisfaction_male(o_satisfied=False, p_satisfied=False)

    assert Male.is_satisfied(fake) is False
