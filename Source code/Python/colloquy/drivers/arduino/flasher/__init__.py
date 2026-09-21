# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/arduino/flasher/__init__.py

"""Putting the sketch in this repo onto the board on the other end.

The page has been able to say the board is running the wrong firmware
since the greeting was added; it has never been able to do anything about
it. That gap got worse with the audio rework, because firmware 2 and
firmware 3 disagree about which pin drives which NeoPixel strip - so a
board left on 2 in an installation wired for 3 answers every command
cheerfully and lights the wrong bodies. `MINIMUM_FIRMWARE_VERSION` makes
the driver refuse that link, which is right, and leaves somebody standing
in a gallery being told to go and find a laptop with the Arduino IDE on
it.

This is that laptop, generally. `drivers/arduino` already knows which
lead the board is on, what is on the USB bus, what version the sketch in
the repo is and what version the board says it is running. Flashing is
the one step that was somewhere else.

**Everything about the shape of the job is in `base.py` now** - the
thread, the toolchain calls, the four refusals, the page - because
`test goertzel ear`, `scope` and `test microphone signal` each turned out
to want the same thing for a different sketch on a different lead. What
stays here is what is true of *this* board and no other:

- the sketch is `colloquy_of_mobiles`, and `firmware.py` already owns the
  path to it and reads its two `#define`s;
- the board type is configurable in params, because this is the one board
  somebody might one day replace;
- the PCB it is soldered to can be taken out of the rack, which makes
  every other question moot;
- and the link is `Arduino`, which is the whole reason a flash can be
  *checked*: `Arduino.open()` waits for the greeting and refuses a
  version it was not written for, so a reopen that succeeds is the board
  saying in its own words which firmware it is now running. An upload
  that avrdude called a success and that left the wrong image on the
  board is caught there and nowhere else.
"""

from colloquy.ui import leaves

from .. import firmware
from .base import SketchFlasher
from .toolchain import ToolchainError

__all__ = ["Flasher", "SketchFlasher", "ToolchainError"]


class Flasher(SketchFlasher):
    """Compile the piece's own sketch, and put it on the piece's board."""

    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def arduino(self):
        return self.owner

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def params(self):
        return self.owner.params

    # --- what it would run ------------------------------------------------

    @property
    def sketch_folder(self):
        """The folder, not the .ino: that is what arduino-cli takes, and
        `firmware.py` already owns the path to the file inside it."""
        return firmware.SKETCH_PATH.parent

    @property
    def fqbn(self):
        """From params, unlike every other flasher in the tree: this is
        the board in the rack, and the one somebody might replace."""
        return self.params["arduino"]["fqbn"]

    @property
    def port(self):
        return self.params["arduino"]["communication port"]

    def sketch_says(self):
        return (
            f"firmware {firmware.sketch_firmware_version()} "
            f"at {firmware.sketch_baudrate()} baud"
        )

    # --- what only this board can refuse ----------------------------------

    def _extra_refusals(self):
        """The board is on a PCB, and the PCB comes out of the rack.

        First of all the refusals, because a board that is not on the end
        of anything makes every question about ports moot.
        """
        if not self.colloquy.hardware.main_pcb.is_mounted:
            return (
                "the main PCB is noted as unmounted, so the board is not on "
                "the end of anything - put it back first"
            )
        return None

    # --- the link, which is what makes the check possible -----------------

    def _release_the_link(self):
        was_open = self.arduino.is_open
        if was_open:
            # avrdude cannot have the port while pyserial holds it, and
            # the error it gives for that names neither.
            self.arduino.close()
        return was_open

    def _check_the_board(self, was_open):
        """Open the link again and let the board say what it is.

        Returns the whole outcome line. Not tidiness - see the module
        docstring: this is the only check there is on what actually
        reached the flash.
        """
        if not was_open:
            return (
                f"uploaded {self.sketch_says()} - the link was closed, "
                "open the port to check the board"
            )
        try:
            self.arduino.open()
        except RuntimeError as error:
            return f"uploaded, but the board did not come back: {error}"
        return f"flashed - board says {firmware.describe(self.arduino.greeting)}"

    # --- the page ---------------------------------------------------------

    def _extra_readings(self, leaf):
        leaf("board says", firmware.describe(self.arduino.greeting))
