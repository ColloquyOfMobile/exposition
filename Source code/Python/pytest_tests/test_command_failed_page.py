# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_command_failed_page.py

"""A command that fails must not take the server down with it.

Two tracebacks, a day apart, both from a bench with the main PCB on it:

- `test audio bringup > hold male1` raised `FirmwareTooOld` - the board
  was still on firmware 3, from before the voices changed hands;
- `test audio subsystem > enable a` raised `SerialException: could not
  open port 'COM5'` - a COM number remembered from a run on another
  machine.

Both reached `Server2.wsgi`'s catch-all, which treats an unhandled
exception as a fault serious enough to emergency-stop the installation,
so the process set its shutdown event and left the server loop - taking
with it `flash firmware` and the port picker, which are the two pages
that fix them.

The first fix was a catch for `ArduinoError`, and the second traceback
showed why that is the wrong shape: the next one is a different type
again. So the walk says *that a command was what raised*
(`ui/tree.CommandFailed`) and the request layer answers any such failure
with a page.

**Why answering is safe.** The catch-all exists because an exception
kills the HTTP loop, and a running thread would then go on moving with no
page left to stop it. Answering keeps the loop, so the page is still
there - EMERGENCY STOP included - and the thing it protects against
cannot happen. The limit is pinned below: anything raised outside a
command still propagates.
"""
from pathlib import Path

import pytest
import serial

from colloquy.drivers.arduino.errors import (
    ArduinoError,
    FirmwareTooOld,
    flash_firmware_offer_html,
)
from colloquy.server2 import remedies
from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui import tree
from colloquy.ui.tree import CommandFailed

# What the two boards actually said, kept verbatim: the reader needs the
# version it found and the port it wanted, and both come from the
# hardware rather than from here.
FIRMWARE_MESSAGE = (
    "Arduino on COM6: the board is running firmware 3, and this driver "
    "needs at least 4. Flash colloquy_of_mobiles.ino (firmware 4) onto it."
)
SERIAL_MESSAGE = (
    "could not open port 'COM5': FileNotFoundError(2, 'Das System kann die "
    "angegebene Datei nicht finden.', None, 2)"
)
# The other shape, from docs/errors/2026-08-28-01.txt: a write on a handle
# that was already open, with no port named in it at all.
WRITE_MESSAGE = (
    "WriteFile failed (PermissionError(13, 'The device does not recognize "
    "the command.', None, 22))"
)
COMMAND = ("tests", "test audio bringup", "call", "hold male1 (160 Hz, D11)")
# What `get_focus` hands back: the "call" marker is consumed by the
# walk, so the leftovers are the command and its arguments.
CALLED = ("hold male1 (160 Hz, D11)",)


class FakeWSGI:
    """The double `_parse_app` is called against.

    WSGI2 cannot be constructed here - it parses an environ and renders a
    whole page in __init__ - so this borrows the three methods under test
    and exposes only what they touch. Borrowed rather than reimplemented:
    what is pinned is which failures those methods answer, and a copy
    would answer whatever this file expected of it.
    """

    _parse_app = WSGI2._parse_app
    _parse_not_found = WSGI2._parse_not_found
    _parse_command_failed = WSGI2._parse_command_failed

    def __init__(self, raises=None):
        self._raises = raises
        self._root = Path("app")
        self.logged = []

    def get_states(self, *args):
        if self._raises is not None:
            raise self._raises
        return {"path": args}

    def log(self, line):
        self.logged.append(line)


def page(raises, *args):
    args = args or COMMAND
    status, headers, body = FakeWSGI(raises)._parse_app(*args)
    return status, body.decode("utf-8")


def failure(error):
    return CommandFailed(CALLED, error)


@pytest.fixture(autouse=True)
def no_real_usb_bus(monkeypatch):
    """The serial remedy lists what is plugged in, and what is plugged
    into the machine running the tests is not the subject."""
    monkeypatch.setattr(
        remedies.boards,
        "detect",
        lambda ports=None: [
            remedies.boards.Board(
                device="COM6",
                name="Arduino Mega 2560 (R3)",
                is_arduino=True,
                vid=0x2341,
                pid=0x0042,
                serial_number="A1",
            )
        ],
    )


# --- the walk says what raised -------------------------------------------


def test_the_walk_marks_a_command_that_raised():
    """`get_states` both renders and calls, so once an exception is loose
    the request layer cannot tell which of the two it came out of."""

    class Root:
        @property
        def snapshot_children(self):
            return {}

        def snapshot(self, path, focus_path):
            return {"path": path, "boom": self.boom}

        def boom(self, *args):
            raise ZeroDivisionError("inside the command")

    with pytest.raises(CommandFailed) as raised:
        tree.get_states(Root(), "call", "boom")

    assert isinstance(raised.value.error, ZeroDivisionError)
    assert raised.value.command == ("boom",)


def test_a_missing_key_is_still_a_routing_miss_and_not_a_command_failure():
    """`update` raises NotImplementedError on a miss, which the page
    answers with a 404. Wrapping it would turn a mistyped link into a
    report of a hardware fault."""

    class Root:
        @property
        def snapshot_children(self):
            return {}

        def snapshot(self, path, focus_path):
            return {"path": path, "name": "root"}

    with pytest.raises(NotImplementedError):
        tree.get_states(Root(), "call", "nothing of the sort")


# --- and the page answers it ---------------------------------------------


