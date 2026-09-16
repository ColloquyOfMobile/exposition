# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_scope.py

"""The scope, with no board and no page.

A run needs a Mega with two microphones on it. What can be checked here
is the part that decides whether the picture tells the truth, and for a
scope that is two things.

**Where the samples go on the clock.** The board captures and then sends,
never both at once, so a recording is a row of 27 ms windows with a gap
between each. Laying them end to end would draw a continuous trace, be
wrong about when everything after the first capture happened, and at a
steady tone show a phase jump at every boundary - a fault that is not in
the wire.

**Which samples belong to which microphone.** They arrive interleaved, so
an off-by-one deinterleave hands every reading to the wrong channel -
which is exactly the fault somebody reaches for this test to find, and
would be invisible: two plausible traces, swapped.

The refusals are checked the way the Goertzel ear's are: unbound calls
with small doubles, per pytest_tests/conftest.py, because building the
node needs the whole hardware graph behind it.
"""
from types import SimpleNamespace

import pytest

from colloquy.tests.scope import Scope
from colloquy.tests.scope.protocol import Pairs, parse_pairs
from colloquy.tests.scope.trace import Trace

SAMPLE_RATE = 9615.4          # per channel: the converter halved
COUNT = 256                   # pairs in one capture
CAPTURE_SECONDS = COUNT / SAMPLE_RATE


def pairs(a=512, b=512, count=COUNT, rate=SAMPLE_RATE, names=("A0", "A1")):
    """One capture with each channel held at a constant, unless a
    sequence is passed for either."""
    def column(value):
        if hasattr(value, "__len__") or hasattr(value, "__iter__"):
            return tuple(value)
        return tuple([value] * count)

    return Pairs(sample_rate=rate, names=names, channels=(column(a), column(b)))


# --- reading the board's reply -------------------------------------------


def test_a_reply_deinterleaves_into_two_channels():
    """a0 a1 a0 a1 on the wire, two channels here. An off-by-one in this
    line swaps every reading between the two microphones."""
    read = parse_pairs("pair n=3 fs=9615.4 pins=A0,A1 10 90 11 91 12 92")
    assert read.channels == ((10, 11, 12), (90, 91, 92))
    assert read.names == ("A0", "A1")
    assert read.sample_rate == 9615.4
    assert read.count == 3


def test_a_truncated_reply_is_dropped():
    """512 numbers do not fit in a serial buffer at once, so a read that
    gives up early yields a line that parses perfectly and is missing its
    end - and on an odd truncation the two channels come apart, every A1
    landing where an A0 belongs."""
    assert parse_pairs("pair n=3 fs=9615.4 pins=A0,A1 10 90 11 91 12") is None


def test_the_ears_own_reply_is_not_a_capture_here():
    """The single-channel `block` line belongs to test_goertzel_ear, and
    reading it as interleaved pairs would silently halve its rate and
    split one microphone into two."""
    assert parse_pairs("block n=2 fs=19230.8 10 11") is None


def test_a_line_that_is_not_a_reply_at_all():
    """The greeting, and whatever half line was in the buffer when the
    port opened, both arrive here. Ordinary, not a fault."""
    assert parse_pairs("microphone_sampler firmware=2 mic_pin=A0") is None
    assert parse_pairs("") is None


def test_a_reply_with_no_rate_is_dropped():
    assert parse_pairs("pair n=1 pins=A0,A1 10 90") is None
    assert parse_pairs("pair n=1 fs=0.0 pins=A0,A1 10 90") is None


# --- where the samples land ----------------------------------------------


def test_a_capture_starts_when_it_was_asked_for():
    trace = Trace()
    trace.add(2.0, pairs())
    assert trace.series()["A0"][0][0] == 2.0


def test_samples_inside_a_capture_are_evenly_spaced():
    """Contiguous and evenly spaced is what makes a waveform readable,
    and it is the one thing that is true inside a capture."""
    trace = Trace()
    trace.add(0.0, pairs())
    line = trace.series()["A0"]
    xs = [line[index][0] for index in range(len(line))]
    steps = {round(b - a, 9) for a, b in zip(xs, xs[1:])}
    assert steps == {round(1.0 / SAMPLE_RATE, 9)}


def column_of(trace, name, axis):
    line = trace.series()[name]
    return [line[index][axis] for index in range(len(line))]


def test_the_gap_between_captures_is_kept():
    """The whole point. Two captures asked for a second apart are a
    second apart in the recording, not 27 ms apart as they would be if
    the samples were laid end to end."""
    trace = Trace()
    trace.add(0.0, pairs())
    trace.add(1.0, pairs())
    xs = column_of(trace, "A0", 0)
    assert xs[COUNT] == pytest.approx(1.0)
    last = (COUNT - 1) / SAMPLE_RATE
    assert xs[COUNT] - xs[COUNT - 1] == pytest.approx(1.0 - last, abs=1e-6)


