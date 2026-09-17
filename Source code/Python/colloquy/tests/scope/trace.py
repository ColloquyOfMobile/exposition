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

    def coupling(self):
        """How much of one channel is the other one. See `coupling_of`."""
        if len(self._y) < 2:
            return None
        return coupling_of(self._y[0], self._y[1], self._x)

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


# How many captures the coupling check looks at, spread evenly along the
# recording. Bounded because this is asked on every render while a run may
# be a million pairs long - and *spread*, not taken off the end, which is
# the mistake that cost the second attempt at this: a run whose tone was
# switched off before it was stopped ends in silence, and two channels
# with no signal on them cannot be correlated whatever is wired where.
# Measured on that run: +0.998 across the whole of it, +0.82 over its last
# twenty captures alone. Evenly spaced and taken as a median, a quiet
# passage is outvoted instead of deciding it.
COUPLING_CAPTURES = 20

# Above this, at the best of three alignments, the two readings are not
# two readings. Set from a measured unplugged lead (+0.998) and
# deliberately above what a room can do: two microphones a few centimetres
# apart on one pure tone reach about 0.93, and two half a wavelength apart
# reach -1 honestly, so anything lower would be calling real geometry a
# fault.
COUPLED = 0.99

# And below that, the band where it is genuinely ambiguous. Two
# microphones a few centimetres apart on one pure tone reach about 0.93,
# and two half a wavelength apart - 43 cm at 400 Hz, an ordinary distance
# in a room - are honestly near -1. A real fault measured here sat at
# -0.97, so this band cannot be read either way from the number alone:
# what it gets is the ambiguity named and the one test that settles it.
#
# The band is not a formality. A pin that is out but whose neighbour is a
# *weak* microphone lands in it - a ghost is a copy of its neighbour plus
# the converter's own noise, so the correlation falls as the source does:
# +0.998 on a strong tone, +0.984 on one four times weaker, both with a
# lead plainly out. Which is why the reading in this band leans on the
# shift rather than on the magnitude that has just failed.
SUSPICIOUS = 0.9


