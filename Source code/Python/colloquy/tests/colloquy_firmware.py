# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/colloquy_firmware.py

"""The piece's own sketch, on the page of a test that cannot work without
it.

Eleven tests under `colloquy/tests/` reach the installation's board -
every one that lights a NeoPixel, reads a photosensor, sounds a tone or
hears one. All of them fail the same way against a stale sketch, and it
is the failure mode this repo keeps being bitten by: **the board answers
cheerfully and is wrong**. Firmware 2 and 3 disagree about which pin
drives which NeoPixel strip, so a board on 2 in a rack wired for 3 lights
the wrong bodies and reports success. Firmware 3 and 4 disagree about
which body speaks at which pitch, so a driver judging a firmware-3 board
by this repo's table gets every verdict wrong while a tone still comes
out and a band still rises.

`Arduino.open()` refuses a version it was not written for, which is what
turns that into a legible failure - and then leaves somebody looking at a
test page with the fix three levels away under `drivers > arduino`. That
is `test microphone signal`'s argument, made once for the one test that
was known to need it; it is the same argument for all eleven.

**It is a view, not a second flasher.** There is one board and one lead,
so there is one `Flasher`, and it hangs where it belongs - under the
Arduino that owns the port. This node forwards the two presses to it and
draws what it says. Two consequences worth knowing:

- every refusal is the real flasher's, so nothing here can drift out of
  step with what flashing actually checks - and only that one knows what
  is on the USB bus;
- the outcome is *shared*. A flash started from `test neopixels` shows
  its progress on `test sensors` too, which is right: there is one board,
  and two pages claiming private knowledge of it would be a lie about the
  hardware.

`in sync` is drawn beside the presses because it is the reading that says
whether pressing is necessary, and it is the one this node exists to put
in front of somebody who is about to press start on a test.
"""
from colloquy.base import Base
from colloquy.drivers.arduino import firmware
from colloquy.ui import leaves


class ColloquyFirmware(Base):
    """`flash firmware` on a test's page, pointing at the one flasher."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self["compile only"] = self.compile_only
        self["flash the board"] = self.flash

    @property
    def name(self):
        return "flash firmware"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def drivers(self):
        return self.owner.drivers

    @property
    def arduino(self):
        return self.drivers.arduino

    @property
    def flasher(self):
        return self.arduino.flasher

    # --- the two presses --------------------------------------------------

    def compile_only(self, request=None):
        """Build the sketch without touching the board.

        Forwarded rather than reimplemented, like everything else here.
        """
        return self.flasher.compile_only()

    def flash(self, request=None):
        """Put this repo's sketch on the installation's board.

        **It delegates rather than deciding.** The flasher already knows
        every reason not to flash - an unmounted PCB, an unchosen port, a
        port this machine does not have, a port that is not a plausible
        Arduino, anything under `drivers` or `tests` still running - and
        every one of those refusals is instant and reads last-known
        state. Restating any of them here would be eleven copies to
        drift, and weaker ones: only the flasher knows what is on the USB
        bus. So this returns the flasher's own sentence, whichever it is.

        The last of those refusals catches the test this hangs on if it
        is still running, which is right rather than awkward: the board
        spends twenty seconds in its bootloader answering nothing, and a
        female mid-pattern-read would simply see darkness.
        """
        return self.flasher.flash()

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        # Both always offered, neither hidden behind a check. The
        # flasher answers a press it will not act on with the reason, in
        # the same request - and a link that vanished exactly when the
        # board was in the state that needs it would be the wrong way
        # round. (Its own page hides the flash link instead, which is
        # right there: that page is about flashing and this one is not.)
        return {
            "compile only": self.compile_only,
            "flash the board": self.flash,
        }

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf("sketch", firmware.SKETCH_PATH.parent.name)
        leaf(
            "would flash",
            f"firmware {firmware.sketch_firmware_version()} "
            f"at {firmware.sketch_baudrate()} baud",
        )
        leaf("board says", firmware.describe(self.arduino.greeting))

        # The reading this node exists to put in front of somebody about
        # to press start on the test above it.
        problems = self.arduino.problems
        leaf("in sync", "yes" if not problems else "NO")
        for number, problem in enumerate(problems, start=1):
            leaf(f"problem {number}", problem)

        refusal = self.flasher._why_not_flash()
        leaf("can flash", "yes" if refusal is None else f"no - {refusal}")

        if self.flasher.is_started:
            leaf("flashing", "in progress - refresh in a moment")
        if self.flasher.outcome is not None:
            # Shared with every other test that draws this node, and with
            # `drivers > arduino > flash firmware`. One board, one answer.
            leaf("last flash", self.flasher.outcome)
        return states


class NeedsColloquyFirmware:
    """A mixin for a test that cannot work against the wrong sketch.

    Adds one child, `flash firmware`, and nothing else - the test's own
    page is already full of its own readings, and what somebody wants
    here is one door rather than six more lines.

    Hung by the test's own `snapshot_children` through `_with_firmware`
    rather than folded in centrally, for exactly the reason
    `BaseThread._with_scenarios` gives: `snapshot_children` is the tree's
    whole routing contract, so a child added to the rendered states and
    not to that dict draws as a link that 404s.

    Built on first use rather than in a constructor, so that adding this
    to a test is one word in the class line and one call in
    `snapshot_children`, with no `__init__` to touch.
    """

    _colloquy_firmware = None

    @property
    def firmware_node(self):
        if self._colloquy_firmware is None:
            self._colloquy_firmware = ColloquyFirmware(owner=self)
            self[self._colloquy_firmware.name] = self._colloquy_firmware
        return self._colloquy_firmware

    def _with_firmware(self, children):
        """This test's children, plus the way to fix its board."""
        node = self.firmware_node
        children[node.name] = node
        return children
