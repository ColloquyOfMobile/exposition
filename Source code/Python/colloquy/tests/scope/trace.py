# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/scope/trace.py

"""What a recording is: samples, and the moment each was taken.

Two flat arrays that grow as blocks arrive, handed to the graph as a
`Columns` view over them. `Columns` is the class `test_with_everything_moving`
already uses to draw a dataframe without copying it, and it is exactly
what is wanted here for the same reason: a recording is a hundred thousand
samples and a picture of it draws four hundred.

**Time is real, and it has holes in it.** The board captures a block and
then sends it, and it cannot do both at once - that is deliberate in the
sketch, since a UART write in the middle of a capture would stretch the
window and put a step in the signal being measured. So a recording is a
row of 26.6 ms windows with a gap between each, and this places every
block at the moment it was *asked for* rather than laying the blocks end
to end.

Laying them end to end is the tempting alternative and it is the one
thing that must not be done: it would draw a continuous trace and be
wrong about when everything after the first block happened, and at a
steady tone it would show a phase jump at each boundary - a fault that is
not in the wire. The gap is real, so it is drawn, and `duty` says how
much of the wall clock is actually in the recording.

The array module rather than a list, because a Python int is 28 bytes and
there are a great many of them: `h` is the ADC's own 16 bits and `d` the
time. Ten bytes a sample, so the cap below is about ten megabytes.
"""
from array import array


class Trace:
    """A growing recording of one pin.

    Kept apart from the node for `protocol.py`'s reason: everything here
    is arithmetic on numbers and can be checked without a board.
    """

    def __init__(self):
        self._x = array("d")     # seconds from the start of the recording
        self._y = array("h")     # ADC counts, 0..1023
        self._blocks = 0
        self._captured = 0.0     # seconds actually inside a block
        self._rate = 0.0         # the last block's measured rate
        self._span = 0.0         # wall clock, first request to last sample

    def __len__(self):
        return len(self._y)

    def add(self, at_seconds, block):
        """One block, captured starting at `at_seconds` into the run.

        The moment the block was *asked for*. The board starts converting
        as soon as the command lands and says nothing until the buffer is
        full, so the request is the best estimate of the first sample's
        moment that this end can make; the reply's arrival is the worst,
        being a whole capture plus a whole transfer later.
        """
        if not block.samples or block.sample_rate <= 0:
            return
        step = 1.0 / block.sample_rate
        for index, value in enumerate(block.samples):
            self._x.append(at_seconds + index * step)
            self._y.append(value)
        self._blocks += 1
        self._rate = block.sample_rate
        self._captured += block.count * step
        self._span = self._x[-1]

    # --- what is in it ----------------------------------------------------

    @property
    def blocks(self):
        return self._blocks

    @property
    def sample_rate(self):
        return self._rate

    @property
    def span(self):
        """Wall clock from the first request to the last sample, in
        seconds - not the same as how much sound is in the recording."""
        return self._span

    @property
    def captured(self):
        """Seconds actually inside a block. See `duty`."""
        return self._captured

    @property
    def duty(self):
        """The fraction of the wall clock that is really in the
        recording, 0..1.

        The one number that says what the gaps cost. It is a property of
        the link rather than of anything being measured - a capture is
        26.6 ms and its transfer about 20 ms at 1 Mbaud - so it lands
        near a half, and a *much* lower one means blocks are being missed
        rather than that the room went quiet.
        """
        if self._span <= 0:
            return 0.0
        return min(1.0, self._captured / self._span)

    @property
    def y_extent(self):
        """Lowest and highest count in the whole recording, or None.

        Not a measurement of anything, and it catches the two faults that
        read as an ordinary trace otherwise: a flat line is a pin with
        nothing driving it, and 0 to 1023 is an input being clipped.
        """
        if not len(self._y):
            return None
        return min(self._y), max(self._y)

    def columns(self):
        """The recording as a sequence of (seconds, count) for the graph.

        A view, not a copy - the arrays stay where they are and the graph
        reads only the few hundred rows it is going to draw.
        """
        from colloquy.ui.graph_view import Columns

        return Columns(self._x, self._y)