def capture_bounds(seconds):
    """Where each capture starts and stops, as index ranges.

    A recording is a row of 27 ms windows with a gap between each, and the
    gap is far larger than the interval inside one - about 92 ms against
    112 us on a real lead - so the clock says where the joins are without
    anything having to be written down beside it. Taken off the clock
    rather than remembered, so a run read back from a CSV splits the same
    way as one in memory, from the same rows.

    Five times the median step is the line: comfortably above jitter in
    the sample interval, comfortably below any gap a transfer takes.
    """
    if len(seconds) < 2:
        return [(0, len(seconds))] if len(seconds) else []

    steps = sorted(
        seconds[index + 1] - seconds[index] for index in range(len(seconds) - 1)
    )
    inner = steps[len(steps) // 2]
    if inner <= 0:
        return [(0, len(seconds))]

    bounds, start = [], 0
    for index in range(len(seconds) - 1):
        if seconds[index + 1] - seconds[index] > inner * 5:
            bounds.append((start, index + 1))
            start = index + 1
    bounds.append((start, len(seconds)))
    return bounds


def coupling_of(left, right, seconds, captures=COUPLING_CAPTURES):
    """How much of one channel is the other one, as (r, shift) or None.

    The correlation of two channels sample by sample, at the best of three
    alignments: as sampled, and each shifted by one. Two things make it an
    instrument rather than a curiosity, and both were learned the hard way.

    Two things decide whether it works, they are separate, and each was
    found by getting it wrong on a real run.

    **Within a capture, never across one.** Correlating the flat arrays
    end to end stitches over the 92 ms gaps - the very thing this module
    refuses to do to the x axis - and each capture's own DC level then
    counts as signal. Measured: a run whose channels correlate at -0.970
    within captures reads -0.852 stitched.

    **Spread along the run, not taken off the end.** A run whose tone was
    switched off before it was stopped ends in silence, and two channels
    with no signal cannot be correlated whatever is wired where. Measured
    on the run with a lead plainly unplugged: +0.998 spread, +0.821 over
    its last twenty captures. That one is the bigger error of the two, and
    the one that would have said a disconnected microphone was fine.

    **The shift.** An unconnected pin is not silent - its sample capacitor
    comes up holding the charge of the channel converted just before it,
    so it reports a copy of its neighbour offset by one conversion, which
    at zero shift looks merely similar and at the right shift is
    unmistakable. On that unplugged lead: +0.95 as sampled, **+0.998**
    shifted by one.

    How much of a copy is measurable, and it is a capacitor rather than
    anything to do with sound: fitting the open pin against its neighbour
    over three runs - both pins, a strong microphone and a weak one - gives
    **94 to 95 per cent** every time, which is the 14 pF sample-and-hold
    sharing with about 0.8 pF of pin. A fixed fraction regardless of how
    loud the source is, and a direction that follows the order of
    conversion rather than the wiring, are what rule out crosstalk in the
    leads.

    Not a verdict, and it must not become one - see `describe_coupling`.
    """
    found_bounds = capture_bounds(seconds)
    if len(found_bounds) > captures:
        step = len(found_bounds) / float(captures)
        bounds = [found_bounds[int(index * step)] for index in range(captures)]
    else:
        bounds = found_bounds

    best = None
    for shift in (-1, 0, 1):
        found = []
        for start, stop in bounds:
            a, b = left[start:stop], right[start:stop]
            if shift > 0:
                a, b = a[:-shift], b[shift:]
            elif shift < 0:
                a, b = a[-shift:], b[:shift]
            if len(a) < 64:
                continue
            value = _correlation(a, b)
            if value is not None:
                found.append(value)
        if not found:
            continue
        found.sort()
        median = found[len(found) // 2]
        if best is None or abs(median) > abs(best[0]):
            best = (median, shift)
    return best


def ghost_of(found, names):
    """Which channel is the copy, or None if the shift does not say.

    **Correlation cannot answer this and order can.** r is symmetric - "A0
    is a copy of A1" and "A1 is a copy of A0" are one statement about the
    numbers - so the direction has to come from the clock. A pair is
    converted first channel then second, so in time the samples run
    `A0[0] A1[0] A0[1] A1[1]`, and a floating pin comes up holding the
    charge of the conversion *immediately before it*. The copy is
    therefore always the later of the two, because the converter cannot
    see the future:

      - the first channel floating holds the second's previous sample,
        which peaks at shift -1;
      - the second channel floating holds the first's sample from the same
        pair, which peaks at shift 0.

    Shift +1 has no ghost reading at all - nothing is converted in that
    order - so it is left unnamed rather than guessed at.

    Read straight off a real recording this says the first channel, which
    is the answer somebody reading the correlation by hand got backwards.

    The shift 0 case is the weak one and says so where it is used: two
    microphones genuinely in phase peak there too.
    """
    if found is None:
        return None
    _r, shift = found
    if shift == -1:
        return names[0]
    if shift == 0:
        return names[1]
    return None


def describe_coupling(found, names=("the first", "the second"), flat=()):
    """Whether the two channels are telling you two things.

    The check that was missing, and the run that found it: with A1
    physically unplugged, both channels showed the same 400 Hz tone at the
    same strength and `compared` said "both are hearing the room". A copy
    of a working microphone looks exactly like a working microphone.

    **Named, not judged.** Two microphones a few centimetres apart hearing
    one pure tone are genuinely correlated - at 400 Hz a 5 cm spacing is 21
    degrees, which is 0.93 - and two half a wavelength apart are genuinely
    anti-correlated. So this says how independent the two readings are, and
    leaves what that means to somebody who knows where the microphones are.
    What it adds is the reading nobody would otherwise have doubted, and
    the test that settles it: unplug one and see whether the other changes.
    """
    if flat:
        # Distinguished from having nothing to work with, because they
        # read alike and mean opposite things: a channel that never moves
        # cannot be correlated however long the run goes on, and if it is
        # flat at zero that is a pin somebody has tied down - which is the
        # honest way to leave an unused channel, since a grounded pin
        # discharges the sample capacitor instead of holding a copy of its
        # neighbour in it.
        which = " and ".join(flat)
        return (
            f"{which} never moves, so there is nothing to correlate - "
            "which is what a pin tied to ground looks like, and the honest "
            "way to leave a channel unused"
        )
    if found is None:
        return "not enough recorded yet to say"
    r, shift = found
    aligned = "" if shift == 0 else f" (shifted by {shift:+d} sample)"
    said = f"correlation {r:+.3f}{aligned}"

    if abs(r) < SUSPICIOUS:
        return f"{said} - the two are reading different things"
    if abs(r) < COUPLED:
        ghost = ghost_of(found, names)
        if r > 0 and ghost is not None:
            # The shift outlives the signal where the magnitude does not.
            # A real run with a weak microphone on one pin and the other
            # pin out reached only +0.984, under the threshold, and the
            # geometry sentence below was wrong twice over about it: it
            # offers two microphones close together, which peak at shift 0,
            # to explain a reading peaking at -1.
            other = names[1] if ghost == names[0] else names[0]
            return (
                f"{said} - close to a copy, and the alignment is a ghost's: "
                f"if it is one, {ghost} is the unconnected pin, since it is "
                f"converted after {other}. A ghost gets noisier as the "
                "source gets weaker - measured +0.998 on a strong tone and "
                "+0.984 on one four times weaker - so the number alone is "
                f"not proof either way. Unplug {other} and see whether "
                f"{ghost} changes"
            )
        geometry = (
            "two microphones half a wavelength apart really are inverted - "
            "43 cm at 400 Hz"
            if r < 0
            else "two microphones close together on one tone really do "
            "agree this well - 5 cm at 400 Hz is 0.93"
        )
        return (
            f"{said} - very close, and this number alone cannot say whether "
            f"that is the wiring or the room: {geometry}. Unplug one lead "
            "and see whether the other changes"
        )
    if r > 0:
        ghost = ghost_of(found, names)
        if ghost is None:
            which = "One channel is very likely an unconnected pin"
        else:
            other = names[1] if ghost == names[0] else names[0]
            hedge = "" if shift == -1 else (
                " - though at this alignment two microphones genuinely in "
                "phase would look the same"
            )
            which = (
                f"{ghost} is very likely an unconnected pin reporting a copy "
                f"of {other}, because it is converted *after* it{hedge}"
            )
        return (
            f"{said} - NOT two readings. {which}: the converter's sample "
            "capacitor comes up holding the charge of the channel before "
            "it. Unplug the other lead and see whether this one changes"
        )
    return (
        f"{said} - NOT two readings, and inverted. One channel is appearing "
        "on the other with its sign turned over, which is what a shared "
        "ground return does: the first channel's current moves the "
        "reference the second is measured against. Check the two grounds go "
        "separately to the board"
    )


def _correlation(left, right):
    """Pearson's r over two equal-length sequences, or None if either is
    flat - a channel that never moves has no correlation with anything,
    and `_describe_channel` already names that fault on its own."""
    count = min(len(left), len(right))
    if count < 2:
        return None
    mean_left = sum(left[:count]) / count
    mean_right = sum(right[:count]) / count

    covariance = spread_left = spread_right = 0.0
    for index in range(count):
        a = left[index] - mean_left
        b = right[index] - mean_right
        covariance += a * b
        spread_left += a * a
        spread_right += b * b
    if spread_left <= 0 or spread_right <= 0:
        return None
    return covariance / (spread_left * spread_right) ** 0.5
