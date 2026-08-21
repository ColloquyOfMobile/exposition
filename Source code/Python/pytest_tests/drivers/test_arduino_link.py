# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/drivers/test_arduino_link.py

"""Opening the Arduino's link, and refusing to open a broken one -
colloquy/drivers/arduino/__init__.py.

Arduino cannot be constructed here (it builds thirty-odd child nodes and
reaches for `colloquy.virtual_drivers`), so every test below calls the
method unbound against a double exposing only what that method touches -
the pattern conftest.py describes.

What is being pinned is that the three failures this link has are told
apart, because they need three different things done about them: a baud
rate typed wrong in params.json, a board flashed with something older,
and a board that is there but silent.
"""
import json
from types import SimpleNamespace

import pytest

from colloquy.base import Base
from colloquy.drivers.arduino import Arduino, firmware


class FakePort:
    """Just enough pyserial to be opened and read a line from."""

    def __init__(self, lines=()):
        self.lines = list(lines)
        self.is_open = False
        self.opened = 0
        self.closed = 0
        self.baudrate = firmware.sketch_baudrate()

    def open(self):
        self.is_open = True
        self.opened += 1

    def close(self):
        self.is_open = False
        self.closed += 1

    def readline(self):
        if not self.lines:
            return b""
        return self.lines.pop(0)


def greeting_line(**overrides):
    return json.dumps(dict(firmware.sketch_greeting(), **overrides)).encode() + b"\r\n"


def fake_arduino(**kwargs):
    fake = SimpleNamespace(
        baudrate=firmware.sketch_baudrate(),
        port_name="COM4",
        port_handler=FakePort(),
        GREETING_TIMEOUT=0.2,
        is_simulated=True,
        log=lambda *args, **kwargs: None,
        _greeting=None,
    )
    for key, value in kwargs.items():
        setattr(fake, key, value)
    return fake


# --- the cheap half: params against the sketch, before anything opens ----


def test_open_refuses_a_baudrate_the_sketch_does_not_use():
    # No board, no port, no power needed - and this is the mismatch that
    # happens by itself, since the two numbers live in two files edited on
    # two different occasions.
    fake = fake_arduino(baudrate=57600, wait_for_reboot=lambda: None)

    with pytest.raises(RuntimeError, match="57600"):
        Arduino.open(fake)

    assert fake.port_handler.opened == 0


def test_open_greets_when_the_two_agree():
    called = []
    fake = fake_arduino(wait_for_reboot=lambda: called.append("greeted"))

    Arduino.open(fake)

    assert fake.port_handler.opened == 1
    assert called == ["greeted"]


def test_open_forgets_the_last_boards_greeting():
    # Otherwise a failed reopen leaves the page showing what the *previous*
    # board said, which is the one reading nobody would think to doubt.
    fake = fake_arduino(_greeting={"firmware": 2}, wait_for_reboot=lambda: None)

    Arduino.open(fake)

    assert fake._greeting is None


# --- reading the greeting ------------------------------------------------


def test_read_greeting_returns_what_the_board_said():
    fake = fake_arduino(port_handler=FakePort([greeting_line()]))

    assert Arduino._read_greeting(fake) == firmware.sketch_greeting()


def test_read_greeting_steps_over_rubbish_to_find_the_line():
    # At the wrong baud rate the board answers with noise, and noise
    # occasionally contains a newline.
    fake = fake_arduino(
        port_handler=FakePort([b"\xf8\x00\x9c\r\n", b"", greeting_line()])
    )

    assert Arduino._read_greeting(fake) == firmware.sketch_greeting()


def test_read_greeting_gives_up_on_silence():
    assert Arduino._read_greeting(fake_arduino()) is None


# --- what the greeting is checked for ------------------------------------


def test_wait_for_reboot_keeps_a_good_greeting():
    greeting = firmware.sketch_greeting()
    fake = fake_arduino(_read_greeting=lambda: greeting)

    Arduino.wait_for_reboot(fake)

    assert fake._greeting == greeting


