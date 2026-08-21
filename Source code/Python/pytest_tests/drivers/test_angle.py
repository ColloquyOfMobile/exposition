"""Unit tests for colloquy.drivers.angle.Angle - the node that lets every
body be commanded in degrees of itself rather than in servo units.

Angle is inert to construct: two attributes and a ValueSetter2, which
builds its own children lazily (see the comment in value_setter2.py). So
these build a real Angle over a hand-made body exposing only what it
touches - `.dxl_origin.get()`, `.dxl.position.read()`,
`.dxl.goal_position.read()/.write()` - and assert in servo units on the
way out, degrees on the way in.

The reduction is the thing worth pinning: the same 20 degrees is 228
units on a male and 683 on a female, and writing the male's number to the
female is exactly the confusion this node removes.
"""
from types import SimpleNamespace

import pytest

from colloquy.drivers.angle import Angle
from colloquy.drivers.angle.conversion import REDUCTIONS


def make_angle(stub_factory, reduction=3, origin=1000, position=1000, moving=False):
    written = []
    goal = [position]

    def write(value):
        written.append(value)
        goal[0] = value

    dxl = SimpleNamespace(
        position=SimpleNamespace(read=lambda request=None: position),
        goal_position=SimpleNamespace(read=lambda request=None: goal[0], write=write),
        is_moving=moving,
        wait_for_servo=lambda timeout=None: written.append(("waited", timeout)),
    )
    body = stub_factory(
        name="a body",
        dxl=dxl,
        dxl_origin=SimpleNamespace(get=lambda: origin),
    )
    angle = Angle(owner=body, reduction=reduction)
    return angle, written


def test_name_is_angle(stub_factory):
    angle, _written = make_angle(stub_factory)

    assert angle.name == "angle"


def test_at_the_origin_the_angle_is_zero(stub_factory):
    angle, _written = make_angle(stub_factory, origin=1000, position=1000)

    assert angle.get() == 0


def test_the_angle_is_measured_from_the_origin_through_the_reduction(stub_factory):
    # 1000 units past the origin: 29.3 degrees of female, 87.9 of male.
    angle, _written = make_angle(stub_factory, reduction=3, origin=1000, position=2000)
    assert angle.get() == pytest.approx(29.297, abs=0.001)

    angle, _written = make_angle(stub_factory, reduction=1, origin=1000, position=2000)
    assert angle.get() == pytest.approx(87.891, abs=0.001)


def test_below_the_origin_the_angle_is_negative(stub_factory):
    angle, _written = make_angle(stub_factory, reduction=3, origin=1000, position=0)

    assert angle.get() == pytest.approx(-29.297, abs=0.001)


def test_rounded_is_the_whole_degree_the_page_setter_works_in(stub_factory):
    angle, _written = make_angle(stub_factory, reduction=3, origin=1000, position=2000)

    assert angle.rounded() == 29


def test_turn_to_writes_the_origin_plus_the_converted_angle(stub_factory):
    angle, written = make_angle(stub_factory, reduction=3, origin=1000)

    angle.turn_to(20)

    assert written == [1683]


def test_the_same_angle_on_a_direct_body_is_a_different_position(stub_factory):
    angle, written = make_angle(stub_factory, reduction=1, origin=1000)

    angle.turn_to(20)

    assert written == [1228]


def test_turn_to_origin_writes_the_origin_itself(stub_factory):
    angle, written = make_angle(stub_factory, origin=1234)

    angle.turn_to_origin()

    assert written == [1234]


def test_turn_to_below_zero_writes_a_negative_position(stub_factory):
    angle, written = make_angle(stub_factory, reduction=3, origin=100)

    angle.turn_to(-29.297)

    assert written == [-900]


def test_goal_reads_back_in_degrees(stub_factory):
    angle, _written = make_angle(stub_factory, reduction=3, origin=1000)

    angle.turn_to(20)

    assert angle.goal == pytest.approx(20, abs=0.02)


def test_jog_steps_from_the_goal_not_from_the_position(stub_factory):
    # Pressing +1 twice while the body is still on its way must add up to
    # two degrees. Measured from the current position it would add up to
    # one and however far it had got.
    angle, written = make_angle(stub_factory, reduction=3, origin=1000, position=1000)

    angle.jog(1)
    angle.jog(1)

    assert written == [1034, 1068]
    assert angle.goal == pytest.approx(2, abs=0.02)


def test_to_ticks_and_to_degrees_are_inverses(stub_factory):
    angle, _written = make_angle(stub_factory, reduction=3, origin=723)

    for degrees in (0, 5.5, -12.25, 29.297):
        assert angle.to_degrees(angle.to_ticks(degrees)) == pytest.approx(
            degrees, abs=0.02
        )


def test_commit_accepts_the_typed_string_the_ui_hands_over(stub_factory):
    angle, written = make_angle(stub_factory, reduction=3, origin=1000)

    angle.commit("-20")

    assert written == [317]


def test_is_moving_and_wait_delegate_to_the_servo(stub_factory):
    angle, written = make_angle(stub_factory, moving=True)

    assert angle.is_moving is True
    angle.wait(timeout=5)
    assert written == [("waited", 5)]


def test_origin_reads_the_bodys_own_calibration(stub_factory):
    angle, _written = make_angle(stub_factory, origin=4321)

    assert angle.origin == 4321


def test_the_reductions_a_body_can_be_built_with(stub_factory):
    # Guards against a body being wired up with the wrong one, which is
    # invisible until something moves three times too far.
    for kind, reduction in REDUCTIONS.items():
        angle, _written = make_angle(stub_factory, reduction=reduction)
        assert angle.reduction == reduction, kind


def test_the_page_shows_both_the_angle_and_what_the_servo_reads(stub_factory):
    angle, _written = make_angle(stub_factory, reduction=3, origin=1000, position=2000)

    states = angle._snapshot_if_opened(("drivers", "female1", "angle"))

    assert states["angle"]["value"] == "29.3\N{DEGREE SIGN}"
    assert states["servo position"]["value"] == 2000
    assert states["servo origin"]["value"] == 1000
    # Calibration by hand goes coarse then fine, in both directions.
    assert [key for key in states if key.startswith("turn ")] == [
        "turn to origin",
        "turn -10",
        "turn -1",
        "turn +1",
        "turn +10",
    ]


def test_the_jog_commands_on_the_page_actually_move_the_body(stub_factory):
    angle, written = make_angle(stub_factory, reduction=1, origin=0, position=0)

    states = angle._snapshot_if_opened(("drivers", "male1", "angle"))
    states["turn +10"]()

    assert written == [114]
