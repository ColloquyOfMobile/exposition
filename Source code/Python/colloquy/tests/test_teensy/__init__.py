# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_teensy/__init__.py

"""Is the Teensy alive? Flash it, ask it, and look at its LED.

The first test of the shields design's step 2: a Teensy 4.1 on the
adapter plate, the plate on the backplane, and nothing else mounted or
wired. Its only lead is USB, so that is all this talks over.

**Three presses, in order.**

1. `com port` - pick the Teensy. Only real leads are offered (no
   stand-in, for the Goertzel ear's reason: a simulated Teensy answering
   "fine" is the one false confidence this exists against), and the list
   names each one by its USB ids, so a Teensy reads as a Teensy.
2. `flash firmware` - put `Source code/Arduino/teensy_check/` on it, with
   arduino-cli and PJRC's Teensy core (installed through the Arduino IDE's
   Boards Manager). It ends by asking the board, as every flasher here
   does.
3. `start` - one pass of checks, a second or so: the status line, the
   version, the clock speed, the die temperature, a hundred echoes over
   USB, and whether the board's clock keeps time with this computer's.
   Then it makes the LED flicker for five seconds, and **that is the half
   a person does**: look, and press `the LED blinked` or `the LED did not
   blink`. See `checks.py` for what each check can and cannot settle.

**A Teensy does not reboot when its port opens** (no DTR reset, unlike a
Mega), so nothing greets: the sketch is asked with `?` instead. And a
Teensy's COM port is the sketch's own - a board running a sketch built
without USB Type "Serial" has no COM port at all. If the picker shows no
Teensy, press the white button on it once and flash from the Arduino IDE
(Tools > Port, the "teensy" ports); from then on it has a COM port and
this page can do the rest.
"""
from datetime import datetime
from random import Random
from time import monotonic, sleep, time

import serial

from colloquy.base_thread import BaseThread
from colloquy.drivers.arduino import boards
from colloquy.drivers.arduino.flasher.base import SketchFlasher
from colloquy.ui import leaves

from ..bench_com_port import BenchComPort
from . import checks, first_run, sketch

# USB serial ignores the rate, but pyserial wants one.
BAUDRATE = 115200
# A reply to one line, over USB, from an idle sketch: milliseconds. A
# second is a board that is not answering.
REPLY_TIMEOUT = 1.0
# After an upload the Teensy reboots and its COM port goes away and comes
# back. How long to wait for it before asking.
REENUMERATE_TIMEOUT = 15.0

SHOW_STEPS_AGAIN = "show the first-run steps again"


class TeensyComPort(BenchComPort):
    """Which lead the Teensy is on. Real leads only."""

    params_section = "teensy"
    offers_stand_in = False


class TeensyFlasher(SketchFlasher):
    """`teensy_check`, onto the Teensy the test is pointed at.

    Everything about the job is `SketchFlasher`'s. What differs: the board
    type, the kind of board the chosen port must be, and the check
    afterwards, which waits for the Teensy to come back on the bus first.
    """

    @property
    def sketch_folder(self):
        return sketch.SKETCH_FOLDER

    @property
    def fqbn(self):
        return sketch.FQBN

    @property
    def port(self):
        return self.owner.com_port.chosen

    def sketch_says(self):
        return sketch.describe()

    def _wrong_kind_of_board(self, board):
        if board.is_teensy:
            return None
        return (
            f"{board.device} is {board.name}, not a Teensy. Pick the Teensy "
            "under 'com port'."
        )

    def _check_the_board(self, state):
        port = self.port
        deadline = monotonic() + REENUMERATE_TIMEOUT
        while monotonic() < deadline:
            if any(board.device == port for board in boards.detect()):
                break
            sleep(0.5)
        else:
            return (
                f"uploaded, but {port} did not come back within "
                f"{REENUMERATE_TIMEOUT:.0f}s - check 'com port': the Teensy "
                "may have come back on another one"
            )
        # The port is listed a moment before it can be opened.
        sleep(1.0)
        try:
            said = self.owner.handshake()
        except Exception as error:  # noqa: BLE001 - a lead pulled mid-flash
            return f"uploaded, but the board could not be asked: {error}"
        return f"flashed - {said}"

    def _extra_readings(self, leaf):
        leaf("board last said", self.owner.board_verdict)


