# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_at_12v/__init__.py

"""Does raising the amplifier supply actually make the piece louder?

`next pcb` section 5 has already decided that all five amplifiers run
from **+12 V**, and decided it on arithmetic: the same acoustic power at
roughly 40% of the current, on a conductor the NeoPixels do not touch.
The decision is not what this test is for. What is still open there is
one of the three remaining measurements - *how much louder, in fact* -
and that is a thing you find out by putting a meter and an ear on a
bench, not by reading a data sheet.

**This is a manual test, and the manual part is not incidental.** No
software anywhere in this repo can move the amplifiers' supply lead.
So the run comes in two halves with a screwdriver between them: one
pass at the supply you have now, one pass at the supply you are asking
about, and a comparison the test can only make once it has both. The
two commands are `measure at 5 V` and `measure at 12 V`; a bare `start`
is popped for the flasher's reason - it would be a button that does one
of two things and does not say which.

**The MAX9814's automatic gain control is the whole difficulty**, and a
test that reported only a band level would lie about this cheerfully.
The AGC exists to hold the output roughly constant against exactly the
change being measured: make the room twice as loud and it turns itself
down. So a flat reading is *not* evidence that nothing changed, and a
run that reported one would talk somebody out of a decision that has
already been taken on better grounds.

Two numbers are recorded per tone because of it:

- **rise** - the tone's own band, over that band's level in silence.
  Direct, easy to read, and the one the gain control compresses.
- **share** - the tone's band as a fraction of all seven bands added up.
  This one largely survives the AGC, and the reason is what the AGC
  does: it holds the *total* near constant, so a tone that is genuinely
  louder in the room takes a larger fraction of that total while the
  room noise in the other six bands is turned down with it. A share
  that climbs while the rise does not is the signature of a working
  amplifier behind a gain control doing its job.

Neither is a sound pressure measurement and this file should not be read
as claiming otherwise. **The verdict that settles it is your ear**, and
the manual tone-hold commands are here so you can use it: hold one tone,
change the supply, listen. The numbers are here to be written down
beside what you heard.

**One line per tone, not twenty-five.** `test_audio_subsystem` asks
which module hears which tone and needs the whole grid for it. The
question here is about five amplifiers on one rail, so each tone is
reported by the *best* rise any module gave it - "how loud did this get
in the room" - and which module that was is the sibling test's business.
"""
import math

from datetime import datetime
from functools import partial
from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

from ..bench_board import BenchBoardLink
from ..bench_com_port import BenchComPort
from ..test_audio_subsystem import protocol

from .setup_document import SupplySetup


class SupplyComPort(BenchComPort):
    """Which port Thomas's board is on.

    Deliberately the *same* params key as `test audio subsystem`: it is
    the same board on the same lead, and having chosen it once on one
    page only to be asked again on the next is the kind of small lie
    about the hardware that this tree is meant not to tell.
    """

    params_section = "audio subsystem"
    stand_in = "simulated audio port"


# The two supplies, and the order the page lists them in. The label is
# what a pass is filed under - what is actually on the rail is whatever
# you wired - but the volts are needed too, because a pass is now refused
# when the module fitted is not known to survive it. See `_why_not_measure`
# and docs/errors/2026-09-01-01.txt.
SUPPLIES = ("5 V", "12 V")
SUPPLY_VOLTS = {"5 V": 5.0, "12 V": 12.0}


