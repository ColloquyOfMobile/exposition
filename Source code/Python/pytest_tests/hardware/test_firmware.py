# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_firmware.py

"""What is on the Arduino, and whether this driver can talk to it -
colloquy/hardware/arduino/firmware.py.

The two numbers checked here are the ones that go wrong on their own,
because each of them is written in two places that get edited on two
different occasions: the baud rate (params.json and the sketch) and the
protocol version (the sketch and whatever is actually flashed). Neither
mismatch announces itself on the wire - a wrong baud rate produces
rubbish, an old firmware answers unknown paths with an empty line - so
these tests pin the *messages*, not just the booleans.
"""
import json

import pytest

from colloquy.hardware.arduino import firmware


def test_the_sketchs_numbers_are_read_out_of_the_sketch():
    # Not copied into Python. The .ino is the file that gets flashed, so
    # it is the only one that can be believed.
    assert firmware.SKETCH_PATH.exists()
    assert firmware.sketch_baudrate() == 1000000
    assert firmware.sketch_firmware_version() >= firmware.MINIMUM_FIRMWARE_VERSION


def test_a_define_with_a_type_suffix_is_still_a_number():
    # Serial.begin() takes an unsigned long and the sketch says so:
    # `#define SERIAL_BAUDRATE 1000000UL`.
    assert isinstance(firmware.sketch_baudrate(), int)


def test_the_sketch_greeting_is_what_the_sketch_would_send():
    assert firmware.sketch_greeting() == {
        "hello": "colloquy of mobiles",
        "firmware": firmware.sketch_firmware_version(),
        "baudrate": firmware.sketch_baudrate(),
    }


def test_parse_greeting_reads_a_board_line():
    line = json.dumps({"hello": "colloquy of mobiles", "firmware": 2, "baudrate": 1000000})

    assert firmware.parse_greeting(line.encode() + b"\r\n") == {
        "hello": "colloquy of mobiles",
        "firmware": 2,
        "baudrate": 1000000,
    }


def test_parse_greeting_recognises_the_old_bare_hello():
    # v1 said "Hello!" and nothing else. Recognising it turns "no
    # response" into "firmware 1, flash it", which is a far better thing
    # to read while standing at the rig.
    assert firmware.parse_greeting(b"Hello!\r\n") == firmware.LEGACY_GREETING


@pytest.mark.parametrize(
    "line",
    [
        b"",
        b"\r\n",
        # What a wrong baud rate actually puts on the wire.
        bytes([0xF8, 0x00, 0x9C, 0xFF]),
        b"245",  # a light sensor reading, arriving where a greeting should
        b'{"status": "ok"}',  # JSON, but nothing that says which firmware
    ],
)
def test_parse_greeting_refuses_anything_that_is_not_one(line):
    assert firmware.parse_greeting(line) is None


def test_no_problems_when_params_matches_the_sketch_and_the_board():
    greeting = firmware.sketch_greeting()

    assert firmware.problems(firmware.sketch_baudrate(), greeting) == []


def test_params_disagreeing_with_the_sketch_is_a_problem_before_anything_opens():
    # The cheap half of the check: no board, no port, no power.
    found = firmware.problems(57600)

    assert len(found) == 1
    assert "57600" in found[0]
    assert str(firmware.sketch_baudrate()) in found[0]


def test_an_old_firmware_is_named_and_so_is_the_fix():
    found = firmware.greeting_problems(
        firmware.LEGACY_GREETING, params_baudrate=57600
    )

    assert any("firmware 1" in problem for problem in found)
    assert any(firmware.SKETCH_PATH.name in problem for problem in found)


def test_a_board_at_another_rate_is_a_problem_of_its_own():
    # Cannot happen at the same time as the one above in practice - a
    # board talking at the wrong rate never gets a greeting read at all -
    # but it is what the reply says once one has been read, e.g. after a
    # probe, and it names both numbers so it can be acted on.
    greeting = dict(firmware.sketch_greeting(), baudrate=57600)

    found = firmware.greeting_problems(greeting, params_baudrate=1000000)

    assert len(found) == 1
    assert "57600" in found[0] and "1000000" in found[0]


def test_a_greeting_with_no_baudrate_is_not_faulted_for_it():
    # Only the version is compulsory. A future firmware that stops
    # repeating the rate back should not be reported as mismatched.
    greeting = {"hello": "colloquy of mobiles", "firmware": 99}

    assert firmware.greeting_problems(greeting, params_baudrate=1000000) == []


def test_describe_says_both_halves_in_one_line():
    assert firmware.describe(None) == "not asked yet"
    assert firmware.describe(firmware.LEGACY_GREETING) == "firmware 1 at 57600 baud"


def test_the_probe_list_covers_every_rate_the_sketch_has_used():
    # Both ends of the change this module exists for, so a board left on
    # either one is diagnosed rather than reported silent.
    assert 57600 in firmware.PROBE_BAUDRATES
    assert firmware.sketch_baudrate() in firmware.PROBE_BAUDRATES
    # Fastest first: the likeliest answer costs the fewest reboots.
    assert list(firmware.PROBE_BAUDRATES) == sorted(
        firmware.PROBE_BAUDRATES, reverse=True
    )
