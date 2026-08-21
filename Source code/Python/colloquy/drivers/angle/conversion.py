# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/angle/conversion.py

"""Ticks to degrees and back - the only place the two meet.

Everything that moves in this installation is a Dynamixel commanded in
position units ("ticks"), but nobody thinks in ticks: what is worth
saying is how far the *body* turned, in degrees. Two things stand between
the two numbers, and both live here.

**The servo's own resolution.** These are X-series servos, 4096 units to
a turn, so one servo degree is 11.378 units.

**The reduction.** A female, a male and the bar all turn three times
slower than their servo; only a mirror turns with its own. So the same
2000 ticks is 58.6 degrees of any of the bodies and 175.8 of a mirror -
which is exactly the confusion this module exists to end. Every
conversion here is in degrees of the thing that actually moves, never of
the servo.

Sign, too: `init_hardware()` puts every servo in extended position mode
(operating mode 4), where positions on either side of zero are normal and
the wire format is two's complement. The SDK writes that correctly and
reads it back as an unsigned dword, so a position of -900 comes back as
4294966396 unless something converts it - `as_signed` is that something.
"""

# X-series: 4096 position units to one turn of the servo shaft.
TICKS_PER_TURN = 4096
DEGREES_PER_TURN = 360

# How many times slower the body turns than its servo. Measured on the
# rig, not derived: a female, a male and the bar all have a 1:3 reduction
# after the servo output; a mirror is direct. The male's stood at 1 here
# for a while, which is a fact about the rig this file had wrong - every
# male angle it produced was three times the truth, and the params
# migration to v3 is that error being taken back out of the calibration.
REDUCTIONS = {
    "female": 3,
    "male": 3,
    "bar": 3,
    "mirror": 1,
}

# Positions are 4-byte registers; the SDK hands them over unsigned.
_DWORD = 1 << 32
_DWORD_SIGN_BIT = 1 << 31


def ticks_per_degree(reduction):
    """Servo units for one degree of the body: 11.378 direct, 34.133 at 1:3."""
    return TICKS_PER_TURN * reduction / DEGREES_PER_TURN


def ticks_to_degrees(ticks, reduction):
    """Servo units to degrees of the body. Exact - no rounding, since the
    caller may be about to subtract two of these."""
    return ticks / ticks_per_degree(reduction)


def degrees_to_ticks(degrees, reduction):
    """Degrees of the body to whole servo units.

    Rounded, because a register takes integers: the error is at most half
    a unit, which is 0.044 degrees direct and 0.015 at 1:3 - a tenth of
    what the servo itself can resolve, and far below anything visible in
    the room.
    """
    return round(degrees * ticks_per_degree(reduction))


def as_signed(raw):
    """A position register read back as an unsigned dword, as the number it
    was written as.

    Above extended position mode's own limits this is meaningless anyway,
    so anything at or past the sign bit is read as negative - which is
    what the servo means by it.
    """
    if raw >= _DWORD_SIGN_BIT:
        return raw - _DWORD
    return raw


def as_unsigned(value):
    """The inverse: what the wire carries for a possibly-negative position.

    Only the simulator needs this - the real SDK's write path already
    does it, and its read path is what `as_signed` undoes.
    """
    return value % _DWORD
