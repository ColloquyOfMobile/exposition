# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/shields.py

"""The arithmetic behind `shields` (SHIELDS.md), so it can be re-run.

Two kinds of number live in that document and neither should be typed in
by hand. **Facts about the Teensy 4.1** - which pin sits on which timer,
which pins both converters reach, what the timers can actually produce -
were read out of PJRC's own core on 2026-10-03, and a pin table written
against them is only as good as the copy. **The voice cards' filter** -
which resistor gives which corner, and over which pitches a card is
cleaner than Thomas's channel - is a calculation, and a calculation
restated in prose is one that can be wrong without anything noticing.

So both are here, and `pytest_tests/hardware/test_shields.py` holds the
document's tables to this module and this module to the v2 contract.

Pure functions over ordinary values, on mypy's `files`: a corner in
hertz, a resistance in ohms and a capacitance in farads are three floats
that read alike, and the whole of this module is keeping them apart.
"""

import math
from collections.abc import Callable
from typing import Final, NamedTuple

# --- Teensy 4.1, out of PJRC's core ---------------------------------------
#
# `cores/teensy4/pwm.c`, `pwm_pin_info[]`, pins 0 to 33. The timer *unit*
# is what matters: `analogWriteFrequency()` sets the frequency of a whole
# FlexPWM submodule or QuadTimer channel (`flexpwmFrequency()` and
# `quadtimerFrequency()` take the submodule and ignore the channel), so
# two pins on one unit always play one pitch. Five voices need five units.
TEENSY41_TIMER: Final[dict[int, str]] = {
    0: "FlexPWM1.1",
    1: "FlexPWM1.0",
    2: "FlexPWM4.2",
    3: "FlexPWM4.2",
    4: "FlexPWM2.0",
    5: "FlexPWM2.1",
    6: "FlexPWM2.2",
    7: "FlexPWM1.3",
    8: "FlexPWM1.3",
    9: "FlexPWM2.2",
    10: "QuadTimer1.0",
    11: "QuadTimer1.2",
    12: "QuadTimer1.1",
    13: "QuadTimer2.0",
    14: "QuadTimer3.2",
    15: "QuadTimer3.3",
    18: "QuadTimer3.1",
    19: "QuadTimer3.0",
    22: "FlexPWM4.0",
    23: "FlexPWM4.1",
    24: "FlexPWM1.2",
    25: "FlexPWM1.3",
    28: "FlexPWM3.1",
    29: "FlexPWM3.1",
    33: "FlexPWM2.0",
}

# `cores/teensy4/analog.c`, `pin_to_channel[]`, and the ADC library's
# `channel2sc1aADC0/1[]`. Pins 14-23 reach both converters, so two of
# them can be converted at the same instant; the others reach one. The
# core calls the converters ADC1 and ADC2; the ADC library calls them
# adc0 and adc1. Pins 40 and 41 are read on ADC1 by the core, and the
# library's table stops at 27, so they are listed on the one converter
# the core is known to use.
TEENSY41_ANALOG: Final[dict[int, frozenset[str]]] = {
    **{pin: frozenset({"ADC1", "ADC2"}) for pin in range(14, 24)},
    24: frozenset({"ADC1"}),
    25: frozenset({"ADC1"}),
    26: frozenset({"ADC2"}),
    27: frozenset({"ADC2"}),
    38: frozenset({"ADC2"}),
    39: frozenset({"ADC2"}),
    40: frozenset({"ADC1"}),
    41: frozenset({"ADC1"}),
}

# The LED pin. The bootloader blinks it, so nothing that reaches the
# piece may hang off it (`next pcb` section 1's reason for D13).
TEENSY41_LED: Final = 13

# `cores/teensy4/clockspeed.c`: the IPG divider is chosen for at most
# 150 MHz, so at the default 600 MHz F_BUS_ACTUAL is 150 MHz. Every
# FlexPWM and QuadTimer counts this clock.
TEENSY41_F_BUS: Final = 150_000_000


def teensy_pwm_frequency(hz: float, pin: int) -> float:
    """What a Teensy 4.1 actually plays when asked for `hz` on `pin`.

    The same steps as `flexpwmFrequency()` / `quadtimerFrequency()`:
    round the divider, halve it (doubling the prescaler) until it fits in
    sixteen bits, then clamp. The halving truncates, which is the whole
    of the error - a fraction of a count in tens of thousands.
    """
    limit = 65534 if TEENSY41_TIMER[pin].startswith("QuadTimer") else 65535
    divider = int(TEENSY41_F_BUS / hz + 0.5)
    prescale = 0
    while divider > limit and prescale < 7:
        divider >>= 1
        prescale += 1
    divider = max(2, min(divider, limit))
    return TEENSY41_F_BUS / (1 << prescale) / divider