def test_wait_for_reboot_refuses_a_board_flashed_with_the_old_firmware():
    # The failure this exists for: firmware 1 answers a path it does not
    # know with an empty line, so left unchecked the only symptom is a
    # female who reads no pattern for forty minutes.
    fake = fake_arduino(_read_greeting=lambda: dict(firmware.LEGACY_GREETING))

    with pytest.raises(RuntimeError, match="firmware 1"):
        Arduino.wait_for_reboot(fake)


def test_wait_for_reboot_refuses_a_board_talking_at_another_rate():
    fake = fake_arduino(_read_greeting=lambda: firmware.sketch_greeting() | {"baudrate": 57600})

    with pytest.raises(RuntimeError, match="57600"):
        Arduino.wait_for_reboot(fake)


def test_wait_for_reboot_asks_for_a_diagnosis_when_nothing_comes_back():
    fake = fake_arduino(
        _read_greeting=lambda: None,
        _diagnose_silence=lambda: "the lead is out",
    )

    with pytest.raises(RuntimeError, match="the lead is out"):
        Arduino.wait_for_reboot(fake)


# --- and the diagnosis ---------------------------------------------------


def test_a_simulated_port_is_not_probed():
    # It ignores baud rates entirely, so probing would "find" the board at
    # the first rate tried and say something confidently wrong.
    def must_not_be_called(baudrate):
        raise AssertionError("probed a simulated port")

    fake = fake_arduino(is_simulated=True, _greet_at=must_not_be_called)

    assert "did not greet" in Arduino._diagnose_silence(fake)


def test_the_probe_names_the_rate_the_board_is_really_at():
    # The quietest failure this link has: the board is there, it is
    # answering, and every byte of it is rubbish.
    tried = []

    def greet_at(baudrate):
        tried.append(baudrate)
        if baudrate == 57600:
            return dict(firmware.LEGACY_GREETING)
        return None

    fake = fake_arduino(is_simulated=False, _greet_at=greet_at)

    message = Arduino._diagnose_silence(fake)

    assert "57600" in message
    assert str(firmware.sketch_baudrate()) in message
    assert firmware.SKETCH_PATH.name in message
    # Never at the rate that has already been tried and failed.
    assert firmware.sketch_baudrate() not in tried


def test_a_board_that_answers_at_no_rate_is_reported_with_the_usb_bus(monkeypatch):
    # A board that has never been flashed enumerates all the same, so
    # "a Mega is plugged in and silent" and "there is nothing there" are
    # different things - and only one of them means fetch a cable.
    from colloquy.drivers.arduino import boards

    monkeypatch.setattr(
        boards,
        "detect",
        lambda ports=None: [
            boards.Board("COM4", "Arduino Mega 2560 (R3)", True, 0x2341, 0x0042, None)
        ],
    )
    fake = fake_arduino(is_simulated=False, _greet_at=lambda baudrate: None)

    message = Arduino._diagnose_silence(fake)

    assert "COM4 - Arduino Mega 2560 (R3)" in message
    assert "never been flashed" in message


def test_nothing_on_the_bus_at_all_says_so(monkeypatch):
    from colloquy.drivers.arduino import boards

    monkeypatch.setattr(boards, "detect", lambda ports=None: [])
    fake = fake_arduino(is_simulated=False, _greet_at=lambda baudrate: None)

    assert "USB lead" in Arduino._diagnose_silence(fake)


# --- the page ------------------------------------------------------------


def test_the_nodes_open_link_opens_the_node_not_the_port():
    # Arduino.open()/close() open and close the *link*, and they share
    # their names with Base.open()/close(), which are what the page's
    # open/close link calls on every node. Drawn as it stood, clicking the
    # Arduino to look inside it would have opened the serial port.
    assert Arduino.open is not Base.open

    fake = SimpleNamespace(_is_opened=False)
    Arduino._open_node(fake)
    assert fake._is_opened is True

    Arduino._close_node(fake)
    assert fake._is_opened is False
