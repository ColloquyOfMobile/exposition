# -*- coding: utf-8 -*-
# Source code/Python/colloquy/server2/remedies.py

"""What to do about a command that failed, where the page can say.

A command on the tree can fail for any reason at all, and most of them the
page has nothing useful to add to: the error text is what there is. These
are the two it does have something to add to, and both were found the same
way - somebody clicked a thing at a bench and got a traceback naming a
Windows error code.

The rule for adding one: only where the *next click* is knowable. "The
board is running firmware 3" has a next click, and it is `flash firmware`.
"COM5 does not exist" has one too, and it is the picker on the node that
remembers COM5 - so the remedy is to say what this machine does have.
Anything else belongs in the error message, not here, and a remedy that
guessed would send somebody the wrong way with more confidence than the
raw exception did.

Installation-side only. The mock's server draws the same page without
this: nothing is plugged into the mock, so a sentence about which COM
ports exist would be fiction there. See colloquy/ui/wsgi.py.
"""
import serial

from colloquy.drivers.arduino import boards
from colloquy.drivers.arduino.errors import FirmwareTooOld, flash_firmware_offer_html


def remedy_html(error):
    """The way out of `error`, as HTML, or None if there is not one.

    None is the ordinary answer and not a failure: most commands that
    raise have said everything there is to say in the message.
    """
    if isinstance(error, FirmwareTooOld):
        return flash_firmware_offer_html()

    if isinstance(error, serial.SerialException):
        return _serial_port_html()

    return None


def _serial_port_html():
    """A port that would not open - so say which ones are there.

    pyserial's own answer is a Windows error code about a file name, which
    is true and useless: the port was remembered in params.json by some
    earlier run, and what the reader needs is the list to pick from
    instead. `boards.detect()` names each lead by the chip bridging it to
    USB, which is what tells the servo bus from the Arduino when the
    numbers have moved (see drivers/arduino/boards.py).
    """
    found = boards.detect()
    if not found:
        return (
            "<p>This machine has <strong>no serial ports at all</strong> "
            "right now. Is the USB lead in?</p>"
        )
    listed = "".join(f"<li>{board.label}</li>" for board in found)
    return (
        "<p>The port was remembered from an earlier run and is not on this "
        "machine now. What is:</p>"
        f"<ul>{listed}</ul>"
        "<p>Pick one under the node's own <strong>com port</strong>.</p>"
    )