def test_captures_are_not_laid_end_to_end():
    trace = Trace()
    trace.add(0.0, pairs())
    trace.add(5.0, pairs())
    assert trace.span == pytest.approx(5.0 + CAPTURE_SECONDS, abs=1e-3)
    assert trace.span != pytest.approx(2 * CAPTURE_SECONDS, abs=1e-3)


def test_both_channels_share_one_clock():
    """They are one conversion apart in truth, about 52 us, and that is
    said on the page rather than carried in a second array of doubles.
    What must be true is that row n of each line is the same moment."""
    trace = Trace()
    trace.add(0.0, pairs())
    assert column_of(trace, "A0", 0) == column_of(trace, "A1", 0)


def test_each_channel_keeps_its_own_samples():
    trace = Trace()
    trace.add(0.0, pairs(a=range(COUNT), b=range(1000, 1000 + COUNT)))
    assert column_of(trace, "A0", 1) == list(range(COUNT))
    assert column_of(trace, "A1", 1) == list(range(1000, 1000 + COUNT))


def test_a_capture_of_other_channels_is_ignored():
    """Two arrays of different lengths would draw one line against the
    other's clock."""
    trace = Trace()
    trace.add(0.0, pairs())
    trace.add(0.1, pairs(names=("A2", "A3")))
    assert trace.captures == 1


def test_an_unparseable_rate_adds_nothing():
    trace = Trace()
    trace.add(0.0, pairs(rate=0.0))
    assert len(trace) == 0
    assert trace.captures == 0


# --- what the recording says about itself --------------------------------


def test_duty_says_how_much_of_the_clock_is_really_in_it():
    trace = Trace()
    trace.add(0.0, pairs())
    trace.add(0.5, pairs())
    assert trace.duty == pytest.approx(
        2 * CAPTURE_SECONDS / (0.5 + CAPTURE_SECONDS), abs=0.01
    )


def test_duty_of_an_empty_recording_is_not_a_division():
    assert Trace().duty == 0.0


def test_duty_never_exceeds_one():
    """Two captures claiming the same moment overlap. It cannot happen
    down a lead answering one command at a time, and a duty of 190% would
    be a worse thing to print than a clamped 100%."""
    trace = Trace()
    trace.add(0.0, pairs())
    trace.add(0.0, pairs())
    assert trace.duty == 1.0


def test_length_is_per_channel():
    """Not the total. The number a reader compares against the sample
    rate to work out how long the recording is."""
    trace = Trace()
    trace.add(0.0, pairs())
    assert len(trace) == COUNT


def test_swing_is_peak_to_peak_per_channel():
    trace = Trace()
    trace.add(0.0, pairs(a=(100, 900), b=(500, 510), count=2))
    assert trace.swing(0) == 800
    assert trace.swing(1) == 10


def test_the_graph_reads_the_arrays_rather_than_a_copy():
    """`Columns` is a view. A recording is a hundred thousand samples and
    a picture of it draws four hundred."""
    from colloquy.ui.graph_view import Columns

    trace = Trace()
    trace.add(0.0, pairs())
    drawn = trace.series()
    assert set(drawn) == {"A0", "A1"}
    assert all(isinstance(line, Columns) for line in drawn.values())


# --- the comparison, which is what two channels are for -------------------


def test_a_dead_microphone_beside_a_live_one_is_named():
    """The reading this whole arrangement exists for."""
    trace = Trace()
    trace.add(0.0, pairs(a=(300, 700), b=(512, 512), count=2))
    said = Scope._compare(trace)
    assert "A1 is flat" in said
    assert "not the room" in said


def test_two_working_microphones_are_named_as_such():
    trace = Trace()
    trace.add(0.0, pairs(a=(300, 700), b=(310, 690), count=2))
    assert "both are hearing the room" in Scope._compare(trace)


def test_a_large_difference_suggests_swapping_the_leads():
    """The one move that separates a dead microphone from a dead channel,
    and this end cannot make it."""
    trace = Trace()
    trace.add(0.0, pairs(a=(300, 700), b=(500, 520), count=2))
    said = Scope._compare(trace)
    assert "out-swings" in said
    assert "Swap the two leads" in said


def test_two_flat_channels_say_there_is_nothing_to_compare():
    """Rather than dividing by a swing of zero, or calling one of two
    dead pins the winner."""
    trace = Trace()
    trace.add(0.0, pairs(a=512, b=512))
    assert "nothing is arriving on either pin" in Scope._compare(trace)


