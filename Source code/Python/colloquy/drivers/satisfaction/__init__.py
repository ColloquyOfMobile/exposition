# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/satisfaction/__init__.py

"""The six seconds after an appetite is met - the melody, and her answer
to it in light.

The only moment in the piece where a body has what it wanted, and the
only sound a male makes that is not a message. Before this it was six
silent, dark seconds: the drive was zeroed and both bodies simply stood
still, which is the arithmetic of TJ's moment without any of its
expression.

**Fifteen notes, and the pair keeps one clock.** `act_satisfaction_vals`
is the tune; the note *lengths* are per male and both tables sum to
exactly 120 ticks of his 50 ms clock, which is the six seconds:

- **male1 taps it out evenly** and holds the last three - `{5 x 12, 10,
  20, 30}`, so a quarter of a second a note until half a second, one
  second, one and a half.
- **male2 swings it**, long-short-long-short - `{10, 5, 10, 5, ...}` -
  and holds only the last, for three quarters of a second.

**The female plays the same rhythm as light rather than as sound**, and
she takes it from *her partner's* table rather than her own
(`internal_partner_ID` in `Logic_fem.ino`). So the two are in step
without either following the other: she uses his note lengths, and which
male it was decides the rhythm both of them keep. Each note is a ramp
from dark to full across her whole body, in the colour of the appetite
they shared - orange for O, the greenish puce for P.

**One divergence, and it is the firmware's.** His fifteen notes are
fifteen *pitches*: 80, 160, 551, 926 Hz to open, then a bright
alternation of 2300 and 3700. A body here has exactly one pitch, fixed by
which hardware timer drives its pin (`drivers/audio.py`, and `Speaker`'s
docstring on why there is no pitch control). So a male keys **his own
tone on and off to the same rhythm** - the shape of the melody without
its tune. Giving it back means the sketch driving OCR values per note
rather than one per body, which is a firmware change and not a wire.
"""
from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

# One tick of TJ's clock, and what the fifteen notes are worth in it.
TICK = 0.05

# `act_satisfaction_vals` - his tune. Carried whole even though nothing
# here can play the pitches, because the day a body can choose a note is
# the day this becomes the table to read.
NOTES_HZ = (80, 160, 80, 551, 80, 926, 2300, 3700, 2300, 3700, 2300, 3700,
            2300, 3700, 2300)

# `act_satisfaction_Durations_I` and `_II`, in ticks. Both sum to 120.
DURATIONS = {
    "male1": (5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10, 20, 30),
    "male2": (10, 5, 10, 5, 10, 5, 10, 10, 10, 10, 5, 5, 5, 5, 15),
}

# The whole moment, and the sum of either table above.
TOTAL_TICKS = 120
DURATION = TOTAL_TICKS * TICK


def durations_for(male_name):
    """The note lengths this pair keeps, in seconds.

    Keyed by the *male*, whichever body is asking: she takes her rhythm
    from her partner, which is what puts the two of them in step.
    """
    return tuple(ticks * TICK for ticks in DURATIONS.get(male_name, DURATIONS["male2"]))


def note_at(elapsed, male_name):
    """(index, how far through it) at `elapsed` seconds, or None past the end.

    The fraction is what her brightness ramps over - TJ's
    `(timer_satisfactionanimation * 256) / act_satisfaction_Duration`.
    """
    start = 0.0
    for index, length in enumerate(durations_for(male_name)):
        if elapsed < start + length:
            return index, (elapsed - start) / length
        start += length
    return None


class Satisfaction(BaseThread):
    """One body's six seconds, started by its own `Reinforcement`."""

    scenario_names = ("the-satisfaction-moment",)

    def __init__(self, owner):
        self._name = f"satisfaction {owner.name}"
        super().__init__(owner=owner)
        self._male_name = None
        self._drive_name = None
        self._started_at = None
        self._note = None

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self.owner

    @property
    def is_female(self):
        return self.body.name.startswith("female")

    def about(self, male_name, drive_name):
        """Whose rhythm, and which appetite's colour. Set before start()."""
        self._male_name = male_name
        self._drive_name = drive_name

    @property
    def note(self):
        return self._note

    @property
    def elapsed(self):
        return 0.0 if self._started_at is None else time() - self._started_at

    # --- the run ----------------------------------------------------------

    def setup(self):
        if self._male_name is None:
            raise ValueError(
                f"{self.body.name}'s satisfaction has no partner's rhythm to keep."
            )
        self._started_at = time()
        self._note = None

    def loop(self):
        found = note_at(self.elapsed, self._male_name)
        if found is None:
            self.stop()
            return

        index, through = found
        if self.is_female:
            self._light(through)
        else:
            self._sound(index)
        self._note = index

    def _light(self, through):
        """Dark to full across this note, in the shared appetite's colour.

        Her whole body, not one segment: the drive lights say what she
        wants, and for these six seconds she does not want anything.
        """
        brightness = int(through * 100)
        pixels = self.body.neopixels
        colour = self._colour()
        for segment in (pixels.body_o, pixels.body_p):
            segment.color = colour
            segment.brightness.value = brightness

    def _colour(self):
        drives = self.body.drives
        return drives.puce if self._drive_name == "P" else drives.orange

    def _sound(self, index):
        """His own pitch, keyed to the rhythm - see the module docstring
        on why it is not the tune."""
        if index == self._note:
            return
        # A note begins: on for this one, and the gap between notes is
        # the note boundary itself rather than a rest.
        self.body.speaker.on()

    def setdown(self):
        # Must not raise - BaseThread calls this from a finally block, and
        # the lights and the tone both have to come off whatever happened.
        for what, action in self._quieting():
            try:
                action()
            except Exception as error:  # noqa: BLE001
                self.log(f"Could not put out {self.body.name}'s {what}: {error}")
        self._started_at = None
        self._note = None

    def _quieting(self):
        if self.is_female:
            pixels = self.body.neopixels
            return (
                ("body O", pixels.body_o.off),
                ("body P", pixels.body_p.off),
            )
        return (("tone", self.body.speaker.off),)

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return self._with_scenarios({})

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if not self.is_started:
            return states

        leaf = leaves.into(states, path)
        leaf("keeping", f"{self._male_name}'s rhythm")
        leaf("appetite", f"{self._drive_name} - {'puce' if self._drive_name == 'P' else 'orange'}")
        leaf("note", f"{self._note + 1} of {len(NOTES_HZ)}" if self._note is not None else "-")
        leaf("left", f"{max(DURATION - self.elapsed, 0):.1f}s")
        return states
