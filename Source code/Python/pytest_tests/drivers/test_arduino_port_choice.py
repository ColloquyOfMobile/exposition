# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/drivers/test_arduino_port_choice.py

"""Which lead the Arduino opens, and therefore whether anything is real.

The question this file pins came apart on 2026-08-28, when the main PCB
was carried off the installation and onto the bench to be debugged. Two
questions had been one:

- **is the piece simulated here** - `is_simulated`, a fact about the
  computer, and true everywhere but the installation;
- **is there an Arduino on the end of this lead** - a fact about the lead,
  and true wherever somebody has plugged the board in.

The bench answers the first yes and the second yes as well, and while the
Arduino asked only the first one it opened the stand-in: every tone
reported "sounding", every microphone reported a band rising, and the real
Mega sat on the desk beside it. A stand-in run passes every check, which
is what makes this worth a file of its own rather than a line in
test_arduino_link.py.

So the picker lists the real leads wherever there are any, and the handler
follows the lead that was chosen. Nothing about the installation changes:
there `is_simulated` is False, there is no stand-in to offer, and the lead
chosen is a real one either way.
"""
from types import SimpleNamespace

import pytest

from colloquy.drivers.arduino import Arduino, boards
from colloquy.drivers.arduino.com_port import ComPort
from colloquy.drivers.com_port import SIMULATED_ARDUINO_PORT

INSTALLATION_HOSTNAME = "Colloquy-Laptop"
BENCH_HOSTNAME = "DESKTOP-MRSLS88"

MEGA = boards.Board(
    device="COM7",
    name="Arduino Mega 2560 (R3)",
    is_arduino=True,
    vid=0x2341,
    pid=0x0042,
    serial_number="A1",
)
U2D2 = boards.Board(
    device="COM4",
    name="FTDI FT232R - the U2D2 is an FTDI device",
    is_arduino=False,
    vid=0x0403,
    pid=0x6001,
    serial_number="B2",
)


@pytest.fixture
def on_the_bus(monkeypatch):
    """What `boards.detect()` finds, for this test."""

    def set(*found):
        monkeypatch.setattr(boards, "detect", lambda ports=None: list(found))

    return set


@pytest.fixture
def hostname(monkeypatch):
    def set(name):
        monkeypatch.setattr("colloquy.machines.socket.gethostname", lambda: name)

    return set


def picker(stub_factory):
    return ComPort(owner=stub_factory())


# --- what the picker offers ----------------------------------------------


def test_the_bench_is_offered_the_real_lead_as_well_as_the_stand_in(
    stub_factory, hostname, on_the_bus
):
    """The whole point. The bench is `is_simulated` and the board is
    nonetheless plugged into it."""
    hostname(BENCH_HOSTNAME)
    on_the_bus(MEGA, U2D2)

    offered = picker(stub_factory).ports

    assert offered == [MEGA.label, U2D2.label, SIMULATED_ARDUINO_PORT]


def test_the_stand_in_comes_last(stub_factory, hostname, on_the_bus):
    """On a machine with a board on it, the board is the answer."""
    hostname(BENCH_HOSTNAME)
    on_the_bus(MEGA)

    assert picker(stub_factory).ports[-1] == SIMULATED_ARDUINO_PORT


def test_a_machine_with_no_board_still_gets_the_stand_in(
    stub_factory, hostname, on_the_bus
):
    """CI and the other dev machine, where it is the only port there is."""
    hostname("some-laptop")
    on_the_bus()

    assert picker(stub_factory).ports == [SIMULATED_ARDUINO_PORT]


def test_the_installation_is_never_offered_the_stand_in(
    stub_factory, hostname, on_the_bus
):
    """Unchanged, and the half that must stay unchanged: the one machine
    that drives the piece has no business opening a fake port."""
    hostname(INSTALLATION_HOSTNAME)
    on_the_bus(MEGA, U2D2)

    assert picker(stub_factory).ports == [MEGA.label, U2D2.label]


def test_the_leads_are_named_by_their_chip_not_only_their_number(
    stub_factory, hostname, on_the_bus
):
    """boards.py's whole reason: COM4 and COM7 do not say which one is the
    servo bus, and Windows renumbers them."""
    hostname(BENCH_HOSTNAME)
    on_the_bus(MEGA, U2D2)

    offered = picker(stub_factory).ports

    assert "Mega" in offered[0]
    assert "U2D2" in offered[1]


def test_choosing_a_lead_writes_it_down_before_pointing_the_link_at_it(
    stub_factory, hostname, on_the_bus
):
    """Order, not tidiness. Which handler is the right one is read out of
    params, so a `use_port` called first would build one for the lead
    being replaced."""
    hostname(BENCH_HOSTNAME)
    on_the_bus(MEGA)
    seen = []
    params = {"arduino": {"communication port": SIMULATED_ARDUINO_PORT}}
    node = picker(stub_factory)
    node._owner = SimpleNamespace(
        params=params,
        use_port=lambda name: seen.append(params["arduino"]["communication port"]),
    )

    node.set(MEGA.device)

    assert params["arduino"]["communication port"] == MEGA.device
    assert seen == [MEGA.device]


