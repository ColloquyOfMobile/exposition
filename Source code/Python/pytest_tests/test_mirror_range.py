# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_mirror_range.py

"""How far a mirror can turn, and where the number came from.

It sat at 0.0 - "stays where it is" - with a comment saying nobody had
measured it. Nobody had to: TJ's OpenCM servo controller drove these
mirrors, and all ten deployed versions of his female sketch carry the
same limits. What could not come from him is the *origin*, which is a
fact about this installation's mechanism rather than about the mirror.

Pinned here because the two numbers are arrived at differently and the
difference is easy to lose: one is arithmetic on his constants, the other
is somebody at the rig with the torque off.
"""
from colloquy.drivers.angle.conversion import REDUCTIONS, ticks_to_degrees
from colloquy.params import DEFAULTS

# `goal_position_mirror_MAX/MIN` and `GOAL_POSITION_OVERRUN`, verbatim.
TJ_CENTRE = 1023
TJ_HALF_SPAN = 512
TJ_OVERRUN = 50

MIRRORS = ("mirror1", "mirror2", "mirror3")


def test_his_scale_is_our_scale():
    """His comment on the line is `//512==45`. If that ever stops being
    true of `ticks_to_degrees`, the range below is wrong by the ratio."""
    assert ticks_to_degrees(TJ_HALF_SPAN, 1) == 45.0


def test_a_mirror_turns_with_its_own_servo():
    """Everything else on the piece is geared 1:3; a mirror is not, and
    the range depends on it."""
    assert REDUCTIONS["mirror"] == 1


def test_the_range_is_his_two_constants():
    high = (TJ_CENTRE + TJ_HALF_SPAN) - TJ_OVERRUN
    low = (TJ_CENTRE - TJ_HALF_SPAN) + TJ_OVERRUN
    expected = round(ticks_to_degrees(high - low, REDUCTIONS["mirror"]), 3)

    assert expected == 81.211
    for name in MIRRORS:
        assert DEFAULTS[name]["motion range"] == expected, name


def test_every_mirror_gets_the_same_range():
    """His limits never varied by female and never changed across ten
    versions of the sketch."""
    ranges = {DEFAULTS[name]["motion range"] for name in MIRRORS}

    assert len(ranges) == 1


def test_the_origin_is_still_nobody_else_s():
    """His centre is 1023 because that is where his servo sat in his
    mechanism. `dxl origin` here is the reading a mirror gives when it
    points where it should, and that is measured at the rig."""
    for name in MIRRORS:
        assert DEFAULTS[name]["dxl origin"] == 0, name


# --- and getting it onto an installation that already has a file ---------


def migrated(**mirror_overrides):
    """A v4 file put through the migration."""
    from colloquy.params import migrate

    data = {
        "params version": 4,
        "mirror1": {"dxl origin": 0, "motion range": 0.0},
        "mirror2": {"dxl origin": 0, "motion range": 0.0},
        "mirror3": {"dxl origin": 0, "motion range": 0.0},
    }
    for name, mirror in mirror_overrides.items():
        data[name] = mirror
    return migrate(data)


def test_an_unmeasured_range_becomes_his():
    """`_fill_missing` only adds keys a file predates, so a file that
    already says 0.0 would never have seen the new default - which is
    every installation, since they all have one."""
    data = migrated()

    for name in MIRRORS:
        assert data[name]["motion range"] == 81.211, name


def test_a_range_somebody_measured_is_left_alone():
    """It is a fact about this installation and outranks a number read
    off somebody else's firmware - the same rule v4 applied to a
    deliberately-typed baud rate."""
    data = migrated(mirror2={"dxl origin": 0, "motion range": 62.5})

    assert data["mirror2"]["motion range"] == 62.5
    assert data["mirror1"]["motion range"] == 81.211


def test_the_origins_are_not_touched():
    """His centre is 1023 because that is where his servo sat in his
    mechanism. Ours is still a person at the rig."""
    data = migrated(mirror3={"dxl origin": 2048, "motion range": 0.0})

    assert data["mirror3"]["dxl origin"] == 2048
    assert data["mirror3"]["motion range"] == 81.211


def test_the_file_says_it_has_been_migrated():
    from colloquy.params import PARAMS_VERSION

    assert migrated()["params version"] == PARAMS_VERSION == 5


def test_migrating_twice_changes_nothing_more():
    from colloquy.params import migrate

    once = migrated()
    twice = migrate(dict(once))

    assert twice == once
