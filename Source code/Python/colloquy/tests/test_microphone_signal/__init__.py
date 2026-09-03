# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_microphone_signal/__init__.py

"""Is a microphone producing a signal at all?

Every other test of the sound channel reads the **analyser**, which is
the next link along from the microphone, so none of them can answer
this. `test_audio_loop` grades the twenty-five-verdict grid and
`test_audio_bringup` takes the chain apart by arranging for the faults
to have different shapes - but both of them are looking at seven band
values out of an MSGEQ7, and a microphone producing nothing looks
exactly like a microphone whose signal never reaches the MSGEQ7 from
there. `diagnosis.py` says as much about itself: three faults it cannot
separate, and it asks a person to listen rather than pretending
otherwise.

**This test cuts the chain at the MSGEQ7's input**, which is the one
place it can usefully be cut, for two reasons that are both about this
board rather than about testing in general:

- The microphone wire arrives on `J11`'s **odd** pin and nothing at all
  is fitted between it and the DSUB - `as built` section 6, "no
  microphone conditioning of any kind". So the odd pin *is* the
  MAX9814's output, reachable with a clip.
- The MSGEQ7's own support network is the one part of this design
  recorded nowhere in this repository (`next pcb` keeps it in its own
  BOM section for exactly that reason). It is therefore the most likely
  thing to be wrong and the least likely thing to be caught by anything
  reading its output.

**Where the clip goes now: straight onto `A0`.** With the analyser
array out of the rack (`hardware > electronics`, and the reason the
audio subsystem came off at all), `A0`-`A4` are five ADC pins on the
installation's own Mega with nothing driving them. So the microphone
goes directly onto `A0` and there is nothing to unsolder, no shunt to
lift off `J11` and no photosensor to borrow - and `microphone_plotter`
already ships reading `A0`, so there is nothing to edit in the sketch
either. It is the cheapest route this test has ever had, and it exists
only because the array is out; put the array back with a microphone
still on `A0` and an MSGEQ7 output is driving the same node as a
MAX9814 output. `plotter setup` opens on that.

**What it costs is this run's own half**, and for a blunter reason than
before. The photosensor route lost it because the plotter sketch drives
neither strobe nor reset; this one loses it twice over, because there
are no analysers plugged in to be strobed. So on this route the table
below has one row - the plot moves or it does not - and the run on the
page is there to say so rather than to be read.

**And it reflashes the installation's own Mega**, which is why
`flash colloquy firmware back` is on this node. Putting firmware 4 back
was a paragraph in a document pointing at a page three levels away; it
is one press from here now, and it ends by reopening the port, so the
outcome line is the board saying in its own words which firmware it is
running.

**The instrument is your eyes on the Arduino IDE's Serial Plotter**, and
that is why this is a manual test rather than an autotest. Music from a
phone played into a body paints a shape anybody recognises in a second;
no arrangement of band numbers is as convincing, and none of it can be
written to a file by this process, because the trace is on a port this
process is deliberately not holding. See `plotter setup`, which hangs
here for `SUPPLY_SETUP.md`'s reason - the moment somebody needs telling
is the moment they are about to clip a lead onto something.

**What the run itself does is the other half of the split.** While you
play music, it holds every speaker silent and reads all five analyser
modules over and over, showing what each one makes of the same sound.
Put beside the plotter, that is the whole diagnosis on one screen:

| plotter | analyser bands | where the fault is |
|---|---|---|
| moves with the music | move too | not here - go on to `test audio bringup` |
| moves with the music | flat | between the microphone wire and the MSGEQ7: its input network, its supply, or the strobe |
| flat | flat | the microphone, its supply, or the wire back to the body |

Nothing is written down, and that is deliberate rather than an omission.
Half of this measurement is on a screen this software cannot see, so a
file holding only the other half would be a record of the half that was
never in doubt.
"""
from time import time

from colloquy.base_thread import BaseThread
from colloquy.drivers import audio
from colloquy.drivers.arduino import firmware
from colloquy.ui import leaves

from . import plotter_sketch
from .plotter_document import MicrophonePlotter


