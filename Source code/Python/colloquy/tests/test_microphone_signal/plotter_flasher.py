# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_microphone_signal/plotter_flasher.py

"""Putting `microphone_plotter` on the installation's own Mega.

This test is the one place in the repo where flashing the piece's board
with something that is *not* the piece's firmware is the instruction
rather than a mistake. Two of its three wiring routes - **B**, the
microphone straight onto `A0` with the analyser array out, and **C**, the
Mega borrowing a female's photosensor pin - leave `microphone_plotter` on
the installation's board, because the instrument is the Arduino IDE's
Serial Plotter and the trace has to come from somewhere.

`flash colloquy firmware back` has been on this test's page since the
routes were written, for the reason that the page telling you to break it
should carry the fix. **The other direction was never there**, and it is
the one the document had to send somebody to the Arduino IDE for: open
the sketch, pick the board, pick the port, upload. Every one of those
four is a thing this page already knows.

**There is no handshake, and that is the honest answer rather than a gap.**
`microphone_plotter` greets with nothing - it streams `min:`/`max:`/
`mean:` lines for a plotter to draw and says nothing about itself, which
is exactly right for what it is. So `_check_the_board` has nothing to
ask, and rather than passing avrdude's word off as the board's it says
what is now true instead: the driver's link is deliberately left shut,
because `Arduino.open()` waits for a greeting that will not come and
refuses a firmware it was not written for. `plotter sketch` on the test's
own page is the nearest thing to a handshake there is - the pin and the
mode read out of the .ino, which is what a wrong sketch shows up as.
"""
from colloquy.drivers.arduino import firmware
from colloquy.drivers.arduino.flasher.base import SketchFlasher

from . import plotter_sketch


class PlotterFlasher(SketchFlasher):
    """`microphone_plotter`, onto the board the piece normally runs on."""

    @property
    def name(self):
        # Not `flash firmware`, though it is one: this board has two
        # sketches that belong on it at different moments, and a link
        # named for neither of them would be the one press on this page
        # somebody could get the wrong way round.
        return "flash the plotter sketch"

    @property
    def test(self):
        return self.owner

    @property
    def arduino(self):
        return self.test.drivers.arduino

    @property
    def sketch_folder(self):
        return plotter_sketch.SKETCH_PATH.parent

    @property
    def port(self):
        """The installation's own lead. The same board the piece uses -
        that is the whole point of routes B and C, and the whole reason
        the way back has to be on this page too."""
        return self.params["arduino"]["communication port"]

    @property
    def fqbn(self):
        """The installation's board type, since it is the installation's
        board."""
        return self.params["arduino"]["fqbn"]

    def sketch_says(self):
        return plotter_sketch.describe()

    def _extra_refusals(self):
        """The board is on a PCB, and the PCB comes out of the rack."""
        if not self.colloquy.hardware.main_pcb.is_mounted:
            return (
                "the main PCB is noted as unmounted, so the board is not on "
                "the end of anything - put it back first"
            )
        return None

    def _release_the_link(self):
        """Close the driver's link so avrdude can have the port."""
        was_open = self.arduino.is_open
        if was_open:
            self.arduino.close()
        return was_open

    def _check_the_board(self, was_open):
        """There is nothing to ask, so say what is true instead.

        Deliberately not a reopen. `Arduino.open()` waits for a greeting
        `microphone_plotter` does not send and refuses a firmware it was
        not written for, so reopening would report a failure that is the
        expected outcome of a successful flash.
        """
        return (
            f"flashed {self.sketch_says()} - the driver's link is left "
            "closed on purpose, since this sketch does not greet and "
            f"firmware {firmware.sketch_firmware_version()} is what "
            "`Arduino.open()` wants. Open the Serial Plotter at "
            f"{plotter_sketch.plot_baudrate()} baud; press 'flash colloquy "
            "firmware back' when you are done"
        )

    def _extra_readings(self, leaf):
        leaf(
            "the way back",
            "'flash colloquy firmware back', on the test's own page - "
            "until firmware "
            f"{firmware.sketch_firmware_version()} is on this board the "
            "driver will not open the link at all",
        )