def test_a_flat_channel_is_named_as_a_dead_pin():
    trace = Trace()
    trace.add(0.0, pairs())
    assert "nothing is driving the pin" in Scope._describe_channel(trace, 0)


def test_touching_both_rails_is_named_as_clipping():
    trace = Trace()
    trace.add(0.0, pairs(a=(0, 1023), b=(500, 510), count=2))
    assert "clipping" in Scope._describe_channel(trace, 0)


def test_an_ordinary_channel_is_its_extent_and_swing():
    trace = Trace()
    trace.add(0.0, pairs(a=(200, 300), b=(500, 510), count=2))
    said = Scope._describe_channel(trace, 0)
    assert "200 to 300" in said
    assert "swing 100" in said


# --- the refusals --------------------------------------------------------


def scope_with(chosen, ports=(), siblings=()):
    """A double carrying only what `_why_not_open` reads."""
    owner = SimpleNamespace(tests=list(siblings))
    double = SimpleNamespace(
        params={"scope": {"communication port": chosen}},
        com_port=SimpleNamespace(ports=list(ports)),
        owner=owner,
    )
    # The one method `_why_not_open` calls on itself, bound to the double.
    double._who_holds_the_lead = lambda port: Scope._who_holds_the_lead(
        double, port
    )
    return double


def test_no_port_chosen_is_refused():
    assert "no port chosen" in Scope._why_not_open(scope_with(None))


def test_a_port_remembered_from_another_machine_is_refused():
    """The chosen port lives in params and outlives the desk that chose
    it, so a name from another machine opens nothing."""
    said = Scope._why_not_open(scope_with("COM9", ports=["COM3"]))
    assert "not a port on this machine" in said
    assert "COM3" in said


def test_a_lead_held_by_another_test_is_refused_by_name():
    """Only one of the two can have the port open. Said in a sentence
    naming which, rather than left to come back as a pyserial error about
    access being denied."""
    busy = SimpleNamespace(
        name="test goertzel ear",
        is_started=True,
        com_port=SimpleNamespace(chosen="COM3"),
    )
    said = Scope._why_not_open(scope_with("COM3", ports=["COM3"], siblings=[busy]))
    assert "test goertzel ear" in said
    assert "stop it first" in said


def test_a_stopped_sibling_on_the_same_lead_is_no_obstacle():
    idle = SimpleNamespace(
        name="test goertzel ear",
        is_started=False,
        com_port=SimpleNamespace(chosen="COM3"),
    )
    assert Scope._why_not_open(
        scope_with("COM3", ports=["COM3"], siblings=[idle])
    ) is None


def test_a_sibling_with_no_lead_of_its_own_is_no_obstacle():
    """Most of the tests in the group have no `com_port` at all."""
    other = SimpleNamespace(name="test neopixels", is_started=True)
    assert Scope._why_not_open(
        scope_with("COM3", ports=["COM3"], siblings=[other])
    ) is None


def test_nothing_recorded_leaves_no_graph():
    """Rather than an empty picture with controls that cannot move."""
    empty = SimpleNamespace(_trace=Trace(), _graph="untouched")
    Scope._draw_the_trace(empty)
    assert empty._graph == "untouched"


# --- the page's own names ------------------------------------------------
#
# A leaf and a child node are written into the *same* dict, so a leaf named
# after a child replaces it: the link becomes a sentence describing the
# link, which is what it did. Silent, because a reading in the right place
# saying the right thing is exactly what a working page looks like.


class LoneScope(Scope):
    """A real Scope with the tree taken out from under it.

    A subclass rather than a duck-typed double, for once, because the
    method under test opens with a zero-argument `super()` - that is the
    call doing the merging, so standing next to it rather than in place of
    it is the whole point.

    The children are bare callables, which `Base._snapshot_if_opened`
    passes through untouched. A real child node would need a tree behind
    it, and what is being checked is only whether its entry survives.
    """

    def __init__(self, graph=None, trace=None, firmware=2):
        self._owner = None
        self._owners = []
        self._dict = {}
        self._path = None
        self._is_opened = False
        self._log = None
        # What `BaseThread._snapshot_if_opened` reads to decide between a
        # `start` link and a `stop` one. Never started here - see
        # pytest_tests/conftest.py.
        self._thread = None

        self._trace = trace if trace is not None else Trace()
        self._graph = graph
        self._greeting = None
        self._firmware = firmware
        self._refused_the_command = False
        self._outcome = None
        self._port_handler = None
        self._children = {"com port": lambda: None}
        if graph is not None:
            self._children["trace"] = lambda: None

    @property
    def params(self):
        return {"scope": {"communication port": "COM3"}}

    @property
    def com_port(self):
        return SimpleNamespace(ports=["COM3"], chosen="COM3")

    def _who_holds_the_lead(self, chosen):
        return None

    @property
    def snapshot_children(self):
        return dict(self._children)


