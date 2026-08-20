# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_subsystem/protocol.py

"""Thomas's audio subsystem tester, as seen down a serial line.

The board is a Mega 2560 of its own - not the installation's Arduino -
running `Source code/Thomas/AudioAnalyzerTest.cpp`. It does two things
this installation has never had: it makes five tones on five hardware
timers, and it hears through five MSGEQ7 analyser modules, one per body.
See CODE_DOCUMENTATION section 9.11, which was written when there was one
analyser and a bare microphone pair.

Everything here is text in and text out, and none of it touches a port:
what a command looks like, what a dump table looks like coming back, and
what counts as the right band lighting up. That keeps the judging - the
part worth being sure about - testable without a board on the bench.

**The one trap in the firmware.** `readSerial()` prints the "> " prompt
and *then* calls `Serial.end()` / `Serial.begin()`, which discards
whatever is already in the input buffer. A command written the instant
the prompt appears can therefore be swallowed. Wait a moment after the
prompt before writing - see PROMPT_SETTLE in __init__.py.
"""
import re

# The board's own serial settings (AudioAnalyzer.h: BAUDRATE).
BAUDRATE = 9600

# What the firmware prints when it wants a command. No newline after it,
# so a reader has to match on the tail of what it has, not on a line.
PROMPT = "> "

# A line from the welcome banner, used to recognise that the thing on the
# other end is this firmware and not something else on the same port.
BANNER = "Audio subsystem tester for"

# The seven MSGEQ7 bands, in the order the firmware prints them
# (showModules()'s header row).
BANDS_HZ = (63, 160, 400, 1000, 2500, 6250, 16000)

# Analyser modules, one per body. AudioAnalyzer.h: NrOfModules = 5,
# connected to the analog inputs from ADCbase = 0 upwards. Which body each
# one belongs to is wiring, not firmware - the bench decides that, so this
# reports by module number.
MODULE_COUNT = 5

# The five tones, by the number the E/D commands take. Note the order: the
# menu counts timers, not frequencies, and timer 2 is the 8-bit one, so
# "E2" is the top tone and not the second one. Reading that off wrong is
# the easiest mistake to make with this board.
#
# Each tone sits in a different analyser band, which is the whole design:
# five bodies, five voices, no two of them competing for one band. Bands
# 63 Hz and 16 kHz are left unused on purpose.
TIMERS = {
    1: {"hz": 160, "pin": "D11", "register": "T1"},
    2: {"hz": 6250, "pin": "D10", "register": "T2"},
    3: {"hz": 400, "pin": "D5", "register": "T3"},
    4: {"hz": 1000, "pin": "D6", "register": "T4"},
    5: {"hz": 2500, "pin": "D46", "register": "T5"},
}

# In the order a sweep should walk them: by pitch, so somebody listening
# hears it climb rather than jump about.
TIMERS_BY_PITCH = (1, 3, 4, 5, 2)

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# "   0\t 12\t 340\t ..." - a module number then its seven band values.
# Anchored on the whole line so the header and the dashed rules cannot
# match, and tolerant of the firmware's mixture of tabs and spaces.
_ROW = re.compile(r"^\s*([0-4])\s+((?:\d+\s+){6}\d+)\s*$")


def strip_ansi(text):
    """The firmware clears the screen with ESC[2J / ESC[H between menus."""
    return _ANSI.sub("", text)


def enable(timer):
    """'E1'..'E5', or 'Ea' for all five at once."""
    return f"E{timer}"


def disable(timer):
    """'D1'..'D5', or 'Da'. 'Da' is what silence means here, and what the
    test leaves the board in when it ends."""
    return f"D{timer}"


def dump(module="a"):
    """'Aa' for every module, 'A0'..'A4' for one.

    It streams tables until it is told to stop, and the only thing that
    stops it is ABORT below. It also *returns* from the command loop when
    it ends, so the firmware redraws its welcome banner afterwards - a
    reader waiting for a bare prompt will find the banner first.
    """
    return f"A{module}"


ABORT = "X"
INFO = "I"

# Every command is a line: the firmware reads until '\n'.
LINE_ENDING = "\n"


def band_index_of(frequency):
    """Which of the seven bands a tone should show up in."""
    return BANDS_HZ.index(frequency)


def expected_band(timer):
    return band_index_of(TIMERS[timer]["hz"])


def parse_tables(text):
    """Every module row in a dump, as {module number: (seven values)}.

    The firmware reprints the header and the dashed rule before every
    sweep, and a sweep of one module prints only that module's row, so
    rows are collected as they come rather than by counting them. A row
    torn in half by a read boundary simply does not match, which is the
    behaviour wanted: a half-read number is worse than a missing one.
    """
    readings = []
    for line in strip_ansi(text).splitlines():
        match = _ROW.match(line)
        if match is None:
            continue
        module = int(match.group(1))
        values = tuple(int(token) for token in match.group(2).split())
        readings.append((module, values))
    return readings


def average_per_module(readings):
    """Mean of each band, per module, over however many sweeps came in."""
    totals = {}
    counts = {}
    for module, values in readings:
        if module not in totals:
            totals[module] = [0] * len(BANDS_HZ)
            counts[module] = 0
        for index, value in enumerate(values):
            totals[module][index] += value
        counts[module] += 1

    return {
        module: tuple(total / counts[module] for total in totals[module])
        for module in totals
    }


def verdict(silence, tone, timer, margin):
    """Did this module hear this tone, and hear it in the right band?

    Three ways it can go, and they mean different things at the bench:

    - "heard": the expected band rose by at least `margin` over silence,
      and rose more than any other band did. Tone and module both good.
    - "wrong band": something rose, but the loudest rise was elsewhere.
      That is a tone at a frequency other than the one the firmware
      claims, or a module wired to the wrong input.
    - "silent": nothing rose. Either the tone is not being generated
      (timer, pin, amp) or the module is not hearing it (microphone,
      routing, or the module itself).
    """
    expected = expected_band(timer)
    rises = [after - before for before, after in zip(silence, tone)]
    best = max(range(len(rises)), key=lambda index: rises[index])

    # "Did anything rise" is asked before "did the right thing rise", and
    # the order matters. Testing the expected band first made a tone
    # coming out at the wrong frequency report as silence, which sends
    # somebody looking at the amp when the fault is in the timer.
    if rises[best] < margin:
        return "silent"
    if best != expected:
        return "wrong band"
    return "heard"
