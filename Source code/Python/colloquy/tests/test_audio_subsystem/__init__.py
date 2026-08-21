# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_subsystem/__init__.py

import serial
import serial.tools.list_ports as list_ports

from datetime import datetime
from functools import partial
from time import time

from colloquy.base_thread import BaseThread
from colloquy.drivers.com_port import ComPort
from colloquy.ui import leaves

from . import protocol
from .setup_document import HardwareSetup


class AudioComPort(ComPort):
    """Which port Thomas's board is on. Its own, not the installation's:
    this is a second Mega on a second USB lead, and picking the wrong one
    of the two is the first thing that goes wrong at a bench."""

    def __init__(self, owner, value=None):
        super().__init__(owner=owner, value=None)

    def set(self, com_port, *args, **kwargs):
        self.owner.port_handler.port = com_port
        self.owner.params["audio subsystem"]["communication port"] = com_port
        self._value = com_port

    @property
    def ports(self):
        """What this machine really has, which is not what the others do.

        The base ComPort answers with the *piece's* simulated ports, and
        that is the wrong question here: the bench has real serial ports
        and no installation, so on it this lists the actual leads. Off the
        bench there is one stand-in and nothing else - offering the U2D2's
        and the Arduino's port names on this picker only ever invited
        somebody to choose one.
        """
        for name in self._ports:
            self._dict.pop(name)

        if self.is_bench:
            self._ports = [port.device for port in list_ports.comports()]
        else:
            self._ports = ["simulated audio port"]

        for name in self._ports:
            self[name] = partial(self.set, com_port=name)

        return self._ports

    @property
    def snapshot_children(self):
        """The ports to choose from, as one command each.

        The base ComPort does not answer this at all - the installation's
        Arduino and U2D2 are reached through path dispatch and never drawn
        as nodes, so nobody had needed it. This test is meant to be used
        from the page by somebody at a bench, and picking the right one of
        three USB leads is the first thing they have to do.
        """
        return {name: self[name] for name in self.ports}


