# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/recording.py

"""Every block's bin levels, and the moments somebody changed something.

The page already says what the five bins read *now*, and that is the
right thing to watch while a tone is sounding. What it cannot say is what
they read a moment before it was pressed - and that difference is the
entire measurement. A rise is a comparison between two moments, so a
reading of one moment can only ever be half of it.

So a run keeps a row per block: the seconds since it started, and each
pitch's level in that block. Four rows a second, five numbers each; a
twenty-minute session is a few thousand rows of floats, which is nothing
beside the samples they were computed from and those are thrown away
after every block as it is.

**The marks are the other half, and they are why this is worth drawing at
all.** The tone comes out of this computer's speakers because somebody
pressed a link, so the exact moment it started is known here - not
inferred from the numbers, which is what looking at a graph of levels
alone would come down to. `160 Hz on`, `silence`, `floors forgotten`:
each is written down as it happens, and `GraphView` draws them as a
dashed rule with a name on it. What you then look for is one line lifting
at one rule and the other four not, which is the claim of the whole test
in a shape an eye reads in a second.

**Nothing is written to disk, and that is the same decision as before.**
This test has no results file because the half of it that matters -
somebody hearing the tone come out of the speakers - is not a thing a
file can hold, and a file holding the other half would look like a
record of the measurement while missing the only part that was ever in
doubt. A graph beside the live readings is a way of looking at the run
that is going on, not a verdict kept after it.

Pure on purpose, like `goertzel.py` beside it: lists and floats in, lists
and floats out, no port, no thread and no clock of its own - every time
is handed in. That is what lets `pytest_tests/hardware_tests/` check the
marks land where the presses were without a board or a speaker.
"""
from colloquy.ui.graph_view import Columns


class Recording:
    """One run's levels over time, and the moments worth coming back to."""

    def __init__(self, pitches):
        self._pitches = tuple(pitches)
        self._started_at = None
        self._seconds = []
        self._levels = {hz: [] for hz in self._pitches}
        self._marks = []

    # --- the run ----------------------------------------------------------

    def start(self, now):
        """Begin a run at `now`, throwing away whatever the last one held.

        The clock is handed in rather than read here so that every time in
        the recording is on the caller's one clock - the same `time()` the
        loop uses to decide whether a block is due and the floors are
        settled. Two clocks would put a mark a few milliseconds off the
        block it belongs beside, which is exactly the distance being
        looked at.
        """
        self._started_at = now
        self._seconds = []
        self._levels = {hz: [] for hz in self._pitches}
        self._marks = []

    @property
    def is_recording(self):
        return self._started_at is not None

    def add(self, now, levels):
        """One block's five levels.

        A block that arrives before `start` is dropped rather than given a
        time of its own: the x axis is seconds since the run began, and
        there is no such thing before there is a run.
        """
        if self._started_at is None:
            return
        self._seconds.append(now - self._started_at)
        for hz in self._pitches:
            self._levels[hz].append(float(levels.get(hz, 0.0)))

    def mark(self, now, label):
        """A moment somebody caused: a tone started, or stopped.

        Silently ignored when nothing is recording, which is the ordinary
        case rather than a fault - the play links work whether the run is
        going or not, and a tone pressed with the test stopped is somebody
        checking their speakers.
        """
        if self._started_at is None:
            return
        self._marks.append((now - self._started_at, label))

    # --- what has been recorded -------------------------------------------

    def __len__(self):
        return len(self._seconds)

    @property
    def seconds(self):
        return list(self._seconds)

    @property
    def marks(self):
        """Moments, as `GraphView` wants them: (seconds, label) pairs."""
        return list(self._marks)

    @property
    def span(self):
        """How long the run has been going, in seconds."""
        if not self._seconds:
            return 0.0
        return self._seconds[-1]

    def line(self, hz):
        """One pitch's levels as (seconds, level), without building them.

        `Columns` is a view over the two lists that are already here, so
        the graph reads the few hundred rows it is going to draw and no
        pair is ever made for the rest. Same reason
        `test_with_everything_moving` hands one over its dataframe.
        """
        return Columns(self._seconds, self._levels[hz])

    def series(self):
        """Every pitch as a labelled line, in the order they are offered.

        All five, including any nobody played: a flat line under a rule
        marked `400 Hz on` is the evidence that the tone went where it was
        supposed to and nowhere else, and leaving it out would drop the
        half of the picture that says so.
        """
        return [(f"{hz} Hz", self.line(hz)) for hz in self._pitches]
