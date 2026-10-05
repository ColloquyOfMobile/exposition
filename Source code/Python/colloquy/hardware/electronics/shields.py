# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/shields.py

"""The arithmetic behind `shields` (SHIELDS.md), so it can be re-run.

Two kinds of number live in that document and neither should be typed in
by hand. **Facts about the Teensy 4.1** - which pin sits on which timer,
which pins both converters reach, what the timers can actually produce -
were read out of PJRC's own core on 2026-10-03, and a pin table written
against them is only as good as the copy. **The voice cards' filter** -
Thomas's two RC sections, which R and C value a card for a pitch, and how
far the Teensy may move that pitch on it - is a calculation, and a
calculation restated in prose is one that can be wrong without anything
noticing.

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


# --- The voice card: Thomas's filter ---------------------------------------
#
# Two RC sections, R1 = R2 and C1 = C2, the second loading the first:
# H = 1 / (1 + 3sRC + (sRC)^2). Every voice card is this circuit, for the
# Mega and the Teensy alike; only R and C change, and they are the
# through-hole parts on the card.
#
# Thomas's own five are the v2 board's values (R101..C502 in
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


# Where this filter is 3 dB down, as omega * RC: the root of
# x^4 + 7x^2 - 1 = 0, which |H| = 1/sqrt(2) reduces to.
X_3DB: Final = math.sqrt((math.sqrt(53) - 7) / 2)

# Thomas put each tone about three times above its channel's corner (his
# five sit 2.3 to 3.6 times above it). There the fundamental loses about
# 10.5 dB and the third harmonic lands about 22 dB below it.
TONE_OVER_CORNER: Final = 3.0

# A card is valued for one pitch, and the Teensy may move that pitch a
# quarter of an octave either way on it: the level stays within 1.7 dB of
# the card's own and the third harmonic at least 21.1 dB down, which is
# Thomas's own quality (21.0 to 23.1 dB). So cards valued half an octave
# apart cover every pitch from 149 Hz to 13.5 kHz. The test recomputes
# both figures for the cards as built.
CARD_WINDOW_OCTAVES: Final = 0.25
CARD_PITCHES: Final[tuple[float, ...]] = tuple(
    1000.0 * 2 ** (k / 2) for k in range(-5, 8)
)

# The through-hole parts a card is built from: E24 metal-film resistors
# kept between 1 K and 4.7 K (Thomas's own are 1K2 to 2K2, and a higher R
# loses more into the body's 25 K divider), and film capacitors in E6.
E24: Final[tuple[float, ...]] = (
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1,
)
FILM_CAPACITORS: Final[tuple[float, ...]] = (
    10e-9, 15e-9, 22e-9, 33e-9, 47e-9, 68e-9,
    100e-9, 150e-9, 220e-9, 330e-9, 470e-9,
)
RESISTOR_RANGE: Final = (1e3, 4.7e3)
RESISTOR_AIM: Final = 2.2e3


def e24(ohms: float) -> float:
    """The nearest E24 value, compared on a log scale as the series is."""
    decade = 10 ** math.floor(math.log10(ohms))
    candidates = [value * decade for value in E24] + [10 * decade]
    return min(candidates, key=lambda value: abs(math.log(value / ohms)))


def rc_for(hz: float) -> float:
    """The R x C that puts `hz` three times above the corner."""
    return TONE_OVER_CORNER * X_3DB / (2 * math.pi * hz)


def card_values(hz: float) -> tuple[float, float]:
    """R and C for a card valued for `hz`: the film capacitor that lands
    R nearest Thomas's 2K2 within 1 K to 4.7 K, and the E24 resistor to
    go with it."""
    wanted = rc_for(hz)
    best: tuple[float, float, float] | None = None
    for farads in FILM_CAPACITORS:
        ohms = e24(wanted / farads)
        if not RESISTOR_RANGE[0] <= ohms <= RESISTOR_RANGE[1]:
            continue
        score = abs(math.log(ohms / RESISTOR_AIM)) + 5 * abs(math.log(ohms * farads / wanted))
        if best is None or score < best[0]:
            best = (score, ohms, farads)
    if best is None:
        raise ValueError(f"no film capacitor gives {hz} Hz with a resistor in range")
    return best[1], best[2]


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


class Window(NamedTuple):
    """What a card does over the pitches the Teensy may play on it."""

    low: float  # Hz
    high: float  # Hz
    level_swing: float  # dB, the most the fundamental moves from the card's own pitch
    third: float  # dB, the worst third harmonic over the window


def card_window(pitch: float, steps: int = 100) -> Window:
    ohms, farads = card_values(pitch)

    def response(hz: float) -> complex:
        return thomas_response(hz, ohms, farads)

    own = square_through(response, pitch).fundamental
    low = pitch * 2 ** -CARD_WINDOW_OCTAVES
    high = pitch * 2 ** CARD_WINDOW_OCTAVES
    swing, third = 0.0, -math.inf
    for step in range(steps + 1):
        hz = low * (high / low) ** (step / steps)
        found = square_through(response, hz)
        swing = max(swing, abs(found.fundamental - own))
        third = max(third, found.third)
    return Window(low, high, swing, third)


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
# A 5 V square's fundamental is (4/pi) x 5 = 6.37 Vpp before the filter;
# what reaches the line is that, less what the card takes off it.
LOGIC_HIGH: Final = 5.0


def line_level_vpp(gain_db: float) -> float:
    return 4 / math.pi * LOGIC_HIGH * 10 ** (gain_db / 20)