def snapshot_of(graph=None, trace=None, firmware=2):
    return LoneScope(
        graph=graph, trace=trace, firmware=firmware
    )._snapshot_if_opened(())


def recorded():
    trace = Trace()
    trace.add(0.0, pairs(a=(300, 700), b=(310, 690), count=2))
    return trace


def test_the_trace_link_survives_the_readings_beside_it():
    """The bug this pins: a `trace` leaf overwrote the `trace` node, so
    the graph could be reached by its URL and by no link on the page.

    With samples in it, because an empty recording returns before any of
    the readings that could shadow anything - a version of this test
    without them passed against the bug.
    """
    states = snapshot_of(graph=object(), trace=recorded())
    assert callable(states["trace"]), (
        "the trace node was replaced by a reading of the same name"
    )


def test_no_reading_is_named_after_a_child():
    """The general form, so the next reading added here cannot do it again
    by picking the obvious name."""
    states = snapshot_of(graph=object(), trace=recorded())
    for child in ("com port", "trace"):
        assert callable(states[child]), f"a reading was drawn over {child!r}"


def test_both_channels_get_a_reading_of_their_own():
    states = snapshot_of(graph=object(), trace=recorded())
    assert "swing" in states["A0"]["value"]
    assert "swing" in states["A1"]["value"]
    assert "compared" in states


def test_the_recording_line_says_where_the_picture_is():
    """It has to be said somewhere, and it cannot be said on a line called
    `trace` - so it is said on the line that counts the samples."""
    while_running = snapshot_of(graph=None, trace=recorded())
    assert "drawn when you press stop" in while_running["recording"]["value"]

    afterwards = snapshot_of(graph=object(), trace=recorded())
    assert "open 'trace'" in afterwards["recording"]["value"]


# --- an old board, which is not a missing lead ---------------------------
#
# Firmware 1 knows A0 and nothing else. Asked for two channels it does not
# go quiet - it answers `error commands: b | ?`, a perfectly good reply to
# a question it does not understand. Read as silence, that sent somebody
# to check a cable that was never the problem, while the board was
# answering the whole time.


def test_the_firmware_is_read_out_of_the_greeting():
    from colloquy.tests.scope.protocol import firmware_of

    greeting = "microphone_sampler firmware=2 mic_pin=A0 n=512 fs=19230.8"
    assert firmware_of(greeting) == 2
    assert firmware_of("microphone_sampler mic_pin=A0") is None
    assert firmware_of("") is None


def test_the_boards_own_refusal_is_recognised():
    from colloquy.tests.scope.protocol import is_refusal

    assert is_refusal("error commands: b | ?")
    assert not is_refusal("pair n=1 fs=9615.4 pins=A0,A1 10 90")
    assert not is_refusal("")


def test_an_old_board_is_not_reported_as_a_missing_lead():
    """The bug: one flat channel and a sentence about a cable."""
    old = SimpleNamespace(_refused_the_command=True, _firmware=1)
    said = Scope._why_nothing_came(old)
    assert "firmware 1" in said
    assert "Reflash" in said
    assert "lead" not in said


def test_a_silent_board_still_points_at_the_lead():
    quiet = SimpleNamespace(_refused_the_command=False, _firmware=2)
    assert "lead" in Scope._why_nothing_came(quiet)


def test_an_old_board_is_refused_before_it_records_anything():
    """Up front, or it answers every capture with a refusal and records
    nothing for as long as somebody leaves it running."""
    refusals = []
    old = SimpleNamespace(
        _outcome=None,
        _graph=None,
        _refused_the_command=False,
        _trace=None,
        _firmware=1,
        _why_not_open=lambda: None,
        _open_if_needed=lambda: None,
        _greeting="microphone_sampler firmware=1 mic_pin=A0",
        _refuse=refusals.append,
    )
    Scope.setup(old)
    assert len(refusals) == 1
    assert "firmware 1" in refusals[0]
    assert "microphone_sampler" in refusals[0]


def test_the_page_names_a_firmware_that_cannot_do_two_channels():
    states = snapshot_of(graph=object(), trace=recorded(), firmware=1)
    assert "too old" in states["firmware"]["value"]


def test_the_page_says_when_the_firmware_is_good():
    states = snapshot_of(graph=object(), trace=recorded(), firmware=2)
    assert "knows both channels" in states["firmware"]["value"]