class TestMicrophoneSignal(BaseThread):
    """Every ear read on a loop, while you play music at one of them."""

    scenario_names = ("microphone-signal-test",)

    # Twice a second. The MSGEQ7 holds a peak with its own decay and the
    # firmware throws ten sweeps away before the one it returns, so a
    # sweep costs about eight milliseconds and asking faster than this
    # would buy nothing but a busier link. Much slower and a passage of
    # music passes between two readings.
    READ_INTERVAL = 0.5

    def __init__(self, owner):
        super().__init__(owner=owner)

        # How to wire it, which of the two ways to do it, and what each
        # shape on the plot means.
        self._document = MicrophonePlotter(owner=self)

        self._last = None
        self._peaks = {}
        self._sweeps = 0
        self._outcome = None
        self._last_read_at = 0.0

        # Registered as well as drawn: registering is what makes it
        # reachable by path, snapshot_children is what draws it.
        self["flash colloquy firmware back"] = self.flash_firmware_back

    @property
    def name(self):
        return "test microphone signal"

    @property
    def flasher(self):
        return self.drivers.arduino.flasher

    @property
    def plotter_sketch(self):
        """What `microphone_plotter` would sample if flashed now.

        Read out of the .ino rather than restated, because the pin the
        clip is on and the pin the sketch reads have to be the same pin
        and nothing says so when they are not - see plotter_sketch.py.
        """
        return plotter_sketch

    @property
    def wired_bodies(self):
        """The bodies whose analyser input is actually connected.

        Read on every use rather than kept, as everywhere else: an
        unwired analyser input is a floating ADC pin, and a floating pin
        does not read silence - it reads garbage. Which bodies those are
        changes as channels go in, and that list is the one place it is
        said.
        """
        return tuple(self.colloquy.params["audio"]["wired bodies"])

    # --- the run ----------------------------------------------------------

    def setup(self):
        self._last = None
        self._peaks = {}
        self._sweeps = 0
        self._outcome = None
        self._last_read_at = 0.0

        # The room has to hold only the sound you are playing into it.
        # The piece's own five tones would be picked up by every module
        # and would make the analyser half of this unreadable - and a
        # body singing while you hold a phone to its microphone is the
        # piece hearing itself, which is a different test entirely
        # (`test audio loop`).
        try:
            self.drivers.audio.silence()
        except Exception as error:
            self._refuse(f"could not silence the speakers: {error}")

    def setdown(self):
        # Nothing to put back. Nothing moved, nothing was lit, and the
        # speakers are meant to be left silent.
        pass

    def loop(self):
        now = time()
        if (now - self._last_read_at) < self.READ_INTERVAL:
            return
        self._last_read_at = now

        try:
            readings = self.drivers.audio.read_all()
        except Exception as error:
            # Almost always one thing, and it is worth naming rather than
            # letting it arrive as a traceback: the installation's own
            # Mega is running the plotter sketch instead of firmware 4,
            # which is what both of the routes that borrow that board do
            # to it. Either gives up this half of the test by
            # construction - see `plotter setup` - so this is a
            # documented way to use this test rather than a fault, and
            # the sentence says which press undoes it.
            self._refuse(
                f"could not read the analysers: {error}. If the plotter "
                "sketch is on the board, that is expected on this route - "
                "'flash colloquy firmware back' puts firmware 4 on it."
            )
            return

        self._last = readings
        for name, values in readings.items():
            previous = self._peaks.get(name)
            if previous is None:
                self._peaks[name] = values
            else:
                self._peaks[name] = tuple(map(max, previous, values))
        self._sweeps += 1

    def _refuse(self, reason):
        self._outcome = f"stopped: {reason}"
        self.log(self._outcome)
        self.stop()

    def forget_the_peaks(self, request=None):
        """Throw the running maxima away.

        Worth a button because a peak is cumulative and the whole use of
        it is comparing one body against another: a spike from clipping
        the probe on, or from the first track being louder than the
        second, sits in that column for the rest of the run and quietly
        makes one ear look better than its neighbour.
        """
        self._peaks = {}
        return "peaks forgotten"

    def flash_firmware_back(self, request=None):
        """Put the piece's own firmware back on the installation's Mega.

        The one press this test owes anybody who followed it. Both of the
        routes that use the installation's own board leave
        `microphone_plotter` on it, and until firmware 4 is back the
        driver will not open the link at all - so the page that carries
        the fix used to be three levels away from the page that told you
        to break it.

        **It delegates rather than deciding.** `drivers > arduino >
        flash firmware` already knows every reason not to flash - an
        unmounted PCB, an unchosen port, a port this machine does not
        have, a port that is not a plausible Arduino, anything under
        `drivers` or `tests` still running - and every one of those
        refusals is instant and reads last-known state. Re-stating any of
        them here would be a second copy to drift, and a weaker one: only
        the flasher knows what is on the USB bus. So this returns the
        flasher's own sentence, whichever it is.

        The last of those refusals catches this very test if it is still
        running, which is right rather than awkward: the board spends
        twenty seconds in its bootloader answering nothing. On the `A0`
        route it will have stopped itself already, because a run that
        cannot read the analysers says so and stops.
        """
        return self.flasher.flash()

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return self._with_scenarios(
            {
                self._document.name: self._document,
                "forget the peaks": self.forget_the_peaks,
                # Always offered, never hidden behind a check of its own.
                # The flasher answers a press it will not act on with the
                # reason, in the same request; a link that vanished
                # exactly when the board was in the state this test puts
                # it in would be the wrong way round.
                "flash colloquy firmware back": self.flash_firmware_back,
            }
        )

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        # Said before any number, as everywhere in the sound channel. The
        # stand-in answers a sweep with entirely plausible numbers, so a
        # simulated run and a real one read alike - and there is no
        # phone and no microphone anywhere in a simulated one.
        leaf(
            "board",
            "the stand-in - there is no microphone behind these numbers"
            if self.drivers.arduino.is_using_the_stand_in
            else "a real board on this lead",
        )
        wired = self.wired_bodies
        leaf("wired bodies", ", ".join(wired) or "none")
        unwired = [name for name in audio.BODIES if name not in wired]
        if unwired:
            leaf(
                "not wired",
                f"{', '.join(unwired)} - a floating ADC pin reads garbage "
                "rather than silence, so ignore those rows",
            )

        # The pin the sketch will sample, out of the sketch. On the `A0`
        # route this is the whole of the wiring instruction, and a sketch
        # still set to `A5` from the photosensor route plots a floating
        # pin - which section 6 lists as a failure shape in its own right.
        try:
            leaf("plotter sketch", plotter_sketch.describe())
        except (OSError, RuntimeError) as error:
            leaf("plotter sketch", f"could not be read: {error}")

        if wired:
            leaf(
                "the other half",
                "the trace in the Arduino IDE's Serial Plotter. Bands that "
                "move with the music say the whole chain works; bands that "
                "stay flat while the plotter moves put the fault between the "
                "microphone wire and the MSGEQ7. See 'plotter setup'.",
            )
        else:
            # Which is the state the `A0` route is run in: no analysers in
            # the rack at all. Promising a second half that cannot exist
            # would have somebody waiting for bands to move.
            leaf(
                "the other half",
                "none on this route - with no analyser wired there is "
                "nothing to read against the plot, so the trace in the "
                "Serial Plotter is the whole measurement. See "
                "'plotter setup'.",
            )

        # What the board on the other end says it is. This is how you
        # know the flash back worked, and it is the same sentence the
        # flasher ends on, from the same place.
        leaf("board says", firmware.describe(self.drivers.arduino.greeting))
        if self.flasher.is_started:
            leaf("flashing", "in progress - refresh in a moment")
        if self.flasher.outcome is not None:
            leaf("last flash", self.flasher.outcome)

        if self._outcome is not None:
            leaf("outcome", self._outcome)

        if self._last is None:
            leaf("sweeps", "none yet - press start")
            return states

        leaf("sweeps", self._sweeps)
        leaf("bands", " ".join(f"{hz}Hz" for hz in audio.BANDS_HZ))
        for name in audio.BODIES:
            leaf(name, " ".join(str(value) for value in self._last[name]))
            leaf(
                f"{name} peak",
                " ".join(str(value) for value in self._peaks.get(name, ())),
            )
        return states
