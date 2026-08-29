# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/__init__.py

"""One board that makes a tone and says whether it hears it.

The bench answer to the question the installation's own hearing side
cannot yet be trusted on: **is a tone of this frequency actually arriving
at this microphone?** `Source code/Arduino/goertzel_ear/` is the sketch,
for a Mega with a speaker and a microphone on it and nothing else.

**Why this is not `test audio subsystem`.** That one drives Thomas's
boards over his own serial menu and asks whether five MSGEQ7 channels
work. This asks a narrower question with no analyser chip in it at all -
one frequency, one Goertzel bin, arithmetic on the samples - and it
answers it about *any* frequency rather than the seven bands an MSGEQ7
happens to have. It is the experiment behind `one board per body` section
4: if a Pro Mini can do this, the analyser array is a part the next board
does not need.

**It closes the loop on one board on purpose.** A speaker and a
microphone on the same Mega means the whole thing sits on a desk with
nothing else plugged in, and a failure is either the air between them or
the board - there is no cable in the middle to blame. That is also its
limit: it says nothing about a body's amplifier, a body's speaker, or a
metre of harness.

**What a run does.** Sweeps the installation's five pitches. For each: it
silences the tone and measures the bin (the floor), plays the tone and
measures again, and records the rise. A tone that does not rise over its
own silence is not being heard, and which of the two halves is at fault
is the one thing this cannot tell you - hold the tone by hand and listen.
"""
from datetime import datetime
from time import time

import serial

from colloquy.base_thread import BaseThread
from colloquy.drivers import audio
from colloquy.ui import leaves

from ..bench_com_port import BenchComPort
from . import protocol


class EarComPort(BenchComPort):
    """Which lead the ear board is on. See `BenchComPort` - the params key
    is the only thing that differs from Thomas's picker."""

    params_section = "goertzel ear"
    stand_in = "simulated ear port"


