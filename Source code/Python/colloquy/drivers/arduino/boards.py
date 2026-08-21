# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/arduino/boards.py

"""What is plugged into the USB ports, and which of it is an Arduino.

The Arduino IDE can name a board with nothing flashed on it, and so can
this, for the same reason: the thing that appears on the USB bus is not
the ATmega2560 running the sketch, it is the separate chip bridging USB to
that chip's serial pins - an ATmega16U2 on an official Mega, a CH340 on
most clones. The bridge enumerates from power alone, with its own VID and
PID, whatever is or is not on the main processor. So an unflashed board
still shows up here, by name.

What it cannot tell you is whether the *right* sketch is on it: an empty
Mega and a working one are identical from the bus. That is what the
greeting in firmware.py is for, and the two are meant to be read together
- this one says a board is there, that one says it is ours.

This matters here beyond curiosity, because the installation has at least
two USB serial leads in it. The U2D2 is one of them, and telling it from
the Arduino by COM number alone means remembering which number Windows
handed out this week; telling them apart by the chip on the board does
not. Hence the `is_arduino` column, which is really "would it be sane to
point the Arduino driver at this one".
"""

from collections import namedtuple

import serial.tools.list_ports

from colloquy.base import Base
from colloquy.ui import leaves

# One row per USB device this room is likely to contain: (vid, pid) ->
# (what it is, could the Arduino driver sensibly open it).
#
# The `False` rows are as useful as the `True` ones. An FTDI part here is
# almost certainly the U2D2 - opening it as the Arduino gets a silence
# that looks exactly like a dead board.
KNOWN_DEVICES = {
    # Official Megas: the ATmega16U2 bridge, in its two revisions.
    (0x2341, 0x0010): ("Arduino Mega 2560 (R2)", True),
    (0x2341, 0x0042): ("Arduino Mega 2560 (R3)", True),
    (0x2A03, 0x0010): ("Arduino Mega 2560 (R2, arduino.org)", True),
    (0x2A03, 0x0042): ("Arduino Mega 2560 (R3, arduino.org)", True),
    # Other official boards, so that the wrong-board case is named rather
    # than left as "unknown".
    (0x2341, 0x0001): ("Arduino Uno", True),
    (0x2341, 0x0043): ("Arduino Uno (R3)", True),
    (0x2A03, 0x0043): ("Arduino Uno (R3, arduino.org)", True),
    (0x2341, 0x003D): ("Arduino Due", True),
    (0x2341, 0x8036): ("Arduino Leonardo", True),
    (0x2341, 0x0036): ("Arduino Leonardo (bootloader)", True),
    # Clone bridges. Counted as Arduinos because in this room that is what
    # they are - nothing else here uses a CH340 - which is a guess, and
    # the reason the label says which chip it saw rather than claiming a
    # board.
    (0x1A86, 0x7523): ("CH340 USB-serial (a Mega or Uno clone)", True),
    (0x1A86, 0x5523): ("CH341 USB-serial (a clone board)", True),
    (0x1A86, 0x55D4): ("CH9102 USB-serial (a clone board)", True),
    # FTDI parts. The U2D2 is one of these, which is exactly why they are
    # not offered as Arduinos.
    (0x0403, 0x6001): ("FTDI FT232R - the U2D2 is an FTDI device", False),
    (0x0403, 0x6014): ("FTDI FT232H - the U2D2 is an FTDI device", False),
    (0x0403, 0x6015): ("FTDI FT-X - the U2D2 is an FTDI device", False),
    (0x10C4, 0xEA60): ("CP2102 USB-serial", False),
}


class Board(namedtuple("Board", "device name is_arduino vid pid serial_number")):
    """One thing on the USB bus, as far as it can be seen without opening
    it. `device` is the COM name, `name` is what the chip says it is."""

    @property
    def label(self):
        """How it reads on the page, and the key it is filed under: the
        COM name is what you have to choose, the rest is why."""
        return f"{self.device} - {self.name}"


def identify(port):
    """One pyserial ListPortInfo -> what is on the other end of it.

    A port whose VID/PID is not in the table falls back to whatever the
    operating system called it, which on Windows is usually the generic
    "USB Serial Device". Unknown means unknown, not "not an Arduino": it
    is left out of the Arduino column rather than guessed at, since the
    cost of guessing wrong is a driver pointed at the U2D2.
    """
    vid = getattr(port, "vid", None)
    pid = getattr(port, "pid", None)
    name, is_arduino = KNOWN_DEVICES.get(
        (vid, pid), (getattr(port, "description", None) or "unknown device", False)
    )
    return Board(
        device=port.device,
        name=name,
        is_arduino=is_arduino,
        vid=vid,
        pid=pid,
        serial_number=getattr(port, "serial_number", None),
    )


def detect(ports=None):
    """Every serial port this machine has, identified.

    `ports` is there to be handed a list in a test; left alone it asks the
    operating system. Sorted by device name so the page does not reshuffle
    itself between two renders.
    """
    if ports is None:
        ports = serial.tools.list_ports.comports()
    return sorted((identify(port) for port in ports), key=lambda board: board.device)


def arduinos(ports=None):
    """Only the ones it would make sense to open as the Arduino."""
    return [board for board in detect(ports) if board.is_arduino]


class Boards(Base):
    """The USB bus, on the page.

    Hangs off the Arduino because that is the question it answers - "is
    the board even there, and which lead is it on" - and because the
    answer is worth having *before* anything is opened. Every other
    diagnosis in this driver needs a working link first.
    """

    @property
    def name(self):
        return "usb boards"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        found = detect()
        if not found:
            # Worth saying out loud rather than drawing an empty list: on
            # the installation it means the lead is out, and on a dev
            # machine it means this is simply not the machine.
            leaf("ports", "none - nothing is plugged in")
            return states

        for board in found:
            leaf(board.device, board.name)

        leaf("arduinos", ", ".join(board.device for board in found if board.is_arduino) or "none")
        leaf(
            "arduino is set to",
            self.owner.params["arduino"]["communication port"] or "not set",
        )
        return states
