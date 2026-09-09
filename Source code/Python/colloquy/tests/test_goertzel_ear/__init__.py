# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/__init__.py

"""Does a microphone hear a tone? Play one and watch the bin.

The narrowest question in the sound channel, and the one every other test
of it has to assume the answer to. `test_audio_subsystem` asks whether
Thomas's five MSGEQ7 channels work; `test_audio_loop` asks whether the
bodies are wired into the piece the right way round; `test_audio_bringup`
takes a nine-link chain apart. All three judge hearing by seven band
values out of an analyser chip. This one has no analyser chip in it at
all - one Goertzel bin per frequency, arithmetic on the samples - so it
can be pointed at *any* frequency rather than the seven bands an MSGEQ7
happens to have.

**Three parts, and only one of them is on a board.**

- The **tone** comes out of this computer's own speakers. One link per
  pitch and one to silence it. See `tone.py`, which also says why it is a
  sine here where the board's was a square.
- The **samples** come from a Mega running
  `Source code/Arduino/microphone_sampler/`, which does nothing else. A
  microphone on `A0`, a common ground, and no other wire.
- The **arithmetic** runs here, in `goertzel.py`, over blocks as they
  arrive.

It used to be one board doing all three (`Source code/Arduino/goertzel_ear/`,
still there and still worth having - see its header). Moving two of the
three off it is not tidying: a sound card makes a cleaner tone than a
timer can, one capture can be measured at all five pitches at once
because the samples are in hand on a machine with memory to spare, and a
sampler that only samples cannot be wrong about a frequency.

**Why this is a manual test where the board version was an autotest.**
The old arrangement was a closed loop on one board - a speaker and a
microphone six inches apart, nothing else plugged in - so it could sweep
five pitches, write a file, and be walked away from. This one is open,
and what it is open across is a room with a volume knob in it. Whether
the speakers are on, whether the output is muted, whether the level is
anywhere near what a microphone across a desk can hear, whether
something else in the room is making a noise: none of that is knowable
from here, and a "not heard" is at least as likely to be a muted laptop
as a deaf microphone. The one thing that settles it is somebody hearing
the tone come out of the speakers, and no file can hold that. So: press
a pitch, *listen*, and watch its row.

**Only the rise means anything.** A MAX9814 has automatic gain control,
so its absolute level says nothing - the gain moves to keep the output
where it likes it. What it can say is that this frequency is louder than
it was a moment ago, at a gain that has not had time to follow. So every
pitch carries a floor - its level while nothing was playing - and the
reading to watch is the difference.

**The link is the lead, not the machine.** There is no `is_bench` here
any more. This is one Mega on one USB lead with a microphone on it, it
travels to whichever desk somebody is working at, and the only questions
worth asking are whether a port has been chosen and whether this machine
has it. That is the lesson `Arduino.is_using_the_stand_in` and
`BenchComPort` both learned, travelling in opposite directions.

**And there is no stand-in, on purpose.** Every other simulated thing in
this repository stands in for something the installation has, and a run
against one is a rehearsal. This exists to say whether a microphone hears
a tone; a stand-in that answered "yes" would be the one kind of false
confidence it is against.
"""
from time import time

import serial

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

from ..bench_com_port import BenchComPort
from . import goertzel, protocol
from .tone import Tone


class EarComPort(BenchComPort):
    """Which lead the sampler board is on. See `BenchComPort` - the params
    key is the only thing that differs from Thomas's picker."""

    params_section = "goertzel ear"
    stand_in = "simulated ear port"


