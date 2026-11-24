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
    assert sketch.firmware_version() == 2
    assert sketch.board_name() == "teensy41"
    assert sketch.blink_fast_seconds() == 5
    assert sketch.chase_seconds() == 7


def test_the_tone_pins_are_the_adapters_copper():
    """Slot n's pin in the sketch is the pin the adapter routes, through its
    translator, to body n's tone net - and so to the backplane's TONE n LED."""
    from colloquy.hardware.electronics import shields_pinout

    _, outputs = shields_pinout.connections()
    copper = {row["signal"]: int(row["teensy"]) for row in outputs if row["kind"] == "tone"}

    assert sketch.tone_pins() == tuple(
        copper[body + "/tone"] for body in shields_pinout.BODIES
    )


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

    def __init__(self, firmware=2, corrupt_echo=False):
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
        elif command == "l":
            self.replies.append("tone leds")

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
        _tones_at=None,
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
    assert port.sent[-2:] == ["b", "l"]
    assert fake._blinked_at is not None
    assert fake._tones_at is not None


def test_a_board_that_does_not_answer_stops_after_the_first_check():
    fake = runner()
    port = FakeTeensyPort(firmware=0)

    TeensyTest._run_checks(fake, port)

    assert len(fake._checks) == 1
    assert fake._outcome.startswith("FAILED")
    assert "b" not in port.sent
    assert "l" not in port.sent


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
    params = {"teensy": {"communication port": None, "first run done": {}}, "arduino": {"arduino-cli": None}}
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
    assert states["tone leds"]["value"] == "not checked yet"
    assert "MEGA 5V lit" in states["backplane power leds"]["value"]
    assert "the LED blinked" not in node.snapshot_children
    assert "hold TONE 1" not in node.snapshot_children
    assert node.ask_the_board().startswith("refused")
    assert node.light_the_tone_leds().startswith("refused")


def test_after_the_chase_the_person_answers_and_can_hold_a_slot(monkeypatch):
    node, _ = built_node(monkeypatch)
    sent = []

    def send(command, expected):
        sent.append(command)
        return None

    node._send = send

    assert "TONE 1 to TONE 5" in node.light_the_tone_leds()
    children = node.snapshot_children
    for key in ("the tone LEDs lit 1 to 5", "a tone LED stayed dark", "hold TONE 5"):
        assert key in children

    assert "U1 drives TONE 1-4" in node["a tone LED stayed dark"]()
    assert "Teensy pin 28" in node["hold TONE 5"]()
    assert sent == ["l", "l 5"]
    states = node._snapshot_if_opened(())
    assert "TONE 5 alone" in states["held"]["value"]


def test_the_picker_offers_no_stand_in(monkeypatch):
    teensy = boards.identify(port_info(0x16C0, 0x0483, device="COM5"))
    node, params = built_node(monkeypatch, ports=[teensy])

    assert node.com_port.ports == ["COM5"]
    node.com_port.set(com_port="COM5")

    assert params["teensy"]["communication port"] == "COM5"
    assert node._why_not_open() is None


# --- before the first run ------------------------------------------------

from colloquy.tests.test_teensy import first_run  # noqa: E402


def step_readings(node):
    states = node._snapshot_if_opened(())
    return {
        key: value["value"]
        for key, value in states.items()
        if key.startswith("before the first run")
    }


def test_every_step_is_shown_with_its_done_link_until_pressed(monkeypatch):
    node, _ = built_node(monkeypatch)

    assert len(step_readings(node)) == len(first_run.STEPS)
    for key in first_run.KEYS:
        assert first_run.done_link(key) in node.snapshot_children
    assert "show the first-run steps again" not in node.snapshot_children


def test_a_step_marked_done_stays_a_moment_then_hides(monkeypatch):
    node, params = built_node(monkeypatch)
    key = first_run.KEYS[0]

    node[first_run.done_link(key)]()

    assert key in params["teensy"]["first run done"]
    shown = step_readings(node)
    assert any("hides in" in text for text in shown.values())
    assert first_run.done_link(key) not in node.snapshot_children

    # Pressed long enough ago: gone, and the way back is offered.
    params["teensy"]["first run done"][key] -= first_run.HIDE_AFTER + 1
    assert len(step_readings(node)) == len(first_run.STEPS) - 1
    assert "show the first-run steps again" in node.snapshot_children

    node["show the first-run steps again"]()
    assert len(step_readings(node)) == len(first_run.STEPS)


def test_hand_edited_nonsense_counts_as_not_done(monkeypatch):
    node, params = built_node(monkeypatch)
    params["teensy"]["first run done"] = {first_run.KEYS[0]: "yesterday"}

    assert len(step_readings(node)) == len(first_run.STEPS)
    params["teensy"]["first run done"] = "garbage"
    assert len(step_readings(node)) == len(first_run.STEPS)
