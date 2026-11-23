"""`test teensy`: the sketch it flashes, the checks it makes, and the
Teensy rows in the USB table.

Per conftest: nothing is started and no port is opened. The sketch is read
for real; the node's methods are called unbound against doubles.
"""
from threading import Event
from time import monotonic
from types import SimpleNamespace

from colloquy.drivers.arduino import boards
from colloquy.tests.test_teensy import TeensyFlasher, checks, sketch
from colloquy.tests.test_teensy import TestTeensy as TeensyTest


# --- the sketch ----------------------------------------------------------


def test_the_sketch_is_read_out_of_the_ino():
    assert sketch.SKETCH_PATH.is_file()
    assert sketch.firmware_version() == 1
    assert sketch.board_name() == "teensy41"
    assert sketch.blink_fast_seconds() == 5


def test_a_status_line_is_parsed():
    line = (
        "teensy_check firmware=1 board=teensy41 f_cpu=600000000 "
        "uptime_ms=1234 temp_c=41.3 led=heartbeat"
    )
    fields = sketch.parse_status(line)

    assert fields["firmware"] == "1"
    assert sketch.number(fields, "temp_c") == 41.3
    assert sketch.number(fields, "missing") is None


def test_anything_else_is_not_a_status_line():
    assert sketch.parse_status("") is None
    assert sketch.parse_status("microphone_sampler firmware=2") is None
    assert sketch.parse_status("error commands: ? | e <text> | b") is None


# --- the checks ----------------------------------------------------------


def test_a_board_running_something_else_fails_the_first_check():
    check = checks.answers(None, 1, "teensy41")

    assert not check.passed
    assert "flash" in check.said


def test_an_old_version_fails_and_says_which():
    check = checks.answers({"firmware": "0", "board": "teensy41"}, 1, "teensy41")

    assert not check.passed
    assert "firmware 0" in check.said


def test_a_lost_echo_fails():
    assert not checks.echo(100, 99, [1.0] * 100).passed
    assert checks.echo(100, 100, [1.0] * 100).passed


def test_a_clock_that_runs_fast_fails():
    assert checks.clock_keeps_time(1000, 1005).passed
    assert not checks.clock_keeps_time(1500, 1000).passed


def test_a_nonsense_temperature_fails():
    assert checks.temperature(45.0).passed
    assert not checks.temperature(-200.0).passed
    assert not checks.temperature(None).passed


def test_an_unusual_clock_speed_is_noted_not_failed():
    check = checks.clock_speed(816e6)

    assert check.passed
    assert "not the 600 MHz default" in check.said


# --- the run, against a pretend Teensy -----------------------------------


class FakeTeensyPort:
    """Answers the way teensy_check does, a line per line."""

    def __init__(self, firmware=1, corrupt_echo=False):
        self.firmware = firmware
        self.corrupt_echo = corrupt_echo
        self.replies = []
        self.sent = []

    def write(self, data):
        command = data.decode().strip()
        self.sent.append(command)
        if command == "?":
            self.replies.append(
                f"teensy_check firmware={self.firmware} board=teensy41 "
                f"f_cpu=600000000 uptime_ms={int(monotonic() * 1000)} temp_c=42.0 led=heartbeat"
            )
        elif command.startswith("e "):
            self.replies.append(command + ("x" if self.corrupt_echo else ""))
        elif command == "b":
            self.replies.append("blink fast")

    def readline(self):
        return (self.replies.pop(0) + "\r\n").encode() if self.replies else b""


def runner():
    fake = SimpleNamespace(
        _stop_event=Event(),
        _ask=TeensyTest._ask,
        _status=None,
        _status_line=None,
        _checks=[],
        _outcome=None,
        _blinked_at=None,
    )
    fake._read_status = lambda handler: TeensyTest._read_status(fake, handler)
    return fake


def test_a_good_teensy_passes_and_is_left_blinking():
    fake = runner()
    port = FakeTeensyPort()

    TeensyTest._run_checks(fake, port)

    assert [check.name for check in fake._checks] == [
        "answers",
        "cpu clock",
        "die temperature",
        "usb echo",
        "clock keeps time",
    ]
    assert all(check.passed for check in fake._checks), fake._checks
    assert port.sent[-1] == "b"
    assert fake._blinked_at is not None


def test_a_board_that_does_not_answer_stops_after_the_first_check():
    fake = runner()
    port = FakeTeensyPort(firmware=0)

    TeensyTest._run_checks(fake, port)

    assert len(fake._checks) == 1
    assert fake._outcome.startswith("FAILED")
    assert "b" not in port.sent


def test_a_corrupted_echo_is_caught():
    fake = runner()

    TeensyTest._run_checks(fake, FakeTeensyPort(corrupt_echo=True))

    echo = next(c for c in fake._checks if c.name == "usb echo")
    assert not echo.passed


# --- the USB table and the flasher ---------------------------------------


def port_info(vid, pid, device="COM9"):
    return SimpleNamespace(device=device, vid=vid, pid=pid, description="x", serial_number=None)


def test_a_teensy_is_named_and_kept_off_the_arduino_picker():
    board = boards.identify(port_info(0x16C0, 0x0483))

    assert board.is_teensy
    assert not board.is_arduino
    assert "Teensy" in board.name


def test_a_mega_is_not_a_teensy():
    assert not boards.identify(port_info(0x2341, 0x0042)).is_teensy


def test_the_flasher_wants_a_teensy_and_nothing_else():
    teensy = boards.identify(port_info(0x16C0, 0x0483))
    mega = boards.identify(port_info(0x2341, 0x0042))
    u2d2 = boards.identify(port_info(0x0403, 0x6014))

    assert TeensyFlasher._wrong_kind_of_board(None, teensy) is None
    assert "not a Teensy" in TeensyFlasher._wrong_kind_of_board(None, mega)
    assert "not a Teensy" in TeensyFlasher._wrong_kind_of_board(None, u2d2)


def test_the_flasher_compiles_for_the_teensy_core():
    assert TeensyFlasher.fqbn.fget(None) == "teensy:avr:teensy41"
    assert TeensyFlasher.sketch_folder.fget(None) == sketch.SKETCH_FOLDER


# --- the page ------------------------------------------------------------


def built_node(monkeypatch, ports=()):
    from pathlib import Path

    monkeypatch.setattr(boards, "detect", lambda ports_=None: list(ports))
    params = {"teensy": {"communication port": None}, "arduino": {"arduino-cli": None}}
    owner = SimpleNamespace(
        colloquy=SimpleNamespace(params=params),
        params=params,
        owners=[],
        name="manual tests",
        path=Path("tests/manual tests"),
        is_simulated=True,
    )
    return TeensyTest(owner=owner), params


def test_the_page_renders_with_nothing_plugged_in(monkeypatch):
    node, _ = built_node(monkeypatch)

    states = node._snapshot_if_opened(())

    assert "no port chosen" in states["can talk"]["value"]
    assert states["led"]["value"] == "not checked yet"
    assert "the LED blinked" not in node.snapshot_children
    assert node.ask_the_board().startswith("refused")


def test_the_picker_offers_no_stand_in(monkeypatch):
    teensy = boards.identify(port_info(0x16C0, 0x0483, device="COM5"))
    node, params = built_node(monkeypatch, ports=[teensy])

    assert node.com_port.ports == ["COM5"]
    node.com_port.set(com_port="COM5")

    assert params["teensy"]["communication port"] == "COM5"
    assert node._why_not_open() is None