def test_a_failed_command_is_a_page_and_not_a_crash():
    """The whole point: it returns, so Server2.wsgi's catch-all never sees
    it and never stops anything."""
    status, html = page(failure(FirmwareTooOld(FIRMWARE_MESSAGE)))

    assert status == "200 OK"
    assert "hold male1" in html


def test_the_page_says_what_actually_went_wrong():
    """Type and message both. "It failed" sends somebody to a log."""
    _, html = page(failure(FirmwareTooOld(FIRMWARE_MESSAGE)))

    assert "FirmwareTooOld" in html
    assert "running firmware 3" in html
    assert "needs at least 4" in html


def test_the_page_says_the_installation_is_still_running():
    """Because the previous behaviour was that it was not, and somebody
    who has seen that once will assume it again."""
    _, html = page(failure(ArduinoError("boom")))

    assert "nothing was stopped" in html


def test_back_points_at_the_node_and_not_at_the_command():
    """Everything from "call" on is the command - see ui/tree.py. A back
    link that kept it would re-run the thing that just failed."""
    _, html = page(failure(ArduinoError("boom")))

    assert 'href="/app/tests/test audio bringup"' in html


def test_the_fault_is_logged_even_though_it_is_answered():
    """It is still a fault. Somebody reading the log afterwards should
    find it there, not only in whichever browser tab met it."""
    fake = FakeWSGI(failure(FirmwareTooOld(FIRMWARE_MESSAGE)))

    fake._parse_app(*COMMAND)

    assert any("firmware 3" in line for line in fake.logged)


# --- the remedies, which are the "point me at the fix" half --------------


def test_an_old_sketch_is_offered_the_flasher():
    _, html = page(failure(FirmwareTooOld(FIRMWARE_MESSAGE)))

    assert "/app/drivers/arduino/flash firmware" in html


def test_the_offer_is_the_one_startup_makes():
    """Written once, in drivers/arduino/errors.py. Two offers pointing at
    two paths would send one of them nowhere."""
    from colloquy.startup import Startup

    startup = Startup.__new__(Startup)
    startup._problems = []
    # Base.log is a property over _log, and _add writes one line to it.
    startup._log = lambda *args, **kwargs: None
    Startup.arduino_firmware_is_old(
        startup, FirmwareTooOld(FIRMWARE_MESSAGE, greeting={"firmware": 3})
    )

    assert startup.problems[0].remedy_html == flash_firmware_offer_html()


def test_a_port_that_is_not_there_is_answered_with_the_ones_that_are():
    """pyserial's own answer is a Windows error code about a file name,
    which is true and useless. The port was remembered by an earlier run;
    what the reader needs is the list to pick from instead."""
    _, html = page(failure(serial.SerialException(SERIAL_MESSAGE)))

    assert "COM5" in html
    assert "Arduino Mega 2560 (R3)" in html
    assert "com port" in html


def test_a_link_that_dropped_mid_transfer_is_not_called_a_missing_port():
    """docs/errors/2026-08-28-01.txt, which is this remedy getting it
    wrong.

    A `WriteFile failed` is a handle that was open and working a moment
    ago. The first version of this told it "the port was remembered from
    an earlier run and is not on this machine now" - printed underneath a
    listing showing an Arduino Mega on the bus. That is the raw exception
    plus a confident wrong sentence, and it sends somebody to re-pick a
    port that was never the problem.
    """
    _, html = page(failure(serial.SerialException(WRITE_MESSAGE)))

    assert "not on this machine" not in html
    assert "stopped answering part way through" in html
    # And the thing that is actually worth knowing about this board.
    assert "supply" in html
    assert "comes back at a new COM number" in html


def test_a_dropped_link_still_lists_what_is_on_the_bus():
    """Because a board that reset is back at a different number, which is
    exactly what happened - COM6 became COM22."""
    _, html = page(failure(serial.SerialException(WRITE_MESSAGE)))

    assert "Arduino Mega 2560 (R3)" in html
    assert "open port" in html


def test_a_port_that_is_there_and_will_not_open_is_held_by_something_else():
    """The third shape, and the only one of the three where the port name
    is right and the machine is right."""
    _, html = page(
        failure(serial.SerialException("could not open port 'COM6': Access denied"))
    )

    assert "COM6 is on this machine" in html
    assert "something else is holding it" in html
    assert "not on this machine" not in html


def test_a_machine_with_nothing_plugged_in_says_so(monkeypatch):
    """An empty list drawn as an empty list reads like a rendering bug."""
    monkeypatch.setattr(remedies.boards, "detect", lambda ports=None: [])

    _, html = page(failure(serial.SerialException(SERIAL_MESSAGE)))

    assert "no serial ports at all" in html


def test_a_failure_nobody_has_a_next_click_for_gets_no_remedy():
    """A remedy that guessed would send somebody the wrong way with more
    confidence than the raw exception did."""
    assert remedies.remedy_html(ValueError("something else entirely")) is None


# --- and the limit -------------------------------------------------------


def test_something_raised_outside_a_command_still_stops_the_hardware():
    """The half that must not move. Out there the process really is
    somewhere nobody can describe, and no thread is supervised by
    anything else."""
    with pytest.raises(ZeroDivisionError):
        page(ZeroDivisionError("raised by the render, not by a command"))


def test_a_mistyped_path_is_still_a_404():
    """The kind that was already handled, unchanged by the one beside
    it."""
    status, html = page(NotImplementedError("no such key"), "nowhere")

    assert status == "404 Not Found"
    assert "no such path" in html