class TestGoertzelEar(BaseThread):
    scenario_names = ("goertzel-ear-test",)

    # The board answers a sweep line per pitch, and a self test is two
    # captures plus two settles - about a third of a second each.
    REPLY_TIMEOUT = 4.0

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._com_port = EarComPort(owner=self)
        self[self._com_port.name] = self._com_port
        self._port_handler = None

        self._manual = {"silence": self._silence, "read once": self._read_once}
        for hz in protocol.PITCHES:
            self._manual[f"hold {hz} Hz"] = self._holder(hz)
        for key, command in self._manual.items():
            self[key] = command

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._readings = []
        self._outcome = None
        self._last_line = None
        self._greeting = None

    @property
    def name(self):
        return "test goertzel ear"

    @property
    def params(self):
        return self.colloquy.params

    @property
    def com_port(self):
        return self._com_port

    @property
    def baudrate(self):
        return self.params[EarComPort.params_section]["baudrate"]

    @property
    def board_is_real(self):
        """Shown on the page, because a wrong answer here is otherwise
        silent - the same lesson as `test audio subsystem`."""
        return self.is_bench

    @property
    def port_handler(self):
        """A real serial port or nothing at all.

        There is deliberately no stand-in. Every other simulated thing in
        this repository stands in for something the installation has, and
        a run against one is a rehearsal; this board exists to answer
        whether a microphone hears a tone, and a stand-in that answered
        "yes" would be the one kind of false confidence this test is
        against. Off the bench it refuses instead - see `_why_not_open`.
        """
        if self._port_handler is None:
            # is_bench, not is_simulated: the bench is simulated as far as
            # the piece goes and its boards are as real as hardware gets.
            self._port_handler = serial.Serial(baudrate=self.baudrate, timeout=0.2)
            self._port_handler.port = self.params[
                EarComPort.params_section
            ]["communication port"]
        return self._port_handler

    # --- the line ---------------------------------------------------------

    def _why_not_open(self):
        """Why talking to it would fail, or None.

        The same check `test audio subsystem` makes, and for the same
        reason: the chosen port is remembered in params and outlives the
        machine that chose it, so a name from another desk opens nothing
        and fails with a pyserial error about a port nobody recognises.
        """
        if not self.is_bench:
            return (
                "this is not the bench - the ear board is a Mega on a desk "
                "with a speaker and a microphone on it, and there is no "
                "stand-in for it on purpose"
            )

        chosen = self.params[EarComPort.params_section]["communication port"]
        if chosen is None:
            return "no port chosen - pick the ear board under 'com port'"

        available = self.com_port.ports
        if chosen not in available:
            return (
                f"{chosen!r} is not a port on this machine - available: "
                f"{', '.join(available) or 'none, is the board plugged in?'}"
                " - pick one under 'com port'"
            )
        return None

    def _command(self, text, expect=1):
        """Send one line and collect the replies it produces."""
        handler = self.port_handler
        handler.reset_input_buffer()
        handler.write((text + "\n").encode("ascii"))

        lines = []
        deadline = time() + self.REPLY_TIMEOUT
        while time() < deadline and len(lines) < expect:
            if self._stop_event.is_set():
                break
            raw = handler.readline()
            if not raw:
                continue
            line = raw.decode("ascii", "replace").strip()
            if line:
                lines.append(line)
                self._last_line = line
        return lines

    # --- what the page offers ---------------------------------------------

    def _holder(self, hz):
        def hold(request=None):
            refusal = self._why_not_open()
            if refusal is not None:
                return f"refused: {refusal}"
            self._open_if_needed()
            self._command(f"f {hz}")
            self._command("t 1")
            return (
                f"{hz} Hz sounding on the ear board's D11. Listen for it, "
                "and press 'silence' when you have."
            )

        return hold

    def _silence(self, request=None):
        refusal = self._why_not_open()
        if refusal is not None:
            return f"refused: {refusal}"
        self._open_if_needed()
        self._command("t 0")
        return "quiet"

    def _read_once(self, request=None):
        refusal = self._why_not_open()
        if refusal is not None:
            return f"refused: {refusal}"
        self._open_if_needed()
        lines = self._command("m")
        self._last_line = lines[0] if lines else "no reply"
        return self._last_line

    def _open_if_needed(self):
        if not self.port_handler.is_open:
            self.port_handler.open()
            # It reboots when the port opens and greets on the way up.
            self._greeting = None
            deadline = time() + 4.0
            while time() < deadline and self._greeting is None:
                raw = self.port_handler.readline()
                if raw and raw.startswith(b"goertzel_ear"):
                    self._greeting = raw.decode("ascii", "replace").strip()

    # --- the run ----------------------------------------------------------

    def run(self):
        now = datetime.now()
        path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_"
            f"{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._readings = []
        self._outcome = None
        self._file.write("hz, bin hz, floor, tone, rise, heard, sample rate\n")

        refusal = self._why_not_open()
        if refusal is not None:
            self._refuse(refusal)
            return

        self._open_if_needed()
        if self._greeting is None:
            self._refuse(
                "no ear board on that port - it did not greet. Is "
                "goertzel_ear.ino flashed onto it?"
            )
            return

        # One self test per pitch, in one command, so the board keeps its
        # own timing between silence and tone rather than waiting on a
        # round trip for each.
        for line in self._command("w", expect=len(protocol.PITCHES) + 1):
            reading = protocol.parse_test(line)
            if reading is None:
                continue
            self._readings.append(reading)
            self._file.write(
                f"{reading.hz}, {reading.bin_hz}, {reading.floor}, "
                f"{reading.tone}, {reading.rise}, "
                f"{1 if reading.heard else 0}, {reading.sample_rate}\n"
            )
        self._file.flush()
        self._finish()
        self.stop()

    def loop(self):
        pass

    def _finish(self):
        heard = [r for r in self._readings if r.heard]
        self._outcome = protocol.summarise(self._readings)
        self.log(f"{len(heard)}/{len(self._readings)} heard - {self._outcome}")

    def _refuse(self, reason):
        self._outcome = f"refused: {reason}"
        self.log(f"Refusing to run: {reason}")
        self.stop()

    def setdown(self):
        try:
            if self._port_handler is not None and self._port_handler.is_open:
                self._command("t 0")
                self._port_handler.close()
        except Exception as error:  # noqa: BLE001 - a quiet board, not a crash
            self.log(f"Could not silence the ear board: {error}")
        finally:
            if self._file is not None:
                self._file.close()

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {self._com_port.name: self._com_port}
        children.update(self._manual)
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf(
            "board",
            "the real ear board" if self.board_is_real else "a stand-in - "
            "this is not the bench, so nothing here is measuring anything",
        )
        leaf("port", self.params[EarComPort.params_section]["communication port"]
             or "not set")
        leaf("sketch", "Source code/Arduino/goertzel_ear/")
        if self._greeting:
            leaf("greeting", self._greeting)

        refusal = self._why_not_open()
        leaf("can run", "yes" if refusal is None else f"no - {refusal}")
        if self._outcome is not None:
            leaf("outcome", self._outcome)
        for reading in self._readings:
            leaf(
                f"{reading.hz} Hz",
                f"floor {reading.floor}, tone {reading.tone}, "
                f"rise {reading.rise} - "
                f"{'heard' if reading.heard else 'NOT heard'}",
            )
        if self._last_line:
            leaf("last reply", self._last_line)
        return states
