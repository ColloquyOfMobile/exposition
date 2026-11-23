# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_teensy/checks.py

"""What each answer from `teensy_check` says about the Teensy. Pure.

Each judge returns a `Check`: a name, whether it passed, and the sentence
for the page. Split from the node so every verdict can be tested without a
port, the way `test_audio_bringup/diagnosis.py` is.

**What these can and cannot settle.** A Teensy that answers `?` has a
working USB link, a running processor and this sketch on it. The echo says
the link carries bytes without losing or corrupting them. The two uptimes
say the board's clock keeps time with this computer's. The temperature is
the die's own sensor, and only judged as plausible: a hard limit would
need a source for it, and none is cited here. What none of them can see is
the LED - that is the one thing a person checks, which is why this is a
manual test.
"""
from typing import NamedTuple

# Round trips in the echo check. Each is ~1 ms over USB, so a run is
# well under a second.
ECHO_ROUNDS = 100

# How far the board's clock may disagree with this computer's over the
# run. Each uptime is read through a USB reply, so the two readings carry
# a millisecond or two of latency each; a crystal off by more than this
# would be a broken one, not a slow reply.
CLOCK_SLACK_MS = 20.0
CLOCK_SLACK_SHARE = 0.02

# Outside this the die sensor is not reading a temperature at all.
PLAUSIBLE_C = (-20.0, 110.0)


class Check(NamedTuple):
    name: str
    passed: bool
    said: str


def answers(fields, expected_version, expected_board):
    """Did `?` get this sketch's status line, and the version in the repo?"""
    if fields is None:
        return Check(
            "answers",
            False,
            "no teensy_check status line came back - the board is running "
            "something else, or nothing. Press 'flash firmware'.",
        )
    version = fields.get("firmware")
    board = fields.get("board")
    if version != str(expected_version):
        return Check(
            "answers",
            False,
            f"teensy_check firmware {version}, but the sketch here is "
            f"firmware {expected_version} - flash it again",
        )
    if board != expected_board:
        return Check("answers", False, f"the sketch says board={board}, not {expected_board}")
    return Check("answers", True, f"teensy_check firmware {version} on a {board}")


def clock_speed(f_cpu):
    """What the processor says it is running at. 600 MHz is the default."""
    if f_cpu is None or f_cpu <= 0:
        return Check("cpu clock", False, "the board did not say its clock speed")
    mhz = f_cpu / 1e6
    if round(mhz) == 600:
        return Check("cpu clock", True, f"{mhz:.0f} MHz, the Teensy 4.1 default")
    return Check(
        "cpu clock",
        True,
        f"{mhz:.0f} MHz - not the 600 MHz default; somebody changed "
        "Tools > CPU Speed. Not a fault",
    )


def temperature(celsius):
    low, high = PLAUSIBLE_C
    if celsius is None:
        return Check("die temperature", False, "the board did not say its temperature")
    if not low <= celsius <= high:
        return Check(
            "die temperature",
            False,
            f"{celsius:.1f} °C - not a plausible reading; the on-chip sensor "
            "is not working",
        )
    return Check(
        "die temperature",
        True,
        f"{celsius:.1f} °C (the processor's own sensor; warm to the touch "
        "is normal at 600 MHz)",
    )


def echo(sent, good, round_trips_ms):
    """`sent` lines, `good` of them came back exactly; times in ms."""
    if sent == 0:
        return Check("usb echo", False, "nothing was sent")
    if good < sent:
        return Check(
            "usb echo",
            False,
            f"{good} of {sent} lines came back intact - the USB link loses "
            "or corrupts data. Try another lead or another USB port",
        )
    mean = sum(round_trips_ms) / len(round_trips_ms)
    return Check(
        "usb echo",
        True,
        f"{sent} of {sent} lines came back intact, {mean:.2f} ms mean and "
        f"{max(round_trips_ms):.2f} ms worst round trip",
    )


def clock_keeps_time(board_ms, host_ms):
    """The board's uptime advanced by `board_ms` while this computer's
    clock advanced by `host_ms`."""
    if board_ms is None or host_ms is None:
        return Check("clock keeps time", False, "two uptimes were not both read")
    slack = CLOCK_SLACK_MS + CLOCK_SLACK_SHARE * host_ms
    off = board_ms - host_ms
    said = (
        f"the board counted {board_ms:.0f} ms while this computer counted "
        f"{host_ms:.0f} ms"
    )
    if abs(off) > slack:
        return Check("clock keeps time", False, f"{said} - its clock is wrong")
    return Check("clock keeps time", True, said)


def overall(checks):
    """One line over all of them, and the person's half named."""
    failed = [check.name for check in checks if not check.passed]
    if failed:
        return "FAILED: " + ", ".join(failed)
    return (
        "the board passed every check it can make on itself - now look at "
        "the LED (below) and say what you saw"
    )
