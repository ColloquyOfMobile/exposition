# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/scope/trace.py

"""What a recording is: two channels, and the moment each sample was taken.

Flat arrays that grow as captures arrive - one clock, one array of counts
per channel - handed to the graph as `Columns` views over them. `Columns`
is the class `test_with_everything_moving` already uses to draw a
dataframe without copying it, and it is wanted here for the same reason: a
recording is a hundred thousand samples and a picture of it draws four
hundred.

**Time is real, and it has holes in it.** The board captures and then
sends, and it cannot do both at once - that is deliberate in the sketch,
since a UART write in the middle of a capture would stretch the window and
put a step in the very signal being measured. So a recording is a row of
27 ms windows with a gap between each, and this places every capture at
the moment it was *asked for* rather than laying them end to end.

End to end is the tempting alternative and the one thing that must not be
done: it would draw a continuous trace, be wrong about when everything
after the first capture happened, and at a steady tone show a phase jump
at each boundary - a fault that is not in the wire. The gaps are real, so
they are drawn, and `duty` says how much of the wall clock is in the
recording.

**One clock for both channels**, though the two halves of a pair are one
conversion apart - about 52 us, since there is one converter behind a
multiplexer. Carrying that difference would mean a second array of
doubles to move two lines by a twentieth of a millisecond, on a picture
whose own x positions come from a `time()` taken on this end before the
command went out. The page says it rather than the arrays, because it is
worth knowing and not worth drawing.

The array module rather than lists, because a Python int is 28 bytes and
there are a great many of them: `h` is the ADC's own 16 bits and `d` the
clock. Twelve bytes a pair, so the node's cap is about ten megabytes.
"""
from array import array


class Trace:
    """A growing recording of two pins.

    Kept apart from the node for `protocol.py`'s reason: everything here
    is arithmetic on numbers and can be checked without a board.
    """

    def __init__(self, names=("A0", "A1")):
        self._names = tuple(names)
        self._x = array("d")                                  # seconds
        self._y = [array("h") for _ in self._names]           # counts
        self._captures = 0
        self._captured = 0.0     # seconds actually inside a capture
        self._rate = 0.0         # the last capture's measured rate
        self._span = 0.0         # first request to last sample

    def __len__(self):
        """Pairs, which is how many samples are on *each* channel."""
        return len(self._x)

    @property
    def names(self):
        return self._names

    def add(self, at_seconds, pairs):
        """One capture, begun at `at_seconds` into the run.

        The moment it was *asked for*. The board starts converting as soon
        as the command lands and says nothing until the buffer is full, so
        the request is the best estimate of the first sample's moment this
        end can make; the reply's arrival is the worst, being a whole
        capture plus a whole transfer later.

        A capture whose channels do not match the ones already recorded is
        ignored rather than appended to - two arrays of different lengths
        would draw one line against the other's clock.
        """
        if not pairs.count or pairs.sample_rate <= 0:
            return
        if tuple(pairs.names) != self._names:
            return

        step = 1.0 / pairs.sample_rate
        for index in range(pairs.count):
            self._x.append(at_seconds + index * step)
        for column, samples in zip(self._y, pairs.channels):
            column.extend(samples)

        self._captures += 1
        self._rate = pairs.sample_rate
        self._captured += pairs.count * step
        self._span = self._x[-1]

    # --- what is in it ----------------------------------------------------

    @property
    def captures(self):
        return self._captures

    @property
    def sample_rate(self):
        """Per channel. Half what the converter runs at, since the two
        channels share it."""
        return self._rate

    @property
    def span(self):
        """Wall clock from the first request to the last sample, in
        seconds - not the same as how much sound is in the recording."""
        return self._span

    @property
    def captured(self):
        """Seconds actually inside a capture. See `duty`."""
        return self._captured

    @property
    def duty(self):
        """The fraction of the wall clock really in the recording, 0..1.

        The one number that says what the gaps cost. It is a property of
        the link rather than of anything being measured - a capture is
        27 ms and its transfer about 40 ms at 1 Mbaud - so it lands near a
        third, and a *much* lower one means captures are being missed
        rather than that the room went quiet.
        """
        if self._span <= 0:
            return 0.0
        return min(1.0, self._captured / self._span)

    def extent(self, index):
        """Lowest and highest count on one channel, or None.

        Not a measurement of anything, and it tells the two faults that
        read as an ordinary trace otherwise: a flat line is a pin with
        nothing driving it, and 0 to 1023 is an input being clipped.
        """
        column = self._y[index]
        if not len(column):
            return None
        return min(column), max(column)

    def swing(self, index):
        """Peak to peak on one channel, in counts.

        The number the whole two-channel arrangement exists to compare. A
        microphone that is producing nothing and one that is producing
        plenty differ here by a factor, whatever the two are biased at -
        which is the comparison a single trace cannot make, because there
        is nothing to call a factor *of*.
        """
        found = self.extent(index)
        return 0 if found is None else found[1] - found[0]

    def series(self):
        """Label to points, one entry per channel, for the graph.

        Views, not copies - the arrays stay where they are and the graph
        reads only the rows it is going to draw. Labelled, so the two get
        colours off tab10 and a legend, which is the whole of what makes
        two lines comparable rather than merely both present.
        """
        from colloquy.ui.graph_view import Columns

        return {
            name: Columns(self._x, column)
            for name, column in zip(self._names, self._y)
        }
