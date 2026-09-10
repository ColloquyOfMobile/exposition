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

**A run is written down, and what a file cannot hold is still not in
it.** This test kept nothing for a while, on the grounds that the half of
the measurement that matters - somebody hearing the tone come out of the
speakers - is not a thing a file can hold. That is still true and the
page still says so; what changed is that there is now something worth
filing. While a run held one best-rise number per pitch there was nothing
to compare; a few hundred rows with the presses marked on them answer the
questions actually asked between runs - is the 6250 Hz bin always the
weak one, did moving the microphone help, is it worse than it was last
week - and none of those can be answered from the one run that happens to
be in memory. Same arrangement as `test_reinforcement`'s analyser
columns: a measurement is worth recording before it is worth acting on.

**The file's shape.** One row per block - the seconds, then a level per
pitch - and **a mark gets a row of its own**, with the level columns empty
and its name in the last one. That is because a mark's whole value is
that its time is exact: it is known here, at the moment the link was
pressed, rather than inferred from the numbers, and hanging it on the next
block instead would blur it by up to a quarter of a second, which is the
distance being looked at. Rows are in time order, so the two kinds
interleave and the file reads the way the run went.

No commas in a mark's name, for `test_search`'s reason - it is the last
column of a CSV, and `test_read_pattern` already lost a column to a tuple
once. The header names the pitches, so a file written before they changed
still reads back as the pitches it actually holds rather than as whatever
`protocol.PITCHES` says today.

Pure on purpose, like `goertzel.py` beside it: lists and floats in, lists
and floats out, no port, no thread and no clock of its own - every time
is handed in. That is what lets `pytest_tests/hardware_tests/` check the
marks land where the presses were without a board or a speaker.
"""
from colloquy.ui.graph_view import Columns

# The columns either end of the file. The pitches sit between them, named
# by the header rather than assumed on the way back in.
TIME_COLUMN = "seconds"
MARK_COLUMN = "mark"


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

    # --- the file ---------------------------------------------------------

    @property
    def labels(self):
        """The pitch columns, in file order."""
        return [f"{hz} Hz" for hz in self._pitches]

    def rows(self):
        """Every line of the file, in time order, blocks and marks alike.

        Built here rather than written straight out, so the one thing a
        reader of the file relies on - the ordering - can be checked
        without a filesystem. A mark and a block never share a row: see
        the module docstring on why a mark keeps its own exact time.
        """
        blanks = [""] * len(self._pitches)
        entries = [
            (
                moment,
                0,
                [f"{self._levels[hz][index]:.4f}" for hz in self._pitches],
                "",
            )
            for index, moment in enumerate(self._seconds)
        ]
        entries += [(moment, 1, blanks, label) for moment, label in self._marks]
        # By time, and a mark at the same instant as a block goes after
        # it: the press is what caused the block, not the other way round.
        entries.sort(key=lambda entry: (entry[0], entry[1]))

        return [
            [f"{moment:.3f}"] + values + [label]
            for moment, _kind, values, label in entries
        ]

    def write(self, path):
        """The run, as one CSV. The path, or None if it held nothing.

        Nothing rather than an empty file: a run that read no blocks is a
        refusal or a pulled lead, and `results` would list it as a graph
        with no picture in it.
        """
        if not len(self._seconds):
            return None

        header = [TIME_COLUMN] + self.labels + [MARK_COLUMN]
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(", ".join(header) + "\n")
            for row in self.rows():
                handle.write(", ".join(row) + "\n")
        return path


def read(path):
    """One recorded run back: its lines and its marks.

    Returns what `GraphView` takes - `series` as (label, points) pairs and
    `marks` as (seconds, label) - so a run off the disk draws through
    exactly the same view as the one still in memory, `Columns` and all.

    The pitches come out of the **header**, not out of `protocol.PITCHES`:
    a file is a record of the run that made it, and a pitch list that
    moved afterwards must not quietly relabel somebody else's
    measurement.

    A row is a block or a mark and never both, so a name in the last
    column is what tells the two apart.
    """
    seconds = []
    levels = {}
    marks = []
    labels = []

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            cells = [cell.strip() for cell in line.strip().split(",")]
            if len(cells) < 3:
                continue

            if not labels:
                labels = cells[1:-1]
                levels = {label: [] for label in labels}
                continue

            try:
                moment = float(cells[0])
            except ValueError:
                # A half-written last line, or a header met twice. Skipped
                # rather than raised on: this reads old runs to look at
                # them, and one bad row must not cost the rest of a file.
                continue

            if cells[-1]:
                marks.append((moment, cells[-1]))
                continue

            try:
                values = [float(cell) for cell in cells[1:len(labels) + 1]]
            except ValueError:
                continue
            if len(values) != len(labels):
                continue

            seconds.append(moment)
            for label, value in zip(labels, values):
                levels[label].append(value)

    series = [(label, Columns(seconds, levels[label])) for label in labels]
    return series, marks
