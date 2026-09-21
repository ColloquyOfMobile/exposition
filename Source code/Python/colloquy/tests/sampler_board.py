# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/sampler_board.py

"""The board `test goertzel ear` and `scope` share, and the two presses
that make it knowable: flash it, and ask it what it is.

Both tests point a lead at `Source code/Arduino/microphone_sampler/`,
open it, and read captures off it. Neither could say what was on the
board until it was already running - the greeting arrives on reboot, the
port reboots the board when it opens, and the port opens at `setup()`.
So the page said `board says: -` until you pressed start, and a run that
came back with one flat line was equally a dead microphone, a missing
lead and an old sketch. `scope` learned to tell the last of those apart
on its own page; it still could not do anything about it.

**Two presses, because they answer two different questions.**
`flash firmware` puts the sketch in this repo on the board. `ask the
board` opens the lead, reads the line it greets with, and closes again -
which is a whole measurement in itself, and the one worth having *before*
a run rather than after: whether this lead has the right board on it at
all. A flash ends by making the same call, because an upload avrdude
called a success and that left the wrong image on the board is caught
there and nowhere else.

**Opening the port is what reboots the board**, so asking costs a reboot
and there is no way to ask without one. That is fine here and worth
knowing: it is why the greeting is missed whenever the port was already
open, and why `ask the board` puts the port back the way it found it
rather than holding it - the other test on the bench may want the lead.

`MINIMUM_FIRMWARE` is the host's, not this module's: `b` is unchanged
since firmware 1 and `d` arrived in firmware 2, so the two tests need
different things of the same board. See `sampler_sketch.verdict`.
"""
from time import time

import serial

from colloquy.drivers.arduino.flasher.base import SketchFlasher

from . import sampler_sketch

# Long enough for a board that reboots on DTR and then writes a line;
# short enough that a lead with nothing on it is reported rather than
# sat on. The same four seconds both tests already waited.
GREETING_TIMEOUT = 4.0


