# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_link_problem_page.py

"""A board with the wrong sketch on it must not take the server down.

The traceback this was written after: the main PCB came to the bench, the
lead was chosen, `test audio bringup > hold male1` was clicked, and
`Arduino.open()` raised `FirmwareTooOld` - the board was still running
firmware 3, from before the voices changed hands on 2026-08-27. That
reached `Server2.wsgi`'s catch-all, which treats any unhandled exception
as a fault serious enough to emergency-stop the installation, so the
process set its shutdown event and left the server loop.

Which took `drivers > arduino > flash firmware` with it - the one page
that fixes exactly this. The same shape as the crash `colloquy/startup/`
was written for, one layer up: an installation that comes up unable to
move is worth more than one that does not come up, and a *running* one
that meets an old sketch is worth more than one that stops.

So it joins `NotImplementedError` as a second kind of failure the request
layer answers with a page. What earns it that: `Arduino.open()` raises
during the greeting, before a pixel, a tone or a servo has been asked for
anything, so nothing is in motion and nothing is half-written. The limit
is pinned below too - everything else still propagates.
"""
from pathlib import Path
import pytest

from colloquy.drivers.arduino.errors import (
    ArduinoError,
    FirmwareTooOld,
    flash_firmware_offer_html,
)
from colloquy.server2.wsgi2 import WSGI2

# What the driver actually said on the bench, kept verbatim: the version
# it found and the version it wants are the whole of what the reader
# needs, and they come from the board rather than from here.
MESSAGE = (
    "Arduino on COM6: the board is running firmware 3, and this driver "
    "needs at least 4. Flash colloquy_of_mobiles.ino (firmware 4) onto it."
)
COMMAND = ("tests", "test audio bringup", "call", "hold male1 (160 Hz, D11)")


class FakeWSGI:
    """The double `_parse_app` is called against.

    WSGI2 cannot be constructed here - it parses an environ and renders a
    whole page in __init__ - so this borrows the three methods under test
    and exposes only what they touch. Borrowed rather than re-implemented:
    what is being pinned is which failures those methods answer, and a
    hand-written copy would answer whatever this file expected.
    """

    _parse_app = WSGI2._parse_app
    _parse_not_found = WSGI2._parse_not_found
    _parse_link_problem = WSGI2._parse_link_problem

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


def wsgi(raises=None):
    return FakeWSGI(raises)


def page(fake, *args):
    status, headers, body = WSGI2._parse_app(fake, *args)
    return status, body.decode("utf-8")


# --- the fault the page answers ------------------------------------------


def test_an_old_sketch_is_a_page_and_not_a_crash():
    """The whole point: it returns rather than propagating, so
    Server2.wsgi's catch-all never sees it and never stops anything."""
    status, html = page(wsgi(FirmwareTooOld(MESSAGE, greeting={"firmware": 3})), *COMMAND)

    assert status == "200 OK"
    assert "The Arduino link is not usable." in html


def test_the_page_says_which_firmware_the_board_is_running():
    """Word for word what the driver said. One version behind and a board
    from another project entirely look the same without it."""
    _, html = page(wsgi(FirmwareTooOld(MESSAGE)), *COMMAND)

    assert "running firmware 3" in html
    assert "needs at least 4" in html


def test_the_page_carries_the_way_out():
    """A diagnosis with no remedy on it sends somebody to read a log."""
    _, html = page(wsgi(FirmwareTooOld(MESSAGE)), *COMMAND)

    assert '/app/drivers/arduino/flash firmware' in html


def test_the_offer_is_the_one_startup_makes():
    """Written once, in drivers/arduino/errors.py. Two offers pointing at
    two paths would send one of them nowhere."""
    from colloquy.startup import Startup

    startup = Startup.__new__(Startup)
    startup._problems = []
    # Base.log is a property over _log, and _add writes one line to it.
    startup._log = lambda *args, **kwargs: None
    Startup.arduino_firmware_is_old(
        startup, FirmwareTooOld(MESSAGE, greeting={"firmware": 3})
    )

    assert startup.problems[0].remedy_html == flash_firmware_offer_html()


def test_it_says_nothing_was_driven():
    """True of this failure specifically, and the reason it is allowed to
    be a page at all: open() raises out of the greeting, before anything
    has been asked to move or light up."""
    _, html = page(wsgi(FirmwareTooOld(MESSAGE)), *COMMAND)

    assert "Nothing was driven" in html


def test_back_points_at_the_node_and_not_at_the_command():
    """Everything from "call" on is the command - see ui/tree.py. A back
    link that kept it would re-run the thing that just failed, which on
    this node means opening the port again."""
    _, html = page(wsgi(FirmwareTooOld(MESSAGE)), *COMMAND)

    assert 'href="/app/tests/test audio bringup"' in html
    assert "hold male1" not in html


def test_a_link_that_is_broken_some_other_way_gets_the_page_without_the_offer():
    """A lead that is out, or a board talking at a rate nobody expected,
    is fixed by standing up - so there is nothing to link to."""
    _, html = page(wsgi(ArduinoError("Arduino on COM6 did not answer.")), *COMMAND)

    assert "did not answer" in html
    assert "flash firmware" not in html


# --- and the limit -------------------------------------------------------


def test_everything_else_still_reaches_the_emergency_stop():
    """The half that must not move. This page is for two named kinds of
    failure; an unknown one is still a crash, and a crash still stops the
    hardware because no thread is being supervised by anything else."""
    with pytest.raises(ZeroDivisionError):
        page(wsgi(ZeroDivisionError("something genuinely wrong")), *COMMAND)


def test_a_mistyped_path_is_still_a_404():
    """The kind that was already handled, unchanged by the new one beside
    it."""
    status, html = page(wsgi(NotImplementedError("no such key")), "nowhere")

    assert status == "404 Not Found"
    assert "no such path" in html


def test_the_fault_is_logged_even_though_it_is_answered():
    """It is still a fault. Somebody reading the log afterwards should
    find it there, not only in whichever browser tab met it."""
    fake = wsgi(FirmwareTooOld(MESSAGE))

    page(fake, *COMMAND)

    assert any("firmware 3" in line for line in fake.logged)
