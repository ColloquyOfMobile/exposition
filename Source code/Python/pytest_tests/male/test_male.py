"""Unit tests for colloquy.drivers.male.Male's pure-arithmetic movement
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
from types import SimpleNamespace

from colloquy import Colloquy
from colloquy.drivers.angle import Angle
from colloquy.drivers.angle.conversion import REDUCTIONS
from colloquy.drivers.male import Male

# What Male.__init__ gives him: 58.594 degrees end to end, which is the
# 2000 servo units he was given before this layer existed, through his
# 1:3 reduction - the same sway a female makes.
SWEEP = 58.594


def _light_patterns():
    # Same technique as pytest_tests/test_light_patterns.py: light_patterns
    # is a pure @property that doesn't touch self beyond being called on
    # an instance.
    return Colloquy.light_patterns.fget(SimpleNamespace())


# --- get_blink_pattern() -------------------------------------------------


def _patterns_for(male_name):
    """Mirrors Male.__init__'s exact construction of _light_patterns
    (drivers/male/__init__.py):

        self._light_patterns = {
            state: tuple(bits)
            for state, bits in self.colloquy.light_patterns[self.name].items()
        }
    """
    patterns = _light_patterns()[male_name]
    return {state: tuple(bits) for state, bits in patterns.items()}


def test_light_pattern_construction_matches_init_logic():
    # Cross-check: confirms Male.__init__ would build exactly 4 patterns per
    # male, keyed by the same 4 tuples which_is_frustated() can return.
    built = _patterns_for("male1")

    assert set(built.keys()) == {tuple(), ("O",), ("P",), ("O", "P")}
    patterns = _light_patterns()["male1"]
    for state, bits in patterns.items():
        assert built[state] == tuple(bits)
        assert len(built[state]) == 10


def test_patterns_are_immutable_sequences():
    # They used to be deques rotated in place by Blink, one step per bit.
    # Blink now sends each burst from its first bit (light_pattern_timing.py),
    # so nothing may quietly change what the next burst starts on.
    for state, bits in _patterns_for("male2").items():
        assert isinstance(bits, tuple), state


def make_blinking_male(male_name, which_is_frustated_return):
    patterns = _patterns_for(male_name)
    fake = SimpleNamespace(
        _light_patterns=patterns,
        drives=SimpleNamespace(
            which_is_frustated=lambda: which_is_frustated_return
        ),
    )
    return fake, patterns


def test_get_blink_pattern_returns_neither_pattern_when_which_is_frustated_empty():
    fake, patterns = make_blinking_male("male1", tuple())

    assert Male.get_blink_pattern(fake) is patterns[tuple()]


def test_get_blink_pattern_returns_o_pattern():
    fake, patterns = make_blinking_male("male1", ("O",))

    assert Male.get_blink_pattern(fake) is patterns[("O",)]


def test_get_blink_pattern_returns_p_pattern():
    fake, patterns = make_blinking_male("male1", ("P",))

    assert Male.get_blink_pattern(fake) is patterns[("P",)]


def test_get_blink_pattern_returns_both_pattern():
    fake, patterns = make_blinking_male("male1", ("O", "P"))

    assert Male.get_blink_pattern(fake) is patterns[("O", "P")]


def test_get_blink_pattern_works_for_male2_too():
    fake, patterns = make_blinking_male("male2", ("O",))

    assert Male.get_blink_pattern(fake) is patterns[("O",)]


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


def make_movable_male(stub_factory, origin_value, sweep=SWEEP, position_memory=None):
    """Build a fake exposing exactly what turn_to_max_position/
    turn_to_min_position/turn_to_origin/toggle_position touch: .sweep,
    .angle (a real Angle over a fake dxl and a fake origin, so the
    assertions below cover the whole path from degrees to what reaches
    the register), and ._position_memory. Records every written goal
    position, in servo units, in `written`.

    toggle_position()'s body calls self.turn_to_max_position()/
    self.turn_to_min_position() (not the module-level functions), so the
    fake also needs bound-looking attributes for those two methods; they
    are wired to invoke the real unbound Male methods against this same
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
        angle=Angle(owner=body, reduction=REDUCTIONS["male"]),
        _position_memory=position_memory,
    )
    fake.written = written
    fake.turn_to_max_position = lambda: Male.turn_to_max_position(fake)
    fake.turn_to_min_position = lambda: Male.turn_to_min_position(fake)
    return fake


def test_turn_to_max_position_writes_half_a_sweep_past_the_origin(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=1000)

    Male.turn_to_max_position(fake)

    # Half of 58.594 degrees, through the 1:3 reduction, is the same 1000
    # servo units he was given before this layer existed - unchanged by
    # the reduction being corrected, because the params number moved with
    # it.
    assert fake.written == [2000]
    assert fake._position_memory == "max"


def test_turn_to_min_position_writes_half_a_sweep_the_other_way(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=1000)

    Male.turn_to_min_position(fake)

    assert fake.written == [0]
    assert fake._position_memory == "min"


def test_the_same_angle_moves_him_exactly_as_far_as_a_female(stub_factory):
    # 20 degrees is 683 units on him as it is on her - both geared 1:3.
    # This test asserted 228 while he was believed to turn one for one,
    # and it is kept, inverted, because that belief is the mistake worth
    # having a test stand against.
    fake = make_movable_male(stub_factory, origin_value=0, sweep=40)

    Male.turn_to_max_position(fake)

    assert fake.written == [683]


def test_the_sweep_is_measured_from_wherever_the_origin_is(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=500, sweep=20)

    Male.turn_to_max_position(fake)
    Male.turn_to_min_position(fake)

    assert fake.written == [841, 159]


def test_turn_to_takes_an_angle_in_degrees(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=1000)

    Male.turn_to(fake, 20)

    assert fake.written == [1683]


def test_turn_to_origin_writes_the_origin_and_leaves_memory_untouched(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=1234, position_memory="max")

    Male.turn_to_origin(fake)

    assert fake.written == [1234]
    # turn_to_origin has no _position_memory assignment in its body.
    assert fake._position_memory == "max"


def test_toggle_position_from_none_goes_to_max(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=1000, position_memory=None)

    Male.toggle_position(fake)

    assert fake._position_memory == "max"
    assert fake.written == [2000]


def test_toggle_position_from_max_goes_to_min(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=1000, position_memory="max")

    Male.toggle_position(fake)

    assert fake._position_memory == "min"
    assert fake.written == [0]


def test_toggle_position_from_min_goes_to_max(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=1000, position_memory="min")

    Male.toggle_position(fake)

    assert fake._position_memory == "max"
    assert fake.written == [2000]


def test_toggle_position_full_cycle_from_fresh_fake(stub_factory):
    fake = make_movable_male(stub_factory, origin_value=1000, position_memory=None)

    Male.toggle_position(fake)  # None -> max
    Male.toggle_position(fake)  # max -> min
    Male.toggle_position(fake)  # min -> max

    assert fake._position_memory == "max"
    assert fake.written == [2000, 0, 2000]


def test_the_sweep_is_read_from_params_so_the_page_can_change_it():
    # A property, not a value held at construction: a range edited on the
    # params page takes effect on the next sway rather than at the next
    # restart.
    fake = SimpleNamespace(
        name="male1",
        params={"male1": {"motion range": 40}},
    )

    assert Male.sweep.fget(fake) == 40

    fake.params["male1"]["motion range"] = 20

    assert Male.sweep.fget(fake) == 20


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