# --- and which handler that lead gets ------------------------------------


class FakeSerial:
    """Enough pyserial to be built and named, never opened."""

    def __init__(self, baudrate=None, timeout=None):
        self.baudrate = baudrate
        self.timeout = timeout
        self.port = None
        self.is_open = False
        self.closed = 0

    def close(self):
        self.is_open = False
        self.closed += 1


@pytest.fixture
def fake_serial(monkeypatch):
    monkeypatch.setattr("serial.Serial", FakeSerial)
    return FakeSerial


class FakeArduino:
    """The double `port_handler` and `use_port` are called against.

    A class rather than a SimpleNamespace because the one thing under test
    has to stay *live*: `is_using_the_stand_in` reads the port out of
    params every time it is asked, and these tests change the port and ask
    again. It is the real property, so what it answers is not a second
    opinion about the rule.
    """

    is_using_the_stand_in = Arduino.is_using_the_stand_in
    port_handler = Arduino.port_handler

    def __init__(self, port, stand_in=None):
        self._port_handler = None
        self._handler_is_the_stand_in = None
        self.baudrate = 1000000
        self.params = {"arduino": {"communication port": port}}
        self.colloquy = SimpleNamespace(
            virtual_drivers=SimpleNamespace(
                arduino_serial_port=(
                    stand_in if stand_in is not None else FakeSerial()
                )
            )
        )


def fake_arduino(port, stand_in=None):
    return FakeArduino(port, stand_in=stand_in)


def is_using_the_stand_in(fake):
    return Arduino.is_using_the_stand_in.fget(fake)


def port_handler(fake):
    return Arduino.port_handler.fget(fake)


def test_the_lead_decides_and_not_the_machine(hostname):
    """Read straight off the port name, so it says the same thing on every
    computer - which is the point of moving the question here."""
    for host in (INSTALLATION_HOSTNAME, BENCH_HOSTNAME, "some-laptop"):
        hostname(host)
        assert is_using_the_stand_in(fake_arduino(SIMULATED_ARDUINO_PORT)) is True
        assert is_using_the_stand_in(fake_arduino("COM7")) is False


def test_a_real_lead_gets_a_real_serial_port(fake_serial):
    fake = fake_arduino("COM7")

    handler = port_handler(fake)

    assert isinstance(handler, FakeSerial)
    assert handler.port == "COM7"
    assert handler.baudrate == 1000000
    assert fake._handler_is_the_stand_in is False


def test_the_stand_in_lead_gets_the_virtual_serial_port(fake_serial):
    stand_in = FakeSerial()
    fake = fake_arduino(SIMULATED_ARDUINO_PORT, stand_in=stand_in)

    handler = port_handler(fake)

    assert handler is stand_in
    assert fake._handler_is_the_stand_in is True


def test_moving_from_the_stand_in_to_a_board_replaces_the_handler(fake_serial):
    """They are different objects, so writing the new name onto the one in
    hand would leave the link pointed at the fake."""
    stand_in = FakeSerial()
    fake = fake_arduino(SIMULATED_ARDUINO_PORT, stand_in=stand_in)
    port_handler(fake)

    fake.params["arduino"]["communication port"] = "COM7"
    Arduino.use_port(fake, "COM7")

    assert fake._port_handler is not stand_in
    assert fake._port_handler.port == "COM7"
    assert fake._handler_is_the_stand_in is False


def test_the_replaced_handler_is_closed_before_it_is_dropped(fake_serial):
    """A discarded pyserial handle keeps the COM port open until the
    garbage collector reaches it, and the next open then fails saying the
    port is busy - which reads exactly like a board that is not there."""
    fake = fake_arduino("COM7")
    real = port_handler(fake)
    real.is_open = True

    fake.params["arduino"]["communication port"] = SIMULATED_ARDUINO_PORT
    Arduino.use_port(fake, SIMULATED_ARDUINO_PORT)

    assert real.closed == 1
    assert fake._port_handler is not real


def test_choosing_the_same_kind_of_lead_keeps_the_handler(fake_serial):
    """COM7 to COM8 is a rename, not a replacement - and dropping an open
    handler for one is how a working link gets closed under a command."""
    fake = fake_arduino("COM7")
    first = port_handler(fake)

    fake.params["arduino"]["communication port"] = "COM8"
    Arduino.use_port(fake, "COM8")

    assert fake._port_handler is first
    assert first.port == "COM8"
    assert first.closed == 0
