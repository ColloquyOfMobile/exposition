# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/microphone_board.py

"""The arithmetic behind `microphone board` (MICROPHONE_BOARD.md).

Every figure the document quotes about the board's circuit and its fixing
to the extrusion is computed here, and
`pytest_tests/hardware/test_microphone_board.py` holds the document to it.
The part values are the MAX9814 datasheet's own typical application
(Maxim, "Typical Application Circuit/Functional Diagram" and
"Applications Information"); the screw stack is ISO dimensions.

Pure functions over ordinary values, on mypy's `files`: ohms, farads,
volts and millimetres all read as small floats.
"""

import math
from typing import Final

# --- The MAX9814 and the parts round it ------------------------------------

MICBIAS: Final = 2.0  # V, the chip's microphone bias output
OUTPUT_BIAS: Final = 1.23  # V, MICOUT at rest
INPUT_RESISTANCE: Final = 100e3  # ohms, MICIN, datasheet
SUPPLY_CURRENT: Final = 3.1e-3  # A, typical

THRESHOLD_TOP: Final = 150e3  # ohms, MICBIAS to TH
THRESHOLD_BOTTOM: Final = 100e3  # ohms, TH to GND
INPUT_CAPACITOR: Final = 100e-9  # farads, capsule to MICIN, C0G
TIMING_CAPACITOR: Final = 470e-9  # farads, CT
SUPPLY_RESISTOR: Final = 33.0  # ohms, harness 5 V to the chip's VDD
SUPPLY_CAPACITOR: Final = 22e-6  # farads, at VDD
BUILD_OUT: Final = 470.0  # ohms, MICOUT to the connector
CABLE_CAPACITANCE: Final = 1e-9  # farads, a long body cable, for the check


def threshold_volts() -> float:
    """VTH, the divider off MICBIAS."""
    return MICBIAS * THRESHOLD_BOTTOM / (THRESHOLD_TOP + THRESHOLD_BOTTOM)


def held_swing() -> float:
    """The datasheet: the AGC limits the output to two times VTH, peak to
    peak."""
    return 2 * threshold_volts()


def held_window() -> tuple[float, float]:
    half = held_swing() / 2
    return OUTPUT_BIAS - half, OUTPUT_BIAS + half


def corner(ohms: float, farads: float) -> float:
    return 1 / (2 * math.pi * ohms * farads)


def input_corner() -> float:
    """The input capacitor against MICIN's 100 K: the low end of what the
    board hears."""
    return corner(INPUT_RESISTANCE, INPUT_CAPACITOR)


def supply_corner() -> float:
    """The supply filter against the NeoPixel-loaded harness 5 V."""
    return corner(SUPPLY_RESISTOR, SUPPLY_CAPACITOR)


def supply_drop() -> float:
    return SUPPLY_RESISTOR * SUPPLY_CURRENT


def build_out_corner() -> float:
    """The build-out against a long cable: far above anything audible."""
    return corner(BUILD_OUT, CABLE_CAPACITANCE)


def attack_seconds() -> float:
    """Datasheet: the attack time constant is 2400 x CCT."""
    return 2400 * TIMING_CAPACITOR


# --- The fixing to the extrusion -------------------------------------------
#
# M5 because the board then fits any profile: M5 T-nuts are made for 6, 8
# and 10 mm slots, so the slot decides only which nut to buy.
SCREW_LENGTH: Final = 12.0  # mm, ISO 7380 M5 x 12, under the head
WASHER: Final = 1.0  # mm, ISO 7089 M5
BOARD: Final = 1.6  # mm
SPACER: Final = 5.0  # mm, nylon
NUT_THREAD: Final = 4.0  # mm, a typical slot-6 M5 T-nut


def thread_left_for_the_nut() -> float:
    """How much screw is left below the spacer to engage the T-nut."""
    return SCREW_LENGTH - (WASHER + BOARD + SPACER)