class TestGoertzelEar(BaseThread):
    scenario_names = ("goertzel-ear-test",)

    # A block is 512 numbers of text - about 20 ms on the wire at 1 Mbaud,
    # after 27 ms of capture. Four a second leaves the link mostly idle and
    # redraws faster than anybody can move a microphone.
    READ_INTERVAL = 0.25

    # Long enough to cover a capture, a 2 kB reply and a board that is
    # thinking about it; short enough that a dead lead is reported rather
    # than sat on.
    REPLY_TIMEOUT = 2.0

    # A tone has to be sounding before the block meant to show it is
    # captured, and the microphone's gain control has to have stopped
    # moving. Blocks inside this window are read and drawn, but scored as
    # neither floor nor rise.
    SETTLE = 0.4

    def __init__(self, owner):
        super().__init__(owner=owner)

        self._com_port = EarComPort(owner=self)
        self[self._com_port.name] = self._com_port
        self._port_handler = None

        self._tone = Tone()

        self._commands = {}
        for hz in protocol.PITCHES:
            self._commands[f"play {hz} Hz"] = self._player(hz)
        self._commands["silence"] = self._silence
        self._commands["forget the floors"] = self._forget_floors
        for key, command in self._commands.items():
            self[key] = command

        self._block = None
        self._levels = {}      # hz -> its level in the last block
        self._floors = {}      # hz -> its level while nothing was playing
        self._best = {}        # hz -> the (floor, level) of its best rise
        self._blocks_read = 0
        self._greeting = None
        self._outcome = None
        self._playing_since = None
        self._last_read_at = 0.0

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
    def tone(self):
        return self._tone

    @property
    def port_handler(self):
        """A real serial port, or none at all - there is no stand-in here.

        See the module docstring. Where there is no board this refuses
        instead, in `_why_not_open`.
        """
        if self._port_handler is None:
            self._port_handler = serial.Serial(
                baudrate=self.baudrate, timeout=self.REPLY_TIMEOUT
            )
            self._port_handler.port = self.params[
                EarComPort.params_section
            ]["communication port"]
        return self._port_handler

    def use_port(self, com_port):
        """Point the link at a newly chosen lead.

        There is only one kind of handler here - no stand-in, on purpose -
        so this is a name change rather than the swap `BenchBoardLink` has
        to make. It exists because `BenchComPort` asks its owner to
        re-point rather than reaching into the handler itself.
        """
        self.port_handler.port = com_port

    # --- the line ---------------------------------------------------------

    def _why_not_open(self):
        """Why talking to the board would fail, or None.

        Two questions, both about the lead. The chosen port is remembered
        in params and outlives the machine that chose it, so a name from
        another desk opens nothing and fails with a pyserial error about a
        port nobody recognises.
        """
        chosen = self.params[EarComPort.params_section]["communication port"]
        if chosen is None:
            return "no port chosen - pick the sampler board under 'com port'"

        available = self.com_port.ports
        if chosen not in available:
            return (
                f"{chosen!r} is not a port on this machine - available: "
                f"{', '.join(available) or 'none, is the board plugged in?'}"
                " - pick one under 'com port'"
            )
        return None

    def _why_no_sound(self):
        """Why playing a tone would fail, or None.

        Asked separately from the lead, because the two failures look
        identical from the readings: a machine that cannot make a sound
        reports five flat bins, which is exactly what a deaf microphone
        reports.
        """
        if not self._tone.is_available:
            return (
                "this machine cannot play a sound - no `sounddevice` (pip "
                "install sounddevice) or no output device. There is "
                "deliberately no silent fallback"
            )
        return None

    def _open_if_needed(self):
        if not self.port_handler.is_open:
            self.port_handler.open()
            # It reboots when the port opens and greets on the way up.
            self._greeting = None
            deadline = time() + 4.0
            while time() < deadline and self._greeting is None:
                raw = self.port_handler.readline()
                if raw and raw.startswith(b"microphone_sampler"):
                    self._greeting = raw.decode("ascii", "replace").strip()

    def _read_block(self):
        """Ask for one capture and read it back, or None."""
        handler = self.port_handler
        handler.reset_input_buffer()
        handler.write(b"b\n")

        deadline = time() + self.REPLY_TIMEOUT
        while time() < deadline:
            if self._stop_event.is_set():
                return None
            raw = handler.readline()
            if not raw:
                continue
            block = protocol.parse_block(raw.decode("ascii", "replace").strip())
            if block is not None:
                return block
        return None

    # --- what the page offers ---------------------------------------------

    def _player(self, hz):
        def play(request=None):
            refusal = self._why_no_sound()
            if refusal is not None:
                return f"refused: {refusal}"
            played = self._tone.play(hz)
            self._playing_since = time()
            return (
                f"{hz} Hz sounding out of this computer's speakers "
                f"(actually {played:.1f} Hz - snapped to a whole number of "
                "cycles so the loop does not click). Listen for it, and "
                "watch its row."
            )

        return play

    def _silence(self, request=None):
        self._tone.stop()
        self._playing_since = None
        return "quiet"

    def _forget_floors(self, request=None):
        """Throw the silent levels away and take them again.

        The command `test_microphone_signal` has for its peaks, and for
        the same reason: a floor taken before somebody moved the
        microphone, shut a window or turned a fan off quietly makes every
        rise measured against it wrong.
        """
        self._floors = {}
        self._best = {}
        self._outcome = None
        return "floors forgotten - taken again on the next silent block"

    # --- the run ----------------------------------------------------------

    def setup(self):
        self._block = None
        self._levels = {}
        self._floors = {}
        self._best = {}
        self._blocks_read = 0
        self._outcome = None
        self._last_read_at = 0.0

        refusal = self._why_not_open()
        if refusal is not None:
            self._refuse(refusal)
            return

        self._open_if_needed()
        if self._greeting is None:
            self._refuse(
                "no sampler board on that port - it did not greet. Is "
                "microphone_sampler.ino flashed onto it, and is the baud "
                f"rate right? Opened at {self.baudrate}."
            )
            return

        sound = self._why_no_sound()
        if sound is not None:
            # Not a refusal. The reading half is worth having on its own -
            # somebody with a signal generator, or a phone, can make the
            # sound another way - and the page says the tone links will not
            # work rather than leaving them to fail one at a time.
            self._outcome = (
                f"reading, but nothing here can play a tone - {sound}. Make "
                "the sound some other way."
            )

    def loop(self):
        now = time()
        if (now - self._last_read_at) < self.READ_INTERVAL:
            return
        self._last_read_at = now

        block = self._read_block()
        if block is None:
            self._refuse(
                "the board stopped answering - it greeted, so the lead was "
                "right; check it is still plugged in"
            )
            return

        self._block = block
        self._blocks_read += 1
        self._levels = goertzel.magnitudes(
            block.samples, protocol.PITCHES, block.sample_rate
        )
        self._score(now)

    def _score(self, now):
        """File this block's levels as floors, or as a rise, or as neither.

        Which of the three depends on one thing: is a tone sounding, and
        has it been sounding long enough for the gain control to stop
        moving. A block caught in between is still read and still drawn -
        the page stays live - and scored as neither, because a floor taken
        while a tone is fading up is a floor with the tone in it.
        """
        sounding = self._tone.hz
        if sounding is None:
            self._floors = dict(self._levels)
            return

        if self._playing_since is None:
            return
        if (now - self._playing_since) < self.SETTLE:
            return

        floor = self._floors.get(sounding)
        if floor is None:
            # Nothing silent has been measured yet, so there is nothing to
            # measure a rise against. Press `silence` first.
            return

        level = self._levels[sounding]
        best = self._best.get(sounding)
        if best is None or (level - floor) > (best[1] - best[0]):
            self._best[sounding] = (floor, level)

        self._outcome = protocol.summarise(self.readings)

    def setdown(self):
        # The room must not be left making a noise by a run that has ended.
        self._tone.stop()
        self._playing_since = None
        try:
            if self._port_handler is not None and self._port_handler.is_open:
                self._port_handler.close()
        except Exception as error:  # noqa: BLE001 - a quiet board, not a crash
            self.log(f"Could not close the sampler board's port: {error}")

    def _refuse(self, reason):
        self._outcome = f"refused: {reason}"
        self.log(f"Refusing to run: {reason}")
        self.stop()

    # --- what has been found ----------------------------------------------

    @property
    def readings(self):
        """One Reading per pitch that has actually been played.

        Not one per pitch: a single tone sounds at a time and the links
        are pressed in whatever order somebody likes, so a pitch nobody
        has played yet is an open question rather than a failure.
        """
        rate = self._block.sample_rate if self._block is not None else 0.0
        count = self._block.count if self._block is not None else 0

        found = []
        for hz in protocol.PITCHES:
            best = self._best.get(hz)
            if best is None:
                continue
            floor, level = best
            found.append(
                protocol.Reading(
                    hz=hz,
                    bin_hz=goertzel.bin_hz(hz, rate, count),
                    floor=floor,
                    level=level,
                    heard=goertzel.is_heard(level, floor),
                    sample_rate=rate,
                )
            )
        return found

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {self._com_port.name: self._com_port}
        children.update(self._commands)
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf(
            "port",
            self.params[EarComPort.params_section]["communication port"]
            or "not set",
        )
        leaf("sketch", "Source code/Arduino/microphone_sampler/")
        if self._greeting:
            leaf("board says", self._greeting)

        refusal = self._why_not_open()
        leaf("can read", "yes" if refusal is None else f"no - {refusal}")

        sound = self._why_no_sound()
        leaf("can play", "yes" if sound is None else f"no - {sound}")

        if self._tone.hz is None:
            leaf("sounding", "nothing")
        else:
            leaf(
                "sounding",
                f"{self._tone.hz} Hz (actually {self._tone.played_hz:.1f} Hz)",
            )

        if self._block is not None:
            width = goertzel.bin_width(self._block.sample_rate, self._block.count)
            leaf(
                "capture",
                f"{self._block.count} samples at "
                f"{self._block.sample_rate:.0f} a second, so a bin "
                f"{width:.1f} Hz wide",
            )
            # Not a measurement of anything, and it catches the two things
            # that read as an ordinary bin level otherwise: nothing on the
            # pin at all, and an input being clipped.
            leaf("signal span", f"{self._block.span} of 1023 ADC counts")
            leaf("blocks read", self._blocks_read)

        if self._outcome is not None:
            leaf("outcome", self._outcome)

        for hz in protocol.PITCHES:
            level = self._levels.get(hz)
            if level is None:
                continue
            parts = [f"now {level:.2f}"]
            floor = self._floors.get(hz)
            if floor is not None:
                parts.append(f"floor {floor:.2f}")
            best = self._best.get(hz)
            if best is None:
                parts.append("not played yet")
            else:
                best_floor, best_level = best
                heard = goertzel.is_heard(best_level, best_floor)
                parts.append(
                    f"best rise +{best_level - best_floor:.2f} - "
                    f"{'heard' if heard else 'NOT heard'}"
                )
            leaf(f"{hz} Hz", ", ".join(parts))

        return states