class SamplerBoard:
    """A mixin for a test whose hardware is one `microphone_sampler`.

    The host provides `port_handler`, `com_port`, `_why_not_open()` and
    `name`, and initialises `_greeting` and `_firmware` to None. In
    return it gets the greeting read for it, a `flash firmware` child, an
    `ask the board` command and the two readings that go with them.

    A mixin rather than a base class because both hosts are already
    `BaseThread`s with a great deal of their own, and what is shared here
    is one board and two presses - not a kind of test.
    """

    # What this host needs of the board, and what it needs it for.
    # Overridden by `scope`, which asks for a command firmware 1 does not
    # have. The second half is prose and earns its place: "the second
    # channel needs 2" says what is lost, and "this needs 2" does not.
    MINIMUM_FIRMWARE = 1
    FIRMWARE_NEEDED_FOR = None

    # A class attribute rather than the module constant used directly, so
    # that a test of this can wait a tenth of a second for a board that
    # was never going to answer instead of four.
    GREETING_TIMEOUT = GREETING_TIMEOUT

    # --- the greeting -----------------------------------------------------

    def _read_greeting(self):
        """Read the line the board sends on reboot, into `_greeting`.

        Only ever called with the port freshly opened: the board greets
        unprompted on the way up and says nothing like it again, so a
        port that was already open has missed it and there is no asking
        for it a second time without another reboot.
        """
        self._greeting = None
        self._firmware = None
        deadline = time() + self.GREETING_TIMEOUT
        while time() < deadline and self._greeting is None:
            raw = self.port_handler.readline()
            if raw and raw.startswith(sampler_sketch.GREETING_PREFIX.encode()):
                self._greeting = raw.decode("ascii", "replace").strip()
                self._firmware = sampler_sketch.firmware_in(self._greeting)

    def _open_if_needed(self):
        """Open the lead if it is shut, and hear the board out if so."""
        if not self.port_handler.is_open:
            self.port_handler.open()
            # It reboots when the port opens and greets on the way up.
            self._read_greeting()

    # --- what the board says about itself ---------------------------------

    @property
    def firmware(self):
        """What the board last said it was running, or None."""
        return self._firmware

    @property
    def board_verdict(self):
        """That version measured against what this test needs, in words."""
        return sampler_sketch.verdict(
            self._firmware, self.MINIMUM_FIRMWARE, self.FIRMWARE_NEEDED_FOR
        )

    def handshake(self):
        """Open the lead, hear the board out, put the lead back. One line.

        Leaves the port exactly as it found it. A port already open has
        missed the greeting and cannot be made to repeat it without a
        reboot, so this says so rather than reopening underneath a run
        that is reading captures off it.

        Silence is answered here rather than by `verdict`, and the
        difference is the whole value of the press: this end has just
        asked, so nothing coming back is a finding about the lead, where
        the same None on the page merely means nobody has asked yet.
        """
        if self.port_handler.is_open:
            return (
                "the lead is already open, so the greeting has been and "
                "gone - what was heard of it: " + self.board_verdict
            )
        try:
            self._open_if_needed()
        finally:
            if self.port_handler.is_open:
                self.port_handler.close()
        if self._greeting is None:
            return (
                f"nothing greeted - if a board is on this lead it is not "
                f"running {sampler_sketch.GREETING_PREFIX}. Flash it: the "
                f"sketch here is firmware {sampler_sketch.firmware_version()}"
            )
        return self.board_verdict

    def ask_the_board(self, request=None):
        """`ask the board` - the handshake, as a press.

        Worth having on its own rather than only as the tail of a flash:
        the question it answers is whether this lead has the right board
        on it, and that is a thing to know *before* a run, not after one
        has come back with a flat line.
        """
        if self.is_started:
            # The loop owns the port and is asking it for captures. A
            # reboot in the middle of that would lose a block and answer
            # nothing new - the greeting is already as read as it gets.
            return (
                f"{self.name} is running and holding the lead - "
                + self.board_verdict
            )
        refusal = self._why_not_open()
        if refusal is not None:
            return f"refused: {refusal}"
        try:
            return self.handshake()
        except serial.SerialException as error:
            return f"could not open the lead - {error}"

    # --- the page ---------------------------------------------------------

    def _board_readings(self, leaf):
        """The two lines every host of this mixin draws the same way."""
        if self._greeting:
            leaf("board says", self._greeting)
        # Named on its own line rather than left inside the greeting: a
        # version is the thing being judged, and the judging is the whole
        # reason the version is on the page.
        leaf("firmware", self.board_verdict)


class SamplerFlasher(SketchFlasher):
    """`microphone_sampler`, onto whichever lead its test is pointed at.

    Everything about compiling and uploading is `SketchFlasher`'s, down
    to the four refusals - and the fourth of those, which refuses while
    anything under `tests` is running, is what keeps this from rewriting
    a board in the middle of its own owner's run. It needs no help
    knowing that: the owner is a thread under `tests` like any other.

    What is added here is the two ends of the lead. The port comes from
    the owner's own picker rather than from the installation's params,
    and the check afterwards is the owner's handshake - so the outcome
    line is the board saying in its own words what it is now running,
    measured against what this particular test needs of it.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def sketch_folder(self):
        return sampler_sketch.SKETCH_FOLDER

    @property
    def port(self):
        """The lead the owning test is pointed at.

        Read back out of its picker on every use, like everything else
        that reads a chosen port: `BenchComPort.set()` writes params and
        then asks its owner to re-point, so params is where the answer
        lives.
        """
        return self.owner.com_port.chosen

    def sketch_says(self):
        return sampler_sketch.describe()

    def _release_the_link(self):
        """Let go of the lead so avrdude can have it.

        avrdude cannot have the port while pyserial holds it, and the
        error it gives for that names neither. The owner's run is
        refused by then, so an open port here means somebody pressed
        `ask the board` and something went wrong putting it back.
        """
        handler = self.owner.port_handler
        if handler.is_open:
            handler.close()
        return None

    def _check_the_board(self, state):
        """Ask the freshly flashed board what it is, through the owner."""
        try:
            said = self.owner.handshake()
        except Exception as error:  # pragma: no cover - a lead pulled mid-flash
            return f"uploaded, but the board could not be asked: {error}"
        return f"flashed - {said}"

    def _extra_readings(self, leaf):
        leaf("board last said", self.owner.board_verdict)
