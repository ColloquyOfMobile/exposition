# -*- coding: utf-8 -*-
# Source code/Python/colloquy/server2/remedies.py

"""What to do about a command that failed, where the page can say.

A command on the tree can fail for any reason at all, and most of them the
page has nothing useful to add to: the error text is what there is. These
are the ones it does have something to add to, and each was found the same
way - somebody clicked a thing at a bench and got a traceback naming a
Windows error code.

The rule for adding one: only where the *next click* is knowable. "The
board is running firmware 3" has a next click, and it is `flash firmware`.
Anything else belongs in the error message, not here.

**And only say what has been checked.** The first version of the serial
remedy told every `SerialException` that its port "is not on this machine
now" - which it never looked at. `docs/errors/2026-08-28-01.txt` is that
sentence printed under a `WriteFile failed` on a port that was plainly
present, next to a listing showing an Arduino Mega on the bus. A remedy
that guesses is worse than no remedy: it is the raw exception plus a
confident wrong sentence, and somebody goes and re-picks a port that was
never the problem.

So the serial remedy now branches on the *shape* of the failure, which
the message does say, and checks the bus before claiming anything about
it.

Installation-side only. The mock's server draws the same page without
this: nothing is plugged into the mock, so a sentence about which COM
ports exist would be fiction there. See colloquy/ui/wsgi.py.
"""
import re

import serial

from colloquy.drivers.arduino import boards
from colloquy.drivers.arduino.errors import FirmwareTooOld, flash_firmware_offer_html

# pyserial names the port when an *open* fails ("could not open port
# 'COM5': ..."). It does not when a read or a write fails on a handle it
# already had, which is the difference this file turns on.
_PORT_IN_MESSAGE = re.compile(r"port '([^']+)'")


def remedy_html(error):
    """The way out of `error`, as HTML, or None if there is not one.

    None is the ordinary answer and not a failure: most commands that
    raise have said everything there is to say in the message.
    """
    if isinstance(error, FirmwareTooOld):
        return flash_firmware_offer_html()

    if isinstance(error, serial.SerialException):
        return _serial_port_html(error)

    return None


def _bus_html(found):
    listed = "".join(f"<li>{board.label}</li>" for board in found)
    return f"<p>What is on the USB bus now:</p><ul>{listed}</ul>"


def _serial_port_html(error):
    """A serial failure - so say what is actually on the bus, and which
    of the two failures this was.

    The two are not the same problem and do not have the same next click.
    A port that would not *open* is usually a name remembered from an
    earlier run. A port that stopped answering *mid-transfer* was open and
    working a moment ago, and something took it away - which on this board
    means power before it means anything else, since the whole audio
    subsystem hangs off the same 5 V (see `hardware > electronics > dirty
    rework`, section 4d).
    """
    found = boards.detect()
    if not found:
        return (
            "<p>This machine has <strong>no serial ports at all</strong> "
            "right now, so whatever was on the other end has gone. Check "
            "the USB lead, and the supply if the board is powered from "
            "anything but the lead.</p>"
        )

    named = _PORT_IN_MESSAGE.search(str(error))
    if named is None:
        # A read or a write on a handle that was already open. The link
        # was working and stopped, which is a different sentence from the
        # one below and used to get the wrong one.
        return (
            "<p>The link was open and stopped answering part way through, "
            "so this is not a port that was never there. Something took "
            "the board away mid-transfer: its supply browning out, the "
            "lead, or a reset.</p>"
            "<p><strong>A board that resets comes back at a new COM "
            "number</strong>, so check the list below against the port "
            "this node is set to before reopening it.</p>"
            + _bus_html(found)
            + "<p>Then <strong>open port</strong> under "
            "<code>drivers &gt; arduino</code>, or pick it again under "
            "that node's own <strong>com port</strong>.</p>"
        )

    port = named.group(1)
    devices = {board.device for board in found}
    if port in devices:
        # It is there and it would not open: something else has it.
        return (
            f"<p><strong>{port} is on this machine</strong>, so the name "
            "is right and something else is holding it - another copy of "
            "this app, a serial monitor, or the Arduino IDE. Close that "
            "and try again.</p>" + _bus_html(found)
        )

    return (
        f"<p><strong>{port} is not on this machine now.</strong> It was "
        "remembered from an earlier run, and a board that has been "
        "replugged or has reset comes back at a different number.</p>"
        + _bus_html(found)
        + "<p>Pick one under the node's own <strong>com port</strong>.</p>"
    )