class TestAudioSubsystem(BaseThread):
    """A bench test for Thomas's audio subsystem, driven through his own
    tester firmware.

    Not part of the installation and not something to run in the gallery:
    it wants a Mega 2560 on a USB lead with `Source code/Thomas/
    AudioAnalyzerTest.cpp` on it, five speakers and five microphones, and
    somebody sitting in front of it. No servo turns and no NeoPixel
    lights - this touches nothing the piece is made of.

    What it answers is one question, five times over: **does each tone
    reach each analyser module?** It silences the board and reads every
    module as a floor, then brings up one tone at a time and reads them
    again, and reports for every tone-and-module pair whether the right
    band rose. See protocol.verdict for what the three answers mean.

    That is the whole hardware chain in one pass - timer, output pin, amp,
    speaker, air, microphone, MSGEQ7, ADC - which is why a failure here
    says which pair is broken but not which link in it. The manual
    commands below are for finding that out: hold one tone on and walk
    along the bench with an ear or a scope.

    Nothing above this exists yet. There is no speaker node, no
    microphone node, and nothing that sings - see CODE_DOCUMENTATION
    section 9, which this does not begin to build. It only says whether
    the hardware it would be built on is working.
    """

    # How long each tone is held while its readings are collected. Long
    # enough for a person to hear it and to place it in the room, since
    # this test is meant to be watched (and listened to) rather than
    # left running.
    TONE_SECONDS = 3.0

    # After a tone is switched on, before its readings count: the MSGEQ7
    # is a peak detector with its own decay, so the first sweep after a
    # change still carries some of the last state.
    SETTLE_SECONDS = 0.7

    # After the "> " prompt appears, before writing the next command.
    # readSerial() prints the prompt and *then* resets the port, throwing
    # away whatever has already arrived - so a command sent the instant
    # the prompt shows can vanish, and the run hangs waiting for a reply
    # to something the board never read. See protocol's module docstring.
    PROMPT_SETTLE = 0.2

    # Nothing on the other end, or the wrong thing on the other end.
    REPLY_TIMEOUT = 5.0

    # How far a band has to rise above its own silent level to count as
    # having heard the tone. The MSGEQ7's output is 0-1023 off the ADC and
    # a tone in its own band is not subtle, so this is deliberately blunt:
    # it is here to reject drift and room noise, not to measure anything.
    # If a real bench needs it tuned, it is a params value away.
    MARGIN = 60

    scenario_names = ("audio-subsystem-test",)

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._port_handler = None
        self._com_port = AudioComPort(owner=self)
        self[self._com_port.name] = self._com_port

        # How to wire the thing this test measures. It sits here rather
        # than on the root because it is about this bench and nothing
        # else - and beside the scenario, which says what the run will
        # do once the wiring is right.
        self._hardware_setup = HardwareSetup(owner=self)

        # For finding out which link of the chain is broken once the sweep
        # has said that one is. Each holds a tone on until something else
        # turns it off, which is what you want while walking the bench.
        self._manual = {}
        for timer in protocol.TIMERS_BY_PITCH:
            hz = protocol.TIMERS[timer]["hz"]
            pin = protocol.TIMERS[timer]["pin"]
            self._manual[f"hold {hz} Hz on ({pin})"] = partial(
                self._send_manual, protocol.enable(timer)
            )
        self._manual["silence"] = partial(self._send_manual, protocol.disable("a"))
        self._manual["all five at once"] = partial(
            self._send_manual, protocol.enable("a")
        )

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._queue = None
        self._current = None
        self._silence = None
        self._verdicts = {}
        self._outcome = None
        self._manual_reply = None
        self._buffer = ""

    @property
    def name(self):
        return "test audio subsystem"

    @property
    def params(self):
        # The board's own settings sit beside the installation's Arduino
        # at the root of params.json, not under "tests": it is a piece of
        # hardware on a bench, not a knob on one run.
        return self.colloquy.params

    @property
    def com_port(self):
        return self._com_port

    @property
    def baudrate(self):
        return self.params["audio subsystem"]["baudrate"]

    @property
    def board_is_real(self):
        """Shown on the page, because a wrong answer here is otherwise
        silent: a run against the stand-in passes all twenty-five and
        looks exactly like a run against a working bench."""
        return self.is_bench

    @property
    def port_handler(self):
        if self._port_handler is None:
            # is_bench, not is_simulated. The bench is simulated as far as
            # the piece goes - it has no servos and no Arduino - and its
            # audio board is as real as hardware gets.
            if self.is_bench:
                self._port_handler = serial.Serial(
                    baudrate=self.baudrate, timeout=0.05
                )
            else:
                self._port_handler = self.colloquy.virtual_drivers.audio_serial_port
            self._port_handler.port = self.params["audio subsystem"][
                "communication port"
            ]
        return self._port_handler

    # --- the line, one exchange at a time ---------------------------------

    def _write(self, command):
        self.log(f"> {command}")
        self.port_handler.write(
            (command + protocol.LINE_ENDING).encode("ascii", "replace")
        )

    def _read_until(self, tail, timeout=None):
        """Collect until what has arrived ends with `tail`.

        Returns everything read, prompt included, or None on timeout - the
        caller decides whether a silent board is a refusal or a failure.
        """
        deadline = time() + (self.REPLY_TIMEOUT if timeout is None else timeout)
        collected = ""
        while time() < deadline:
            if self._stop_event.is_set():
                return None
            chunk = self.port_handler.read(256)
            if chunk:
                collected += chunk.decode("ascii", "replace")
                if protocol.strip_ansi(collected).rstrip(" ").endswith(tail.rstrip(" ")):
                    return collected
        return None

    def _command(self, command):
        """Write one command and read back to the next prompt.

        Every step here begins at a prompt and ends at one - setup() reads
        past the opening banner to the first, and each reply ends at the
        next - so this does not wait for one first. It used to, and that
        deadlocked on the very first command: the prompt it was waiting
        for had already been read as the tail of the banner.
        """
        self._settle(self.PROMPT_SETTLE)
        self._write(command)
        return self._read_until(protocol.PROMPT)

    def _settle(self, seconds):
        """Wait without going deaf: bytes that arrive during a settle are
        kept, since the board is free to talk whenever it likes."""
        deadline = time() + seconds
        while time() < deadline and not self._stop_event.is_set():
            chunk = self.port_handler.read(256)
            if chunk:
                self._buffer += chunk.decode("ascii", "replace")

    def _send_manual(self, command, request=None):
        """One command from the page, with or without a run going.

        Opening the port resets the board, so if a sweep is running this
        borrows the line it already has rather than taking a second one -
        which is also why holding a tone during a sweep will show up in
        that sweep's readings. Do one or the other.
        """
        was_open = self._port_handler is not None and self.port_handler.is_open
        if not was_open:
            self.port_handler.open()
            self._read_until(protocol.PROMPT, timeout=8.0)
        self._settle(self.PROMPT_SETTLE)
        self._write(command)
        reply = self._read_until(protocol.PROMPT, timeout=3.0)
        self._manual_reply = (
            protocol.strip_ansi(reply).strip() if reply else "no reply"
        )
        if not was_open and not self.is_started:
            # Left open on purpose while a tone is being held: closing it
            # resets the board, which would silence the very tone that was
            # just asked for. "silence" is what closes it again.
            if command == protocol.disable("a"):
                self.port_handler.close()
        return self._manual_reply

    # --- the run ----------------------------------------------------------

    def run(self):
        now = datetime.now()
        file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = file_path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._start_time = time()
        self._verdicts = {}
        self._silence = None
        self._outcome = None
        self._buffer = ""
        self._file.write(
            "seconds, tone, module, "
            + ", ".join(f"{hz} Hz" for hz in protocol.BANDS_HZ)
            + "\n"
        )

        chosen = self.params["audio subsystem"]["communication port"]
        if chosen is None:
            self._refuse("no port chosen - pick Thomas's board under 'com port'")
            return

        # The chosen port is remembered in params, and it outlives the
        # machine that chose it: a laptop that ran this simulated leaves
        # "simulated audio port" behind, and on the bench that opens
        # nothing and fails with a pyserial error about a port nobody
        # recognises. Say what is stored and what is actually there.
        available = self.com_port.ports
        if chosen not in available:
            self._refuse(
                f"{chosen!r} is not a port on this machine - "
                f"available: {', '.join(available) or 'none, is the board plugged in?'}"
            )
            return

        self.port_handler.open()

        # His firmware clears the screen and prints its banner on reset,
        # and opening the port is what resets the board. Waiting for the
        # banner rather than for the prompt is what tells us this is the
        # audio tester and not the installation's own Arduino on the next
        # USB socket down - which answers JSON and would otherwise sit
        # there silently failing to be a menu.
        banner = self._read_until(protocol.PROMPT, timeout=8.0)
        if banner is None or protocol.BANNER not in protocol.strip_ansi(banner):
            self._refuse(
                "no audio tester on that port - expected the welcome banner "
                f"({protocol.BANNER!r}) and got {banner!r}"
            )
            return

        self._queue = [None] + list(protocol.TIMERS_BY_PITCH)
        self._advance()

    def setdown(self):
        self._start_time = None
        self._current = None
        if self._port_handler is not None and self.port_handler.is_open:
            # Leave it quiet whatever happened, including on an error or a
            # stop half way: five tones left on is not a state to walk
            # away from.
            self._write(protocol.disable("a"))
            self._read_until(protocol.PROMPT, timeout=2.0)
            self.port_handler.close()
        if self._file is not None:
            self._file.close()

    def _refuse(self, reason):
        self._outcome = f"refused: {reason}"
        self.log(f"Refusing to run: {reason}")
        self.stop()

    def _advance(self):
        if not self._queue:
            self._current = None
            self._outcome = self._summary()
            self.stop()
            return
        self._current = self._queue.pop(0)

    def loop(self):
        if self._current is None and self._queue is None:
            return

        timer = self._current
        label = "silence" if timer is None else f"{protocol.TIMERS[timer]['hz']} Hz"

        # One tone at a time: everything off first, so a leftover from the
        # previous step cannot be counted as this one.
        if self._command(protocol.disable("a")) is None:
            self._refuse(f"no reply while silencing before {label}")
            return
        if timer is not None and self._command(protocol.enable(timer)) is None:
            self._refuse(f"no reply while enabling {label}")
            return

        self._settle(self.SETTLE_SECONDS)

        readings = self._collect(label)
        if not readings:
            self._refuse(f"no analyser readings came back during {label}")
            return

        averages = protocol.average_per_module(readings)
        if timer is None:
            self._silence = averages
        else:
            self._judge(timer, averages)

        self._advance()

    def _collect(self, label):
        """Hold this tone and read tables for TONE_SECONDS."""
        if self._command(protocol.dump("a")) is None:
            # "Aa" streams rather than returning to a prompt, so no reply
            # here is the normal case - the read below is the real one.
            pass

        deadline = time() + self.TONE_SECONDS
        text = self._buffer
        self._buffer = ""
        while time() < deadline and not self._stop_event.is_set():
            chunk = self.port_handler.read(256)
            if chunk:
                text += chunk.decode("ascii", "replace")

        self._write(protocol.ABORT)
        # Aborting returns from the command loop, so the board redraws its
        # whole welcome banner before prompting again. Read past it.
        self._read_until(protocol.PROMPT, timeout=3.0)

        readings = protocol.parse_tables(text)
        elapsed = time() - self._start_time
        for module, values in readings:
            self._file.write(
                f"{elapsed}, {label}, {module}, "
                + ", ".join(str(value) for value in values)
                + "\n"
            )
        return readings

    def _judge(self, timer, averages):
        for module in range(protocol.MODULE_COUNT):
            silence = self._silence.get(module)
            tone = averages.get(module)
            if silence is None or tone is None:
                self._verdicts[(timer, module)] = "no reading"
                continue
            self._verdicts[(timer, module)] = protocol.verdict(
                silence, tone, timer, self.MARGIN
            )

    def _summary(self):
        heard = sum(1 for value in self._verdicts.values() if value == "heard")
        total = len(self._verdicts)
        if total and heard == total:
            return f"all {total} tone/module pairs heard"
        bad = sorted(
            f"{protocol.TIMERS[timer]['hz']} Hz on module {module}: {value}"
            for (timer, module), value in self._verdicts.items()
            if value != "heard"
        )
        return f"{heard}/{total} heard - " + "; ".join(bad)

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {
            self._com_port.name: self._com_port,
            self._hardware_setup.name: self._hardware_setup,
        }
        children.update(self._manual)
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        into = leaves.into(states, path)

        into(
            "board",
            "real, on this machine" if self.board_is_real else "simulated stand-in",
        )
        into("port", self.params["audio subsystem"]["communication port"])
        if self._outcome is not None:
            into("outcome", self._outcome)
        if self._manual_reply is not None:
            into("last command", self._manual_reply)
        if self._current is not None:
            hz = protocol.TIMERS[self._current]["hz"]
            into("now sounding", f"{hz} Hz ({protocol.TIMERS[self._current]['pin']})")

        for (timer, module), value in sorted(self._verdicts.items()):
            hz = protocol.TIMERS[timer]["hz"]
            into(f"{hz} Hz -> module {module}", value)

        return states
