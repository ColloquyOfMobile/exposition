"""Unit tests for colloquy.hardware.angle.conversion.

Pure arithmetic, no objects at all: the module is functions and constants
only, so these are called directly.

The numbers being pinned are the two facts everything else in the angle
layer rests on - 4096 servo units to a turn, and a 1:3 reduction on a
female and on the bar against 1:1 on a male and a mirror. One degree of
body is therefore 11.378 units direct and 34.133 units through the
reduction, and the same 2000-unit sweep is 175.8 degrees of male but only
58.6 degrees of female. Getting that backwards is the whole reason the
module exists, so it is asserted from both directions.
"""
import pytest

from colloquy.hardware.angle.conversion import (
    DEGREES_PER_TURN,
    REDUCTIONS,
    TICKS_PER_TURN,
    as_signed,
    as_unsigned,
    degrees_to_ticks,
    ticks_per_degree,
    ticks_to_degrees,
)


# --- the constants themselves --------------------------------------------


def test_a_turn_is_4096_units():
    # X-series resolution; VirtualDXL's speed model assumes the same
    # number (virtual_hardware/virtual_dxl.py).
    assert TICKS_PER_TURN == 4096
    assert DEGREES_PER_TURN == 360


def test_reductions_are_three_for_the_geared_pair_and_one_for_the_rest():
    assert REDUCTIONS == {"female": 3, "male": 1, "bar": 3, "mirror": 1}


def test_ticks_per_degree():
    assert ticks_per_degree(1) == pytest.approx(11.3778, abs=0.0001)
    assert ticks_per_degree(3) == pytest.approx(34.1333, abs=0.0001)


# --- ticks -> degrees ----------------------------------------------------


def test_a_full_servo_turn_is_360_degrees_direct_and_120_geared():
    assert ticks_to_degrees(4096, 1) == 360
    # Three servo turns to one turn of the body.
    assert ticks_to_degrees(4096, 3) == 120
    assert ticks_to_degrees(3 * 4096, 3) == 360


def test_todays_sweeps_in_degrees():
    # The same 2000 units both bodies are given today, which is the
    # asymmetry this layer makes visible: a male sweeps three times as far
    # as a female for the same number written to the servo.
    assert ticks_to_degrees(2000, REDUCTIONS["male"]) == pytest.approx(175.781, abs=0.001)
    assert ticks_to_degrees(2000, REDUCTIONS["female"]) == pytest.approx(58.594, abs=0.001)
    # The bar's full travel, and the window the simulator calls "facing
    # forward" (400 units, which is a much wider angle for a male).
    assert ticks_to_degrees(10000, REDUCTIONS["bar"]) == pytest.approx(292.969, abs=0.001)
    assert ticks_to_degrees(400, REDUCTIONS["female"]) == pytest.approx(11.719, abs=0.001)
    assert ticks_to_degrees(400, REDUCTIONS["male"]) == pytest.approx(35.156, abs=0.001)


def test_negative_ticks_are_negative_degrees():
    assert ticks_to_degrees(-1024, 1) == -90


def test_ticks_to_degrees_does_not_round():
    # Callers subtract two of these (a position and an origin) before
    # showing anything, so rounding here would be rounding twice.
    assert ticks_to_degrees(1, 1) == pytest.approx(0.087890625)
    assert ticks_to_degrees(1, 3) == pytest.approx(0.029296875)


# --- degrees -> ticks ----------------------------------------------------


def test_degrees_to_ticks_rounds_to_whole_units():
    # A register takes integers.
    assert degrees_to_ticks(20, 3) == 683  # 682.67
    assert degrees_to_ticks(20, 1) == 228  # 227.56
    assert isinstance(degrees_to_ticks(20, 3), int)


def test_degrees_to_ticks_of_the_sweeps():
    assert degrees_to_ticks(87.891, 1) == 1000
    assert degrees_to_ticks(29.297, 3) == 1000
    assert degrees_to_ticks(292.969, 3) == 10000


def test_degrees_to_ticks_handles_the_negative_half():
    assert degrees_to_ticks(-29.297, 3) == -1000
    assert degrees_to_ticks(-90, 1) == -1024


def test_round_trip_stays_within_half_a_unit():
    # Half a unit is 0.044 degrees direct and 0.015 geared - below what
    # the servo itself resolves, so a value that goes out and comes back
    # is the same angle for any purpose in this installation.
    for reduction in (1, 3):
        for degrees in (0, 0.5, 12.3, -12.3, 87.891, -29.297, 292.969):
            back = ticks_to_degrees(degrees_to_ticks(degrees, reduction), reduction)
            assert back == pytest.approx(degrees, abs=0.05)


# --- sign ----------------------------------------------------------------


def test_as_signed_leaves_ordinary_positions_alone():
    assert as_signed(0) == 0
    assert as_signed(2000) == 2000


def test_as_signed_reads_the_two_complement_the_servo_sends_back():
    # The one that bites: female1's origin is 100 and half its sweep is
    # 1000, so turning to its minimum writes -900. The SDK writes that
    # correctly and reads it back as an unsigned dword.
    assert as_signed(4294966396) == -900
    assert as_signed(4294967295) == -1


def test_as_unsigned_is_the_inverse():
    for value in (0, 1, 2000, -1, -900, -100000):
        assert as_signed(as_unsigned(value)) == value


def test_as_unsigned_of_a_positive_value_changes_nothing():
    assert as_unsigned(2000) == 2000