class TestAudioAt12V(BenchBoardLink, BaseThread):
    """Two passes over Thomas's five tones, one per amplifier supply."""

    scenario_names = ("audio-supply-test",)

    # As `test_audio_subsystem`, and for its reasons: long enough for a
    # person to hear the tone and place it in the room.
    TONE_SECONDS = 3.0

    # Longer than the sibling test's 0.7, and the AGC is why. The MSGEQ7's
    # own decay is what 0.7 was sized for; here the microphone's gain
    # control has also just been handed a step change in level and has to
    # settle *both* ways - fast coming down at 1:500, slower going back
    # up. A reading taken during that is a reading of the gain control.
    SETTLE_SECONDS = 1.5

    # See protocol's module docstring: readSerial() prints the prompt and
    # then resets the port, so a command sent the instant it appears can
    # vanish.
    PROMPT_SETTLE = 0.2

    REPLY_TIMEOUT = 5.0

    # How far a band has to rise over its own silence before the tone
    # counts as present at all. Same blunt number as the sibling test -
    # it is here to reject drift, not to measure anything.
    MARGIN = 60

    # How much of a change is worth calling a change. Two passes minutes
    # apart in a room with people in it do not repeat to better than this,
    # and reporting 0.4 dB as an improvement would be inventing precision
    # the bench does not have.
    DB_NOISE_FLOOR = 1.5

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._port_handler = None
        self._com_port = SupplyComPort(owner=self)
        self[self._com_port.name] = self._com_port

        # How to wire it, and how not to destroy anything doing so. It
        # hangs here rather than on the root for `HardwareSetup`'s reason:
        # the moment somebody needs telling is the moment they are about
        # to press one of the two buttons below it.
        self._setup = SupplySetup(owner=self)

        # The two halves of the run. Each is the same sweep; which one it
        # is, is the label it writes its numbers under.
        self._commands = {
            f"measure at {supply}": partial(self._measure, supply)
            for supply in SUPPLIES
        }
        self._commands["forget both passes"] = self._forget

        # For the ear, which is the instrument that actually settles this.
        # Hold a tone, change the supply under it, listen.
        self._manual = {}
        for timer in protocol.TIMERS_BY_PITCH:
            hz = protocol.TIMERS[timer]["hz"]
            pin = protocol.TIMERS[timer]["pin"]
            self._manual[f"hold {hz} Hz on ({pin})"] = partial(
                self._send_manual, protocol.enable(timer)
            )
        self._manual["silence"] = partial(self._send_manual, protocol.disable("a"))

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._supply = None
        self._queue = None
        self._current = None
        self._silence = None
        # {supply: {timer: {"rise": float, "share": float, "module": int}}}
        self._results = {}
        self._outcome = None
        self._manual_reply = None
        self._buffer = ""

    @property
    def name(self):
        return "test audio at 12v"

    @property
    def params(self):
        # The board's own settings sit at the root of params.json beside
        # the installation's Arduino, not under "tests" - it is a piece of
        # hardware on a bench, not a knob on one run.
        return self.colloquy.params

    @property
    def com_port(self):
        return self._com_port

    @property
    def baudrate(self):
        return self.params["audio subsystem"]["baudrate"]

    # `board_is_real`, `port_handler` and `use_port` come from
    # BenchBoardLink. They asked `is_bench`, which is the one machine this
    # test is least likely to be run on: the supply being changed is the
    # piece's, so the board comes to the installation's laptop. A run
    # against the stand-in produces two passes that differ by nothing,
    # which reads exactly like a bench where 12 V bought you nothing - so
    # which board answered is said on the page before any number is.

    # --- the line ---------------------------------------------------------

    def _write(self, command):
        self.log(f"> {command}")
        self.port_handler.write(
            (command + protocol.LINE_ENDING).encode("ascii", "replace")
        )

    def _read_until(self, tail, timeout=None):
        deadline = time() + (self.REPLY_TIMEOUT if timeout is None else timeout)
        collected = ""
        while time() < deadline:
            if self._stop_event.is_set():
                return None
            chunk = self.port_handler.read(256)
            if chunk:
                collected += chunk.decode("ascii", "replace")
                if protocol.strip_ansi(collected).rstrip(" ").endswith(
                    tail.rstrip(" ")
                ):
                    return collected
        return None

    def _command(self, command):
        self._settle(self.PROMPT_SETTLE)
        self._write(command)
        return self._read_until(protocol.PROMPT)

    def _settle(self, seconds):
        """Wait without going deaf - the board talks when it likes."""
        deadline = time() + seconds
        while time() < deadline and not self._stop_event.is_set():
            chunk = self.port_handler.read(256)
            if chunk:
                self._buffer += chunk.decode("ascii", "replace")

    def _send_manual(self, command, request=None):
        """One command from the page, with or without a pass running.

        Same arrangement as the sibling test's: opening the port resets
        the board, so a held tone borrows the line a run already has
        rather than taking a second one and silencing itself.
        """
        was_open = self._port_handler is not None and self.port_handler.is_open
        if not was_open:
            refusal = self._why_not_open()
            if refusal is not None:
                self._manual_reply = f"refused: {refusal}"
                return self._manual_reply
            self.port_handler.open()
            self._read_until(protocol.PROMPT, timeout=8.0)
        self._settle(self.PROMPT_SETTLE)
        self._write(command)
        reply = self._read_until(protocol.PROMPT, timeout=3.0)
        self._manual_reply = protocol.strip_ansi(reply).strip() if reply else "no reply"
        if not was_open and not self.is_started:
            # Left open while a tone is held: closing resets the board and
            # would silence the very tone just asked for. Changing the
            # supply under a held tone is the point of these commands.
            if command == protocol.disable("a"):
                self.port_handler.close()
        return self._manual_reply

    # --- the two passes ---------------------------------------------------

    @property
    def amplifier(self):
        """The module recorded as fitted, and the rail it survives."""
        audio = self.params["audio"]
        return audio["amplifier module"], float(audio["amplifier max supply volts"])

    def _why_not_measure(self, supply):
        """Why this pass would destroy something, or None.

        **This test used to be able to break the hardware it measures**,
        and on 2026-09-01 it did: `measure at 12 V` was pressed with
        Thomas's GF1002s fitted and one died the instant the rail came
        up. It was not a wiring mistake - the wiring was this document's
        own - it was a number nobody had a source for. `SUPPLY_SETUP.md`
        said the module was "specified 4.5-15 V", having taken that from
        `next pcb` section 5, where it was a *specification for a module
        still to be bought* rather than a fact about the ones on the
        bench. The two claims read alike and are not the same sentence.

        So the rating is now a recorded fact about the module in your
        hand (`params > audio`), the refusal is instant and reads only
        that, and raising it is a deliberate press against a datasheet
        rather than against another document in this repository.
        """
        module, rated = self.amplifier
        volts = SUPPLY_VOLTS[supply]
        if volts > rated:
            return (
                f"the amplifier module recorded as fitted is a {module}, known "
                f"to survive {rated:g} V, and this pass needs {volts:g} V. A "
                "GF1002 was destroyed instantly at 12 V on 2026-09-01 "
                "(docs/errors/2026-09-01-01.txt) - the 4.5-15 V this test used "
                "to claim was never sourced. Fit a module rated for the rail "
                "and record it under params > audio > amplifier module."
            )
        return None

    def _measure(self, supply, request=None):
        """Run one pass, under the label of the supply now on the rail."""
        if self.is_started:
            self._outcome = "a pass is already running - let it finish or stop it"
            return self._outcome
        refusal = self._why_not_measure(supply)
        if refusal is not None:
            self._outcome = f"refused: {refusal}"
            self.log(self._outcome)
            return self._outcome
        self._supply = supply
        self.start(started_by=None)
        return f"measuring at {supply}"

    def _forget(self, request=None):
        """Throw both passes away.

        Worth a button because the failure it prevents is a quiet one: a
        5 V pass from before somebody moved a microphone, compared against
        a 12 V pass from after, reads as a beautifully convincing result.
        """
        self._results = {}
        self._outcome = "both passes forgotten"
        return self._outcome

    def run(self):
        now = datetime.now()
        label = (self._supply or "unknown").replace(" ", "")
        file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_"
            f"{now.minute:02}min_{now.second:02}s_{label}.csv"
        )
        run_with = self._file = file_path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._start_time = time()
        self._silence = None
        self._outcome = None
        self._buffer = ""
        self._file.write(
            "seconds, supply, tone, module, "
            + ", ".join(f"{hz} Hz" for hz in protocol.BANDS_HZ)
            + "\n"
        )

        refusal = self._why_not_open()
        if refusal is not None:
            self._refuse(refusal)
            return

        self.port_handler.open()

        # Opening the port resets the board and it prints its banner. That
        # banner is what says this is Thomas's tester and not the
        # installation's own Arduino on the next socket down, which
        # answers JSON and would sit there silently failing to be a menu.
        banner = self._read_until(protocol.PROMPT, timeout=8.0)
        if banner is None or protocol.BANNER not in protocol.strip_ansi(banner):
            self._refuse(
                "no audio tester on that port - expected the welcome banner "
                f"({protocol.BANNER!r}) and got {banner!r}"
            )
            return

        self._results[self._supply] = {}
        self._queue = [None] + list(protocol.TIMERS_BY_PITCH)
        self._advance()

    def setdown(self):
        self._start_time = None
        self._current = None
        if self._port_handler is not None and self.port_handler.is_open:
            # Quiet whatever happened, including a stop half way. Five
            # tones left sounding is not a state to walk away from - and
            # here it would be five tones sounding while somebody has a
            # screwdriver on the supply.
            self._write(protocol.disable("a"))
            self._read_until(protocol.PROMPT, timeout=2.0)
            self.port_handler.close()
        if self._file is not None:
            self._file.close()

    def _why_not_open(self):
        """Why opening the line would fail, or None if it would not.

        Instant, and reading only what is already known, so the buttons
        can ask before they touch pyserial - a `SerialException` out of a
        request used to be read by the server as a crash worth stopping
        the installation over.
        """
        chosen = self.params["audio subsystem"]["communication port"]
        if chosen is None:
            return "no port chosen - pick Thomas's board under 'com port'"

        available = self.com_port.ports
        if chosen not in available:
            return (
                f"{chosen!r} is not a port on this machine - available: "
                f"{', '.join(available) or 'none, is the board plugged in?'}"
                " - pick one under 'com port'"
            )
        return None

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
            self._record(timer, averages)

        self._advance()

    def _collect(self, label):
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
                f"{elapsed}, {self._supply}, {label}, {module}, "
                + ", ".join(str(value) for value in values)
                + "\n"
            )
        return readings

    def _record(self, timer, averages):
        """Keep this tone's best rise, and the share that goes with it.

        "Best across the five modules" rather than one line per pair: the
        question is how loud this tone got in the room, and which module
        heard it best is `test audio subsystem`'s business, not this
        one's.
        """
        band = protocol.expected_band(timer)
        best = None
        for module, values in averages.items():
            silence = (self._silence or {}).get(module)
            if silence is None:
                continue
            rise = values[band] - silence[band]
            if best is None or rise > best["rise"]:
                best = {
                    "rise": rise,
                    "share": _share(values, band),
                    "silent share": _share(silence, band),
                    "module": module,
                }
        if best is not None:
            self._results[self._supply][timer] = best

    # --- what the two passes say together ---------------------------------

    def _summary(self):
        measured = self._results.get(self._supply, {})
        heard = sum(1 for best in measured.values() if best["rise"] >= self.MARGIN)
        line = f"{self._supply}: {heard}/{len(measured)} tones heard"
        if len(self._results) < len(SUPPLIES):
            missing = [s for s in SUPPLIES if s not in self._results]
            return f"{line} - now change the supply and measure at {missing[0]}"
        return f"{line} - both passes in, see the comparison below"

    def _comparison(self):
        """One row per tone, or None until both passes exist."""
        if any(supply not in self._results for supply in SUPPLIES):
            return None

        rows = {}
        low, high = SUPPLIES
        for timer in protocol.TIMERS_BY_PITCH:
            hz = protocol.TIMERS[timer]["hz"]
            before = self._results[low].get(timer)
            after = self._results[high].get(timer)
            if before is None or after is None:
                rows[hz] = "not measured in both passes"
                continue

            if before["rise"] < self.MARGIN and after["rise"] < self.MARGIN:
                # Silent either way. On this bench that is almost always a
                # channel nobody has wired yet, and it is emphatically not
                # a statement about the supply.
                rows[hz] = (
                    "not heard at either supply - nothing to compare "
                    "(an unwired channel looks exactly like this)"
                )
                continue

            rows[hz] = self._describe(before, after)
        return rows

    def _describe(self, before, after):
        louder = _decibels(before["rise"], after["rise"])
        share_change = after["share"] - before["share"]

        parts = [
            f"rise {before['rise']:.0f} -> {after['rise']:.0f}",
            f"share {before['share']:.2f} -> {after['share']:.2f}",
        ]
        if louder is not None:
            parts.append(f"{louder:+.1f} dB")

        # The two readings and what their disagreement means. This is the
        # whole reason `share` is recorded at all - see the module
        # docstring on the AGC.
        if louder is not None and louder >= self.DB_NOISE_FLOOR:
            parts.append("louder")
        elif share_change >= 0.05:
            parts.append(
                "louder in the room, held down by the gain control - the "
                "band took a larger share while its level did not move"
            )
        elif louder is not None and louder <= -self.DB_NOISE_FLOOR:
            parts.append("QUIETER - check the wiring before believing it")
        else:
            parts.append(
                "no change this bench can resolve - listen to it before "
                "concluding there is none"
            )
        return "; ".join(parts)

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {
            self._com_port.name: self._com_port,
            self._setup.name: self._setup,
        }
        children.update(self._commands)
        children.update(self._manual)
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        # A bare `start` would be a button that runs one of two passes
        # without saying which, and the label is the entire content of the
        # measurement. `stop` stays - a pass at the wrong supply is worth
        # being able to abandon. Same reasoning as the flasher's.
        states.pop("start", None)

        into = leaves.into(states, path)

        into(
            "board",
            "real, on this machine" if self.board_is_real else "simulated stand-in",
        )
        into("port", self.params["audio subsystem"]["communication port"])

        # Said before any number, like `board` above and for the same
        # kind of reason: the pass somebody is about to press is refused
        # or not on the strength of this one line.
        module, rated = self.amplifier
        into("amplifier fitted", f"{module}, known to survive {rated:g} V")
        blocked = [
            supply for supply in SUPPLIES if self._why_not_measure(supply) is not None
        ]
        if blocked:
            into("refusing", f"{', '.join(blocked)} - see this node's setup document")
        into(
            "passes recorded",
            ", ".join(supply for supply in SUPPLIES if supply in self._results)
            or "none yet",
        )
        if self._outcome is not None:
            into("outcome", self._outcome)
        if self._manual_reply is not None:
            into("last command", self._manual_reply)
        if self._current is not None:
            hz = protocol.TIMERS[self._current]["hz"]
            into("now sounding", f"{hz} Hz ({protocol.TIMERS[self._current]['pin']})")

        comparison = self._comparison()
        if comparison is None:
            into(
                "how to read it",
                "two passes with a screwdriver between them. Measure at the "
                "supply you have, change it, measure again - the comparison "
                "appears once both are in. The gain control in the "
                "microphone flattens 'rise' on purpose; 'share' is the one "
                "that survives it, and your ear settles it.",
            )
        else:
            for hz, row in comparison.items():
                into(f"{hz} Hz", row)

        return states


def _share(values, band):
    """One band as a fraction of all seven added up.

    The reading that survives the microphone's automatic gain control.
    The AGC holds the *total* roughly constant, so it cannot hide a tone
    taking a larger fraction of that total - which is what a genuinely
    louder tone in the same room does, the other six bands being turned
    down along with everything else.
    """
    total = sum(values)
    if total <= 0:
        return 0.0
    return values[band] / total


def _decibels(before, after):
    """How much louder, or None when the before reading cannot carry it.

    A rise at or below zero is a tone that was not there to begin with,
    and dividing by it produces a number that looks like a measurement.
    """
    if before <= 0 or after <= 0:
        return None
    return 20.0 * math.log10(after / before)
