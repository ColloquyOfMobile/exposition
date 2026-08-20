# -*- coding: utf-8 -*-
# Source code/Python/colloquy/virtual_hardware/virtual_audio_serial_port.py

"""Stands in for Thomas's audio subsystem tester when there is no board.

The real thing is a Mega 2560 running `Source code/Thomas/
AudioAnalyzerTest.cpp`: a text menu at 9600 baud, five hardware timers
making five tones, and five MSGEQ7 analyser modules reading seven bands
each. This answers the same menu, with the same quirks, so the bench test
can be exercised and read without a board on the desk.

What is modelled is only what the test depends on:

- the welcome banner on open, since opening the port resets the board and
  the test uses the banner to tell this board from the installation's own
  Arduino on the next socket down;
- the "> " prompt, printed *before* the input buffer is cleared, which is
  the firmware's one real trap;
- E/D/A/I, and the fact that "A" streams until it is sent an "X" and then
  redraws the whole welcome banner;
- readings that follow which timers are on: the tone's own band rises on
  every module, the rest sit at a noise floor.

What is deliberately **not** modelled is the room: a real module hears a
real speaker through air, so a real bench can perfectly well show one
module deaf while its neighbours are fine, and this cannot. A green run
here says the test drives the menu correctly; it says nothing about
anybody's wiring.
"""
from random import Random
from time import time

from colloquy.base import Base
from colloquy.tests.test_audio_subsystem import protocol

# 9600 baud, 8N1: ten bits a character, so 960 characters a second. This
# is enforced below rather than decorative, for the same reason
# VirtualSerialPort has a latency - an instant reply is not neutral. A
# dump of five modules is some 700 characters, three quarters of a second
# on the wire, so a three-second read gets four sweeps. Unthrottled it
# got four thousand, and the run wrote a 25MB file that no bench would
# ever produce.
CHARS_PER_SECOND = 960

WELCOME = (
    "\x1b[2J\x1b[H"
    "----           Audio subsystem tester for            ----\r\n"
    "----        Gordon Pask - Colloquy of Mobiles        ----\r\n"
    "---- Copyright: ZKM | Zentrum fuer Kunst und Medien  ----\r\n"
    "----                  Center for Art and Media       ----\r\n"
    "----                                                 ----\r\n"
    "----                  Enter 'H' for help             ----\r\n"
    "\r\n"
)

INFO = (
    "\t\t\tTimer Info\r\n"
    "Timer:\t\tT1\tT3\tT4\tT5\tT2\r\n"
    "Frequency:\t160Hz\t400Hz\t1kHz\t2k5Hz\t6k25Hz\r\n"
    "Pin:\t\tD11\tD5\tD6\tD46\tD10\r\n"
    "Configure terminal to: 'local echo' and 'send on enter'\r\n"
    "\r\n"
)

HEADER = (
    "Module\t63 Hz\t160 Hz\t400 Hz\t1k Hz\t2.5k Hz\t6.25kHz\t16k Hz\r\n"
    "---------------------------------------------------------------\r\n"
)
RULE = "---------------------------------------------------------------\r\n"

# What a band reads with nothing playing, and what it reads with its own
# tone on. Both well inside the ADC's 0-1023, and far enough apart that
# the test's margin is not the thing under test.
NOISE_FLOOR = 40
TONE_LEVEL = 620


