# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_startup_problems.py

"""Startup survives hardware that is not there, and says what to do.

Both crashes in `docs/errors/2026-08-27-01.txt` are pinned here: a board
running firmware 2, and a servo that did not answer. Each of them ended
the process, so the page that would have explained the fault and the
command that would have fixed it died with it.

`open_the_hardware()` is called against duck-typed doubles rather than a
real `Colloquy` (see conftest: never build the real object graph, never
start a thread). What is under test is which calls it keeps making after
one of them raises, and what ends up on the page.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# main.py sits at the repo root, beside "Source code", and is not
# importable as part of the colloquy package.
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from colloquy.drivers.arduino.errors import ArduinoError, FirmwareTooOld
from colloquy.startup import Startup

import main as entrypoint


class _Recorder(Startup):
    """The real node, minus the Base machinery it inherits a logger from."""

    def __init__(self):
        self._problems = []

    def log(self, message):
        pass


def make_colloquy(u2d2_raises=None, arduino_raises=None, dxl_raises=()):
    """A Colloquy-shaped double for open_the_hardware().

    `dxl_raises` names the bodies whose `init_hardware()` should fail, so
    a test can have exactly one servo refuse while the other five answer.
    """
    done = []

    def dxl(name):
        def init_hardware():
            done.append(f"init {name}")
            if name in dxl_raises:
                raise RuntimeError(f"{name} gave up after 5 attempts")

        return SimpleNamespace(name=f"dxl_{name}", init_hardware=init_hardware)

    def u2d2_open():
        done.append("u2d2 open")
        if u2d2_raises is not None:
            raise u2d2_raises

    def arduino_open():
        done.append("arduino open")
        if arduino_raises is not None:
            raise arduino_raises

    body_names = ("female1", "female2", "female3", "male1", "male2", "bar")
    drivers = SimpleNamespace(
        u2d2=SimpleNamespace(
            com_port=SimpleNamespace(set=lambda name: done.append(f"port {name}")),
            open=u2d2_open,
            body_dxls={name: dxl(name) for name in body_names},
        ),
        arduino=SimpleNamespace(open=arduino_open),
        neopixels=SimpleNamespace(
            turn_all_on=lambda: done.append("lights on"),
            turn_all_off=lambda: done.append("lights off"),
        ),
    )
    return SimpleNamespace(drivers=drivers, startup=_Recorder(), done=done)


@pytest.fixture(autouse=True)
def _no_sleeping(monkeypatch):
    """The blink is half a second of real time and says nothing here."""
    monkeypatch.setattr(entrypoint, "sleep", lambda seconds: None)


# --- the two crashes in the error log ------------------------------------


def test_an_old_sketch_does_not_stop_the_server_starting():
    fake = make_colloquy(
        arduino_raises=FirmwareTooOld(
            "Arduino on COM22: the board is running firmware 2, and this "
            "driver needs at least 3.",
            greeting={"firmware": 2},
        )
    )

    entrypoint.open_the_hardware(fake)

    assert fake.startup.has_problems
    (problem,) = fake.startup.problems
    assert "firmware 2" in problem.what


def test_an_old_sketch_is_answered_with_the_flasher_and_not_a_traceback():
    """The one startup failure with a remedy that is a link. It has to be
    the link and not only prose, because the whole point is that nobody
    has to leave the page to fix it."""
    fake = make_colloquy(
        arduino_raises=FirmwareTooOld("too old", greeting={"firmware": 2})
    )

    entrypoint.open_the_hardware(fake)

    (problem,) = fake.startup.problems
    assert problem.remedy_html is not None
    assert "/app/drivers/arduino/flash firmware" in problem.remedy_html


def test_a_servo_that_does_not_answer_does_not_stop_the_server_starting():
    fake = make_colloquy(dxl_raises=("female2",))

    entrypoint.open_the_hardware(fake)

    (problem,) = fake.startup.problems
    assert "female2" in problem.what
    # Named, so somebody knows which lead to look at. "dxl_2" is not an
    # answer to "which body is broken".
    assert "female2" in problem.remedy


def test_one_dead_servo_does_not_cost_the_other_five():
    """It used to: the loop was unguarded, so the first servo that did not
    answer ended the process before the rest had been touched."""
    fake = make_colloquy(dxl_raises=("female1",))

    entrypoint.open_the_hardware(fake)

    for name in ("female2", "female3", "male1", "male2", "bar"):
        assert f"init {name}" in fake.done


# --- the mirrors, which is what actually failed on 27 August --------------


def test_the_mirrors_are_not_woken_at_startup():
    """`Mirror`'s own docstring: nothing may enable torque on one until
    somebody asks by hand. Startup iterated all nine servos anyway, so an
    unwired mirror took the process down on the first write it ignored.

    Pinned on `body_dxls` being what is iterated - a mirror is not in it,
    so a mirror cannot be initialised here however it is wired.
    """
    fake = make_colloquy()

    entrypoint.open_the_hardware(fake)

    assert not any("mirror" in step for step in fake.done)
    assert len([step for step in fake.done if step.startswith("init ")]) == 6


# --- the halves are independent ------------------------------------------


def test_a_dead_arduino_does_not_cost_the_servos():
    fake = make_colloquy(arduino_raises=ArduinoError("the lead is out"))

    entrypoint.open_the_hardware(fake)

    assert "init bar" in fake.done


def test_a_dead_servo_bus_does_not_cost_the_lights():
    fake = make_colloquy(u2d2_raises=RuntimeError("COM4 is not there"))

    entrypoint.open_the_hardware(fake)

    assert "lights on" in fake.done
    assert "lights off" in fake.done


def test_a_dead_servo_bus_is_not_then_asked_for_servos():
    """Every one of the six would raise the same way, which is six copies
    of one fact on the page."""
    fake = make_colloquy(u2d2_raises=RuntimeError("COM4 is not there"))

    entrypoint.open_the_hardware(fake)

    assert not any(step.startswith("init ") for step in fake.done)
    (problem,) = fake.startup.problems
    assert "COM4" in problem.what


def test_a_clean_start_reports_nothing():
    fake = make_colloquy()

    entrypoint.open_the_hardware(fake)

    assert not fake.startup.has_problems
    assert fake.done[-1] == "lights off"


# --- what the page does with it ------------------------------------------


def test_every_problem_says_what_it_means_and_what_to_do():
    """A fault without a remedy sends somebody to read a traceback in a
    log, which is what this node exists to replace."""
    fake = make_colloquy(
        u2d2_raises=RuntimeError("COM4 is not there"),
        arduino_raises=ArduinoError("the lead is out"),
    )

    entrypoint.open_the_hardware(fake)

    assert len(fake.startup.problems) == 2
    for problem in fake.startup.problems:
        assert problem.means
        assert problem.remedy


def test_the_node_draws_a_line_per_part_of_every_problem():
    startup = _Recorder()
    startup.arduino_firmware_is_old(
        FirmwareTooOld("too old", greeting={"firmware": 2})
    )
    startup.servo_failed("bar", SimpleNamespace(name="dxl_9"), RuntimeError("silent"))

    states = Startup._snapshot_if_opened(startup, ("app", "startup problems"))

    assert "arduino firmware" in states
    assert "servo bar: what that means" in states
    assert "servo bar: what to do" in states
    # The flasher offer is markup, since it carries an anchor into the
    # tree; the servo one is a plain reading.
    assert "html" in states["arduino firmware: what to do"]
    assert "value" in states["servo bar: what to do"]