class TestTeensy(BaseThread):
    scenario_names = ("teensy-test",)

    def __init__(self, owner):
        super().__init__(owner=owner)

        self._com_port = TeensyComPort(owner=self)
        self[self._com_port.name] = self._com_port
        self._flasher = TeensyFlasher(owner=self)
        self[self._flasher.name] = self._flasher

        self._commands = {
            "ask the board": self.ask_the_board,
            "blink the led": self.blink_the_led,
            "the LED blinked": self._led_was(True),
            "the LED did not blink": self._led_was(False),
        }
        for key, command in self._commands.items():
            self[key] = command
        # Before the first run: one `done` link per step, and one to bring
        # them all back. See first_run.py.
        self._done_links = {
            first_run.done_link(key): self._mark_done(key) for key in first_run.KEYS
        }
        self._done_links[SHOW_STEPS_AGAIN] = self._show_steps_again
        for key, command in self._done_links.items():
            self[key] = command

        self._status = None       # the last `?` reply, parsed
        self._status_line = None   # and as it came
        self._checks = []          # the last run's `checks.Check`s
        self._outcome = None
        self._ran_at = None
        self._blinked_at = None    # when `b` was last sent
        self._led_seen = None      # what the person said about it

    @property
    def name(self):
        return "test teensy"

    @property
    def params(self):
        return self.colloquy.params

    @property
    def com_port(self):
        return self._com_port

    def use_port(self, com_port):
        """`BenchComPort.set` asks this after writing params. The link is
        opened afresh for every conversation, so there is nothing to
        re-point; what the board said belongs to the old lead, though."""
        self._status = None
        self._status_line = None

    # --- the lead ---------------------------------------------------------

    def _why_not_open(self):
        """Why talking to the Teensy would fail, or None."""
        chosen = self.com_port.chosen
        if chosen is None:
            return "no port chosen - pick the Teensy under 'com port'"
        found = {board.device: board for board in boards.detect()}
        if chosen not in found:
            available = ", ".join(sorted(found)) or "none, is the Teensy plugged in?"
            return (
                f"{chosen!r} is not a port on this machine - available: "
                f"{available}. A Teensy with no COM port is running a sketch "
                "without USB serial: see this test's description"
            )
        if not found[chosen].is_teensy:
            return f"{chosen} is {found[chosen].name}, not a Teensy"
        return None

    def _open(self):
        handler = serial.Serial(
            port=self.com_port.chosen, baudrate=BAUDRATE, timeout=REPLY_TIMEOUT
        )
        handler.reset_input_buffer()
        return handler

    @staticmethod
    def _ask(handler, command):
        """One line out, one line back (stripped), or '' on silence."""
        handler.write(command.encode("ascii") + b"\n")
        return handler.readline().decode("ascii", "replace").strip()

    def _read_status(self, handler):
        self._status_line = self._ask(handler, "?")
        self._status = sketch.parse_status(self._status_line)
        return self._status

    @property
    def board_verdict(self):
        """What the board last said it was, in words."""
        if self._status_line is None:
            return "not known yet - press 'ask the board'"
        return checks.answers(
            self._status, sketch.firmware_version(), sketch.board_name()
        ).said

    def handshake(self):
        """Open the lead, ask `?`, close it. One line for the page."""
        handler = self._open()
        try:
            self._read_status(handler)
        finally:
            handler.close()
        if not self._status_line:
            return (
                "nothing answered '?' - if this is a Teensy it is not "
                "running teensy_check. Press 'flash firmware'"
            )
        return self.board_verdict

    # --- before the first run ---------------------------------------------

    @property
    def _first_run_done(self):
        """params' record of the steps pressed done. Read defensively: a
        hand-edited params must not break the render."""
        section = self.params.get("teensy")
        done = section.get("first run done") if isinstance(section, dict) else None
        return done if isinstance(done, dict) else {}

    def _mark_done(self, key):
        def done(request=None):
            section = self.params["teensy"]
            if not isinstance(section.get("first run done"), dict):
                section["first run done"] = {}
            section["first run done"][key] = time()
            return (
                f"'{key}' done - it hides from this page in "
                f"{first_run.HIDE_AFTER:.0f} seconds"
            )

        return done

    def _show_steps_again(self, request=None):
        self.params["teensy"]["first run done"] = {}
        return "every first-run step is back on the page"

    # --- presses ----------------------------------------------------------

    def _refusal(self):
        if self.is_started:
            return "the check is running - wait for it"
        if self._flasher.is_started:
            return "the flasher is running - wait for it"
        return self._why_not_open()

    def ask_the_board(self, request=None):
        refusal = self._refusal()
        if refusal is not None:
            return f"refused: {refusal}"
        try:
            return self.handshake()
        except serial.SerialException as error:
            return f"could not open the lead - {error}"

    def blink_the_led(self, request=None):
        refusal = self._refusal()
        if refusal is not None:
            return f"refused: {refusal}"
        try:
            handler = self._open()
            try:
                said = self._ask(handler, "b")
            finally:
                handler.close()
        except serial.SerialException as error:
            return f"could not open the lead - {error}"
        if said != "blink fast":
            return f"the board did not take the command - it said {said!r}"
        self._blinked_at = time()
        self._led_seen = None
        return self._led_instruction()

    def _led_was(self, seen):
        def record(request=None):
            if self._blinked_at is None:
                return "nothing has blinked yet - press 'blink the led' or 'start'"
            self._led_seen = seen
            return self._led_reading()

        return record

    def _led_instruction(self):
        return (
            f"look at the Teensy now: its small orange LED should flicker "
            f"fast for {sketch.blink_fast_seconds():.0f} seconds, then go "
            "back to a slow blink. Then press 'the LED blinked' or 'the LED "
            "did not blink'"
        )

    def _led_reading(self):
        if self._blinked_at is None:
            return "not checked yet"
        if self._led_seen is None:
            return self._led_instruction()
        if self._led_seen:
            return "seen flickering - pin 13 and the LED work"
        if self._status is not None:
            return (
                "NOT seen, though the board answers - the LED or pin 13 is "
                "at fault, or the adapter plate hides it from view"
            )
        return "NOT seen, and the board does not answer - see the checks"

    # --- the run ----------------------------------------------------------

    def setup(self):
        self._checks = []
        self._outcome = None
        self._ran_at = datetime.now()
        self._led_seen = None
        self._blinked_at = None

        refusal = self._why_not_open()
        if refusal is not None:
            self._outcome = f"refused: {refusal}"
            return
        if self._flasher.is_started:
            self._outcome = "refused: the flasher is running - wait for it"
            return

        try:
            handler = self._open()
        except serial.SerialException as error:
            self._outcome = f"could not open the lead - {error}"
            return
        try:
            self._run_checks(handler)
        except serial.SerialException as error:
            self._outcome = f"the lead failed during the check - {error}"
        finally:
            handler.close()

    def _run_checks(self, handler):
        started = monotonic()
        first = self._read_status(handler)
        found = [checks.answers(first, sketch.firmware_version(), sketch.board_name())]
        self._checks = found
        if not found[0].passed:
            self._outcome = checks.overall(found)
            return

        found.append(checks.clock_speed(sketch.number(first, "f_cpu")))
        found.append(checks.temperature(sketch.number(first, "temp_c")))

        rng = Random()
        good, times = 0, []
        for index in range(checks.ECHO_ROUNDS):
            if self._stop_event.is_set():
                break
            text = f"e {index:03d} {rng.getrandbits(160):040x}"
            sent_at = monotonic()
            back = self._ask(handler, text)
            times.append((monotonic() - sent_at) * 1000)
            good += back == text
        found.append(checks.echo(len(times), good, times))

        second = self._read_status(handler)
        ended = monotonic()
        board_ms = None
        if second is not None:
            before = sketch.number(first, "uptime_ms")
            after = sketch.number(second, "uptime_ms")
            if before is not None and after is not None:
                board_ms = after - before
        found.append(checks.clock_keeps_time(board_ms, (ended - started) * 1000))

        if self._ask(handler, "b") == "blink fast":
            self._blinked_at = time()

        self._checks = found
        self._outcome = checks.overall(found)

    def loop(self):
        # One pass, all of it in setup(). Nothing to poll.
        self.stop()

    def setdown(self):
        pass

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {
            self._com_port.name: self._com_port,
            self._flasher.name: self._flasher,
            "ask the board": self.ask_the_board,
            "blink the led": self.blink_the_led,
        }
        if self._blinked_at is not None:
            children["the LED blinked"] = self._commands["the LED blinked"]
            children["the LED did not blink"] = self._commands["the LED did not blink"]
        # A step not yet done offers its `done`; one just pressed is still
        # drawn (so the press visibly took) but has nothing left to press.
        steps = first_run.visible(self._first_run_done, time())
        for key, _, left in steps:
            if left is None:
                link = first_run.done_link(key)
                children[link] = self._done_links[link]
        if len(steps) < len(first_run.STEPS):
            children[SHOW_STEPS_AGAIN] = self._done_links[SHOW_STEPS_AGAIN]
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        # First, because nothing below works until they are done.
        for number, (key, text, left) in enumerate(
            first_run.visible(self._first_run_done, time()), start=1
        ):
            if left is not None:
                text = f"done - hides in {left:.0f}s"
            leaf(f"before the first run {number}: {key}", text)

        leaf("port", self.com_port.chosen or "not set")
        leaf("sketch", "Source code/Arduino/teensy_check/")
        if self._status_line:
            leaf("board says", self._status_line)
        leaf("firmware", self.board_verdict)

        refusal = self._why_not_open()
        leaf("can talk", "yes" if refusal is None else f"no - {refusal}")

        if self.is_started:
            leaf("running", "checking - refresh in a moment")
        if self._ran_at is not None:
            leaf("last run", self._ran_at.strftime("%Y-%m-%d %H:%M:%S"))
        for check in self._checks:
            mark = "ok" if check.passed else "FAILED"
            leaf(f"check: {check.name}", f"{mark} - {check.said}")
        leaf("led", self._led_reading())
        if self._outcome is not None:
            leaf("outcome", self._outcome)
        return states