# --- Thomas's channel, the baseline ----------------------------------------
#
# Two RC sections, R1 = R2 and C1 = C2, the second loading the first:
# H = 1 / (1 + 3sRC + (sRC)^2). Values are the v2 board's (R101..C502 in
# `circuit.json`), body order. The pitch each plays is what his trimmed
# OCR values come out at (the sketch's own comment), not the round name.
THOMAS_CHANNELS: Final[dict[str, tuple[float, float]]] = {
    "female1": (1.2e3, 150e-9),
    "female2": (1.8e3, 47e-9),
    "female3": (2.2e3, 10e-9),
    "male1": (2.2e3, 470e-9),
    "male2": (2.0e3, 220e-9),
}
MEGA_PITCHES: Final[dict[str, float]] = {
    "female1": 1012.0,
    "female2": 2531.0,
    "female3": 6329.0,
    "male1": 162.0,
    "male2": 405.0,
}


def thomas_response(hz: float, ohms: float, farads: float) -> complex:
    s = 2j * math.pi * hz
    t = ohms * farads
    return 1 / (1 + 3 * s * t + (s * t) ** 2)


# --- The active voice card -------------------------------------------------
#
# Fourth-order Butterworth, two unity-gain Sallen-Key stages with equal
# resistors. With equal R a stage's Q is set by its capacitor ratio alone,
# Q = sqrt(C1/C2) / 2 (C1 the feedback capacitor, C2 the one to ground),
# so a card's *shape* is fixed by four capacitors that never change and
# its *corner* by four resistors that are the whole of a card variant.
# Butterworth wants Q = 0.541 and 1.307; E12 C0G values give 0.548 and
# 1.291, which moves nothing that matters (see the test).
STAGE_CAPACITORS: Final[tuple[tuple[float, float], ...]] = (
    (12e-9, 10e-9),
    (22e-9, 3.3e-9),
)

# A card is named by its corner, on a half-octave grid through 1 kHz.
# Half an octave is what makes the sweet windows below tile: 0.6 x sqrt 2
# is 0.849, just under 0.85, so every pitch from 106 Hz to 9.6 kHz lies
# in some card's sweet window (in a sliver of 0.2 % at each join, in two).
CARD_CORNERS: Final[tuple[float, ...]] = tuple(
    1000.0 * 2 ** (k / 2) for k in range(-5, 8)
)

# Where a pitch may sit, as a fraction of the card's corner.
#
# SWEET: what a card is *chosen* by. Within it the fundamental loses at
# most 1.1 dB and the third harmonic is at least 29.7 dB down - better
# than every Thomas channel at its own pitch (21-23 dB).
#
# ALLOWED: what the firmware will play on a fitted card without asking
# for another one. One octave; the fundamental loses at most 3.1 dB at
# the top and the third harmonic is still at least 23.6 dB down, which is
# no worse than Thomas's chain.
#
# All four figures are for the cards as built (E96 resistors, E12
# capacitors), and the test recomputes them.
SWEET: Final = (0.60, 0.85)
ALLOWED: Final = (0.50, 1.00)

# The E96 decade, for the resistors that make a card.
E96: Final[tuple[float, ...]] = (
    1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30,
    1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62, 1.65, 1.69, 1.74,
    1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15, 2.21, 2.26, 2.32,
    2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09,
    3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
    4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49,
    5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32,
    7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76,
)


def e96(ohms: float) -> float:
    """The nearest E96 value, compared on a log scale as the series is."""
    decade = 10 ** math.floor(math.log10(ohms))
    candidates = [value * decade for value in E96] + [10 * decade]
    return min(candidates, key=lambda value: abs(math.log(value / ohms)))


def stage_q(capacitors: tuple[float, float]) -> float:
    feedback, to_ground = capacitors
    return math.sqrt(feedback / to_ground) / 2


def stage_resistor(corner_hz: float, capacitors: tuple[float, float]) -> float:
    """The exact equal-R value that puts this stage's natural frequency
    on the card's corner."""
    feedback, to_ground = capacitors
    return 1 / (2 * math.pi * corner_hz * math.sqrt(feedback * to_ground))


def card_resistors(corner_hz: float) -> tuple[float, ...]:
    """The E96 resistors of a card, one value per stage (two of each)."""
    return tuple(
        e96(stage_resistor(corner_hz, capacitors))
        for capacitors in STAGE_CAPACITORS
    )


