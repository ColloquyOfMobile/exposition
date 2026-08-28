# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/arduino/errors.py

"""What can go wrong with the link, in kinds the page can act on.

Both are `RuntimeError`s, which is what `Arduino.open()` raised before
there were classes here - so every existing `except RuntimeError` still
catches them and nothing that was written against the old behaviour has
to change.

The split exists for one reason: **one of these failures has a remedy the
page can offer and the others do not.** A board running an old sketch is
fixed by `drivers > arduino > flash firmware`, without anybody leaving
the room or opening the Arduino IDE, so startup turns it into that offer
(`colloquy/startup/`). A lead that is out, or a board talking at a rate
nobody expected, is fixed by standing up - and telling the two apart by
matching on the prose of the message would break the first time somebody
reworded it.
"""


class ArduinoError(RuntimeError):
    """The link is not usable, and nothing that follows will work."""


class FirmwareTooOld(ArduinoError):
    """The board answered, and its sketch is older than this driver needs.

    Carries the greeting, so the page can say which firmware it found and
    not only which one it wanted. That difference is what tells somebody
    whether they are one version behind or looking at a board from a
    different project.
    """

    def __init__(self, message, greeting=None):
        super().__init__(message)
        self.greeting = greeting or {}

    @property
    def found_version(self):
        """What the board says it is running, or None if it did not say."""
        return self.greeting.get("firmware")


# Where a board with the wrong sketch on it gets fixed, and the offer to
# go there, written once. Two pages make this offer now - the startup
# report (`colloquy/startup/`) and a request that meets the fault while
# the installation is already running (`server2/wsgi2.py`) - and an offer
# that pointed at two different paths would send one of them nowhere.
FLASH_FIRMWARE_PATH = "/app/drivers/arduino/flash firmware"


def flash_firmware_offer_html():
    """The remedy for FirmwareTooOld, as the page offers it."""
    return (
        "<p>The board can be flashed from here - it compiles and "
        "uploads this repo's own sketch, and reopens the link "
        "afterwards so the board says in its own words which "
        "firmware it ends up with.</p>"
        f'<p><a href="{FLASH_FIRMWARE_PATH}">'
        "<strong>go to flash firmware</strong></a> "
        "(press <em>compile only</em> first if you have never "
        "flashed from this machine)</p>"
    )