class VirtualAudioSerialPort(Base):
    """A pyserial-shaped object: port, open/close/read/write/is_open."""

    def __init__(self, owner, port=None):
        super().__init__(owner=owner)
        assert port is None, f"Port should be none to avoid opening! ({port=})"
        self._port = None
        self._is_open = False
        self._out = ""
        self._line = ""
        self._enabled = set()
        self._dumping = None
        self._random = Random(0)
        self._sent_at = None
        self._budget = 0.0

    @property
    def name(self):
        return "audio serial port"

    @property
    def snapshot_children(self):
        return {}

    # --- the pyserial surface --------------------------------------------

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    @property
    def is_open(self):
        return self._is_open

    def open(self):
        assert self._port is not None
        # Opening the port resets the board, which is why the banner comes
        # out here and not in __init__: a second run gets a second banner,
        # exactly as the real one does.
        self._enabled = set()
        self._dumping = None
        self._out = WELCOME + protocol.PROMPT
        self._sent_at = time()
        self._budget = 0.0
        self._is_open = True

    def close(self):
        self._is_open = False
        self._out = ""

    def read(self, size=1):
        if not self._is_open:
            raise AssertionError("Port should be open before using it.")

        # Only as many characters as the wire could have carried since the
        # last read. Without this the caller is handed everything at once
        # and a timed read collects thousands of sweeps instead of four.
        now = time()
        self._budget += (now - self._sent_at) * CHARS_PER_SECOND
        self._sent_at = now
        allowed = min(size, int(self._budget))
        if allowed < 1:
            return b""

        # A sweep at a time until there is enough to hand back: the real
        # board is streaming continuously, so a big read should get
        # several tables and not one. Making only one per read meant a
        # long listen came back as short as a brief one.
        while self._dumping is not None and len(self._out) < allowed:
            self._out += self._table(self._dumping)

        chunk, self._out = self._out[:allowed], self._out[allowed:]
        self._budget -= len(chunk)
        return chunk.encode("ascii")

    def write(self, data):
        if not self._is_open:
            raise AssertionError("Port should be open before using it.")
        self._line += data.decode("ascii", "replace")
        while "\n" in self._line:
            line, self._line = self._line.split("\n", 1)
            self._handle(line.strip("\r "))
        return len(data)

    def flush(self):
        pass

    # --- the menu ---------------------------------------------------------

    def _handle(self, line):
        if not line:
            self._out += protocol.PROMPT
            return

        command, argument = line[0], (line[1:2] or "")

        # A dump is the one command that does not return to the prompt: it
        # streams until an 'X' arrives, and then the firmware falls out of
        # processCommands() and main() redraws the banner.
        if self._dumping is not None:
            if command == "X":
                self._dumping = None
                self._out += "\r\n" + WELCOME + protocol.PROMPT
            return

        if command == "A":
            self._dumping = argument if argument in "01234" else "a"
            self._out += (
                f"< Dump {'five analyzers' if self._dumping == 'a' else 'analyzer ' + self._dumping}\r\n"
                "< Enter 'X' to abort action\r\n\r\n"
            )
            return

        if command == "E":
            if argument == "a":
                self._enabled = set(protocol.TIMERS)
                self._out += "< Enable five timers\r\n"
            else:
                timer = self._clamp(argument)
                self._enabled.add(timer)
                self._out += f"< Enable timer {timer}\r\n"
        elif command == "D":
            if argument == "a":
                self._enabled = set()
                self._out += "< Disable five timers\r\n"
            else:
                timer = self._clamp(argument)
                self._enabled.discard(timer)
                self._out += f"< Disable timer {timer}\r\n"
        elif command == "I":
            self._out += INFO
        elif command == "H":
            self._out += "----         Commands          ----\r\n\r\n"

        self._out += "\r\n" + protocol.PROMPT

    @staticmethod
    def _clamp(argument):
        """The firmware's own clamp: anything outside 1-5 becomes 1."""
        try:
            timer = int(argument)
        except ValueError:
            return 1
        return timer if 1 <= timer <= 5 else 1

    # --- what the analysers say ------------------------------------------

    def _levels(self):
        levels = [NOISE_FLOOR] * len(protocol.BANDS_HZ)
        for timer in self._enabled:
            levels[protocol.expected_band(timer)] = TONE_LEVEL
        return levels

    def _table(self, option):
        levels = self._levels()
        text = HEADER
        for module in range(protocol.MODULE_COUNT):
            if option != "a" and int(option) != module:
                continue
            values = [
                max(0, level + self._random.randrange(-8, 9)) for level in levels
            ]
            text += "   " + str(module) + "\t"
            text += "\t".join(" " + str(value) for value in values)
            text += "\r\n" + RULE
        return text + "\r\n"
