# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/drivers/test_boards.py

"""Naming a board without opening it -
colloquy/drivers/arduino/boards.py.

The point of the module is that it works on a board with nothing flashed
on it: what enumerates on the USB bus is the bridge chip, not the
processor running the sketch. So every test here works off a
ListPortInfo-shaped double and never opens anything.
"""
from types import SimpleNamespace

from colloquy.drivers.arduino import boards


def port(device="COM4", vid=None, pid=None, description=None, serial_number=None):
    """A stand-in for one pyserial ListPortInfo."""
    return SimpleNamespace(
        device=device,
        vid=vid,
        pid=pid,
        description=description,
        serial_number=serial_number,
    )


MEGA = port("COM4", vid=0x2341, pid=0x0042, description="Arduino Mega 2560 (COM4)")
CLONE = port("COM5", vid=0x1A86, pid=0x7523, description="USB-SERIAL CH340 (COM5)")
U2D2 = port("COM6", vid=0x0403, pid=0x6014, description="USB Serial Converter")
STRANGER = port("COM9", vid=0x1234, pid=0x5678, description="USB Serial Device (COM9)")


def test_an_official_mega_is_named_by_its_bridge_chip():
    board = boards.identify(MEGA)

    assert board.name == "Arduino Mega 2560 (R3)"
    assert board.is_arduino is True
    assert board.device == "COM4"


def test_a_ch340_clone_counts_as_an_arduino_but_says_what_it_saw():
    # In this room nothing else uses a CH340 - which is a guess, and the
    # reason the label names the chip rather than claiming a board.
    board = boards.identify(CLONE)

    assert board.is_arduino is True
    assert "CH340" in board.name


def test_an_ftdi_part_is_not_offered_as_an_arduino():
    # This is the U2D2. Pointing the Arduino driver at it gets a silence
    # indistinguishable from a dead board, which is exactly the mistake
    # worth making impossible from the picker.
    board = boards.identify(U2D2)

    assert board.is_arduino is False
    assert "U2D2" in board.name


def test_an_unknown_device_keeps_the_name_the_os_gave_it():
    # Unknown means unknown, not "not an Arduino" - it is left out of the
    # Arduino column rather than guessed at.
    board = boards.identify(STRANGER)

    assert board.name == "USB Serial Device (COM9)"
    assert board.is_arduino is False


def test_a_device_with_no_description_at_all_still_identifies():
    board = boards.identify(port("COM3"))

    assert board.name == "unknown device"
    assert board.is_arduino is False


def test_the_label_puts_the_com_name_first():
    # It is the half you have to choose; the rest is why.
    assert boards.identify(MEGA).label == "COM4 - Arduino Mega 2560 (R3)"


def test_detect_sorts_by_device_so_the_page_does_not_reshuffle():
    found = boards.detect([U2D2, MEGA, CLONE])

    assert [board.device for board in found] == ["COM4", "COM5", "COM6"]


def test_arduinos_leaves_out_the_lead_that_is_not_one():
    found = boards.arduinos([MEGA, U2D2, STRANGER])

    assert [board.device for board in found] == ["COM4"]


def test_nothing_plugged_in_is_an_empty_list_not_a_failure():
    assert boards.detect([]) == []


def test_serial_number_is_carried_through():
    # Two identical Megas on one machine are told apart by this and
    # nothing else.
    board = boards.identify(port("COM4", vid=0x2341, pid=0x0042, serial_number="85..."))

    assert board.serial_number == "85..."