def card_response(
    hz: float, corner_hz: float, resistors: tuple[float, ...] | None = None
) -> complex:
    """The card's transfer at `hz`. With `resistors` given it is the card
    as built, E96 rounding and all; without, the ideal corner."""
    if resistors is None:
        resistors = tuple(
            stage_resistor(corner_hz, capacitors) for capacitors in STAGE_CAPACITORS
        )
    s = 2j * math.pi * hz
    response: complex = 1
    for ohms, (feedback, to_ground) in zip(resistors, STAGE_CAPACITORS):
        response /= 1 + 2 * s * ohms * to_ground + (s * ohms) ** 2 * feedback * to_ground
    return response


def db(value: complex | float) -> float:
    return 20 * math.log10(abs(value))


class Harmonics(NamedTuple):
    """A square wave through a filter: what the fundamental loses, and
    how far below it the third and fifth land, all in dB."""

    fundamental: float
    third: float
    fifth: float


def square_through(response: Callable[[float], complex], hz: float) -> Harmonics:
    """A square wave's odd harmonics are 1/3, 1/5 of its fundamental
    before any filter; `response(f)` is the filter."""
    first = response(hz)
    return Harmonics(
        fundamental=db(first),
        third=db(response(3 * hz) / 3) - db(first),
        fifth=db(response(5 * hz) / 5) - db(first),
    )


def card_for(hz: float) -> float:
    """The corner of the card whose sweet window holds this pitch."""
    for corner in CARD_CORNERS:
        if SWEET[0] * corner <= hz < SWEET[1] * corner:
            return corner
    raise ValueError(f"{hz} Hz is outside every card's sweet window")


# --- The analogue inputs ---------------------------------------------------
#
# The microphone, out of the MAX9814 datasheet's electrical
# characteristics (Maxim; characterised at a 3.3 V supply). This
# repository measured the same part on the body's 5 V at 1.21 V of bias
# and about 1.44 Vpp in a quiet room (`scope > diagnosing a microphone`),
# which is the datasheet's bias and its 1.40 Vpp regulated level.
MAX9814_BIAS: Final = 1.23  # V, MICOUT unconnected
MAX9814_MOST_VPP: Final = 2.0  # V peak to peak, maximum output at 1 % THD
MAX9814_HIGHEST: Final = 2.45  # V, MICOUT high output, sourcing 1 mA

# Its path to the Teensy: 4.7 K on the backplane, 1 M to AGND after it,
# 1 nF at the pin on the adapter.
MIC_SERIES: Final = 4.7e3  # ohms
MIC_RESERVOIR: Final = 1e-9  # farads

# `analogReference()` is empty on a Teensy 4: the converter reads against
# its own 3.3 V and nothing else.
TEENSY41_REFERENCE: Final = 3.3  # V
TEENSY41_COUNTS: Final = 4096

# A photosensor is a 3-pin module on the body's 5 V; 5.25 V is the top of
# a USB-class 5 V rail. The adapter divides it 100 K over 150 K.
PHOTOSENSOR_HIGHEST: Final = 5.25  # V
PHOTOSENSOR_DIVIDER: Final = 150e3 / (100e3 + 150e3)


def microphone_window() -> tuple[float, float]:
    """The lowest and highest a microphone's output reaches at its most."""
    half = MAX9814_MOST_VPP / 2
    return MAX9814_BIAS - half, MAX9814_BIAS + half


def span_used(low: float, high: float, reference: float) -> float:
    """The fraction of a converter's range a signal from low to high
    occupies."""
    return (high - low) / reference


def microphone_corner() -> float:
    """The 4.7 K and the 1 nF at the pin, as a low-pass, in hertz."""
    return 1 / (2 * math.pi * MIC_SERIES * MIC_RESERVOIR)


# --- Level -----------------------------------------------------------------
#
# The card divides the 5 V square to 2.0 Vpp around its own mid-rail
# before filtering, so the passband fundamental is (4/pi) x 2.0 = 2.55 Vpp:
# `next pcb` section 3's line level, which the body's 22K/3K3 divider was
# sized for. 15K from the voice line, 10K to the reference.
LOGIC_HIGH: Final = 5.0
DIVIDER_TOP: Final = 15e3
DIVIDER_BOTTOM: Final = 10e3


def line_level_vpp(gain_db: float = 0.0) -> float:
    square = LOGIC_HIGH * DIVIDER_BOTTOM / (DIVIDER_TOP + DIVIDER_BOTTOM)
    return 4 / math.pi * square * 10 ** (gain_db / 20)

