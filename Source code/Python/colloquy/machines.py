# -*- coding: utf-8 -*-
# Source code/Python/colloquy/machines.py

"""Which computer this is, and therefore what is real on it.

There are two machines with hardware attached, and they have different
hardware attached, so "is this simulated?" was never really one question:

- **The installation** (`Colloquy-Laptop`) has the piece on it - nine
  Dynamixel servos through a U2D2, and the Arduino carrying every
  NeoPixel and light sensor. It has no audio bench and never will: the
  audio boards live in an office.
- **The bench** (`DESKTOP-MRSLS88`) has Thomas's audio subsystem on it -
  his Mega 2560, the filter board, the amplifiers, the microphones and
  the analyser array. It has none of the piece.
- **Anything else** - the other dev machine, CI - has neither, and runs
  entirely against `colloquy/virtual_drivers/`.

So a body is simulated everywhere except the installation, and the audio
board is simulated everywhere except the bench, and those are two
different tests. Both are exact hostname matches, which is blunt but
honest: see test_simulated_switch.py for what a near-miss costs.

Moving a machine or renaming one means editing the two names here and
nowhere else.
"""
import socket

INSTALLATION = "Colloquy-Laptop"
BENCH = "DESKTOP-MRSLS88"


def hostname():
    return socket.gethostname()


def is_installation():
    """The machine the piece is wired to."""
    return hostname() == INSTALLATION


def is_bench():
    """The machine Thomas's audio subsystem is wired to."""
    return hostname() == BENCH
