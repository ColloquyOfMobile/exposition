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


def test_a_flat_channel_is_named_by_the_voltage_it_sits_at():
    """Not "nothing is driving the pin", which is what this used to say
    about every flat reading. A pin with nothing on it does not sit still
    at all - it copies its neighbour - so a channel that really is steady
    is being *held* at something, and which something is the whole of what
    is worth saying about it."""
    trace = Trace()
    trace.add(0.0, pairs())
    said = Scope._describe_channel(trace, 0)
    assert "steady 2.502 V" in said


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
        self._written_to = None
        self._outcome = None
        self._port_handler = None
        self._children = {"com port": lambda: None, "results": lambda: None}
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
    for child in ("com port", "trace", "results"):
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


# --- the run on the disk -------------------------------------------------
#
# It kept nothing at first, on the grounds that a scope trace is looked at
# now, at a wire. That was wrong the moment two microphones were being
# compared: every question then is *between* runs, and none of them can be
# answered from the one that happens to be in memory.


def test_a_run_writes_and_reads_back_whole(tmp_path):
    from colloquy.tests.scope import recording

    trace = Trace()
    trace.add(0.0, pairs(a=range(COUNT), b=range(1000, 1000 + COUNT)))
    path = recording.write(trace, tmp_path / "run.csv")

    read = recording.read(path)
    assert set(read) == {"A0", "A1"}
    assert [value for _s, value in read["A0"]] == list(range(COUNT))
    assert [value for _s, value in read["A1"]] == list(range(1000, 1000 + COUNT))


def test_the_channel_names_come_out_of_the_header(tmp_path):
    """Not out of the code. A channel list that changes later must not be
    able to relabel a measurement somebody already took."""
    from colloquy.tests.scope import recording

    path = tmp_path / "old.csv"
    path.write_text("seconds,MIC,REF\n0.000000,100,900\n", encoding="utf-8")
    assert set(recording.read(path)) == {"MIC", "REF"}


def test_the_clock_survives_the_round_trip(tmp_path):
    """Six decimals, because samples are about 104 us apart - three would
    put a whole run into eleven distinct timestamps and draw a staircase."""
    from colloquy.tests.scope import recording

    trace = Trace()
    trace.add(0.0, pairs())
    trace.add(1.0, pairs())
    path = recording.write(trace, tmp_path / "run.csv")

    read = recording.read(path)["A0"]
    assert read[1][0] == pytest.approx(1.0 / SAMPLE_RATE, abs=1e-6)
    assert read[COUNT][0] == pytest.approx(1.0, abs=1e-6)


def test_the_gaps_are_in_the_file(tmp_path):
    """A row is a moment and rows are not evenly spaced, which is why the
    clock is a column rather than implied by the row number."""
    from colloquy.tests.scope import recording

    trace = Trace()
    trace.add(0.0, pairs())
    trace.add(1.0, pairs())
    read = recording.read(recording.write(trace, tmp_path / "run.csv"))["A0"]
    steps = {round(b[0] - a[0], 4) for a, b in zip(read, read[1:])}
    assert len(steps) > 1, "the gap between captures was flattened"


def test_a_half_written_row_is_skipped_rather_than_fatal(tmp_path):
    """A run killed mid-write leaves a half line at the end, and losing it
    is not worth losing the hour before it."""
    from colloquy.tests.scope import recording

    path = tmp_path / "cut.csv"
    path.write_text("seconds,A0,A1\n0.000000,1,2\n0.000104,3\n", encoding="utf-8")
    read = recording.read(path)
    assert [value for _s, value in read["A0"]] == [1]


def test_an_empty_file_reads_as_nothing(tmp_path):
    from colloquy.tests.scope import recording

    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    assert recording.read(path) == {}


def test_a_run_that_recorded_nothing_writes_no_file(tmp_path):
    """A file of one header line is a run somebody would open."""
    empty = SimpleNamespace(
        _trace=Trace(), _dir_path=tmp_path, _written_to="untouched"
    )
    Scope._write_the_trace(empty)
    assert list(tmp_path.iterdir()) == []
    assert empty._written_to == "untouched"


# --- a run keeps its place -----------------------------------------------
#
# A GraphView holds which page and which zoom the reader is on. Rebuild the
# node that carries it on every request and every press mutates a graph
# that is then thrown away: the links answer, the readings change for one
# render, and the picture never moves. Building fresh is the obvious way to
# write a listing, and it is silently wrong.


def written_run(tmp_path):
    from colloquy.tests.scope import recording
    from colloquy.tests.scope.results import Results

    trace = Trace()
    for capture in range(8):
        trace.add(capture * 0.07, pairs(a=range(COUNT), b=range(COUNT)))
    recording.write(trace, tmp_path / "2026_09_17_10h_00min_00s.csv")
    return Results(owner=SimpleNamespace(owner=None, owners=[]), dir_path=tmp_path)


def test_a_listed_run_is_the_same_node_next_request(tmp_path):
    results = written_run(tmp_path)
    first = results.snapshot_children["2026_09_17_10h_00min_00s"]
    again = results.snapshot_children["2026_09_17_10h_00min_00s"]
    assert first is again


def test_paging_into_a_run_survives_the_next_click(tmp_path):
    """The bug: press next page, and the picture came back at page one."""
    results = written_run(tmp_path)
    run = results.snapshot_children["2026_09_17_10h_00min_00s"]
    graph = run.graph
    graph.smaller_page()
    graph.next_page()
    moved_to = graph.page

    later = results.snapshot_children["2026_09_17_10h_00min_00s"]
    assert later.graph is graph
    assert later.graph.page == moved_to


def test_a_run_written_while_the_page_is_open_turns_up(tmp_path):
    """The other half, and why the folder is rescanned at all."""
    from colloquy.tests.scope import recording

    results = written_run(tmp_path)
    assert len(results.snapshot_children) == 1

    trace = Trace()
    trace.add(0.0, pairs())
    recording.write(trace, tmp_path / "2026_09_17_11h_00min_00s.csv")
    assert len(results.snapshot_children) == 2


# --- are the two channels telling you two things -------------------------
#
# The check that was missing. With A1 physically unplugged, both channels
# showed the same 400 Hz tone at the same strength and `compared` said
# "both are hearing the room": an unconnected pin is not silent, it comes
# up holding the charge of the channel converted just before it, so it
# reports a copy of its neighbour - and a copy of a working microphone
# looks exactly like a working microphone.

from math import pi, sin  # noqa: E402 - beside the tests that use it

from colloquy.tests.scope.trace import (  # noqa: E402
    COUPLED,
    capture_bounds,
    coupling_of,
    describe_coupling,
)


def tone(count, hz=400.0, rate=8929.0, amplitude=100, offset=248, phase=0.0):
    return [
        int(offset + amplitude * sin(2 * pi * hz * i / rate + phase))
        for i in range(count)
    ]


def clock(captures, per=256, rate=8929.0, gap=0.092):
    """A recording's seconds column: captures of `per` samples, far apart."""
    seconds, start = [], 0.0
    for _ in range(captures):
        seconds.extend(start + i / rate for i in range(per))
        start = seconds[-1] + gap
    return seconds


def test_captures_are_found_from_the_clock_alone():
    """Nothing is written beside the rows to say where a capture ends; the
    gap is 800 times the interval inside one, so the clock says it."""
    assert len(capture_bounds(clock(5))) == 5
    assert capture_bounds(clock(3))[1] == (256, 512)


def test_an_unconnected_pin_reporting_its_neighbour_is_caught():
    """One conversion behind, which is what the sample capacitor does."""
    real = tone(256 * 6)
    ghost = real[1:] + [real[-1]]
    found = coupling_of(real, ghost, clock(6))
    assert found is not None
    assert abs(found[0]) >= COUPLED
    assert "NOT two readings" in describe_coupling(found)


def test_two_independent_microphones_are_not_flagged():
    """Same tone, different rooms' worth of noise and a different level -
    the ordinary case, which must not be called a fault."""
    from random import Random

    random = Random(4)
    left = tone(256 * 6, amplitude=100)
    right = [
        int(0.4 * value + random.uniform(-40, 40) + 120) for value in left
    ]
    found = coupling_of(left, right, clock(6))
    assert abs(found[0]) < COUPLED
    assert "reading different things" in describe_coupling(found)


def test_the_ambiguous_band_names_the_ambiguity_rather_than_a_verdict():
    """Two microphones half a wavelength apart really are inverted - 43 cm
    at 400 Hz, an ordinary distance in a room - so a number in this band
    cannot be read either way on its own."""
    from random import Random

    random = Random(5)
    left = tone(256 * 6)
    right = [int(-0.9 * (v - 248) + 248 + random.uniform(-20, 20)) for v in left]
    found = coupling_of(left, right, clock(6))
    assert COUPLED > abs(found[0]) >= 0.9
    said = describe_coupling(found)
    assert "cannot say whether" in said
    assert "Unplug one lead" in said


def test_the_correlation_is_taken_within_captures_not_across_them():
    """Stitching the captures end to end lets each one's DC level count as
    signal. Measured on a real run: -0.970 within captures, -0.852
    stitched.

    Reproduced by letting each channel's DC wander on its own from capture
    to capture, which is what a real pair does - the wander is
    uncorrelated between the two, so stitched it reads as disagreement
    that is not in the signal at all.
    """
    from random import Random

    random = Random(11)
    left, right = [], []
    for _capture in range(8):
        here, there = random.uniform(-60, 60), random.uniform(-60, 60)
        piece = tone(256)
        left.extend(int(value + here) for value in piece)
        right.extend(int(-(value - 248) * 0.9 + 160 + there) for value in piece)

    within = coupling_of(left, right, clock(8))[0]
    flat = [index / 8929.0 for index in range(len(left))]
    across = coupling_of(left, right, flat)[0]
    assert abs(within) > 0.99 > abs(across), f"{within=} {across=}"


def test_a_quiet_passage_cannot_decide_it():
    """A run whose tone was switched off before it was stopped ends in
    silence, and two channels with no signal cannot be correlated whatever
    is wired where. Measured on the real run with a lead plainly
    unplugged: +0.998 spread along it, +0.821 over its last twenty
    captures alone - which would have said a disconnected microphone was
    fine."""
    real = tone(256 * 20) + [248] * (256 * 4)
    ghost = real[1:] + [real[-1]]
    found = coupling_of(real, ghost, clock(24))
    assert abs(found[0]) >= COUPLED


def test_a_recording_too_short_to_judge_says_so():
    assert describe_coupling(coupling_of([1, 2], [1, 2], [0.0, 0.1])) == (
        "not enough recorded yet to say"
    )


def test_the_comparison_defers_to_it_rather_than_reassuring(tmp_path):
    """The reading that was dangerously wrong: with one lead unplugged the
    two swings match to a tenth, because one of them *is* the other."""
    trace = Trace()
    real = tone(256)
    ghost = real[1:] + [real[-1]]
    for capture in range(6):
        trace.add(capture * 0.12, pairs(a=real, b=ghost, count=256))
    said = Scope._compare(trace)
    assert "see 'independent'" in said
    assert "both are hearing the room" not in said


# --- which channel is the copy -------------------------------------------
#
# Correlation cannot answer this: r is symmetric, so "A0 is a copy of A1"
# and "A1 is a copy of A0" are one statement about the numbers. Order can,
# because the converter cannot see the future - a pair runs A0, A1, A0, A1
# in time, and a floating pin holds the charge of the conversion
# immediately before it, so the copy is always the later of the two. Read
# by hand off a real run, this is the part that came out backwards.

from colloquy.tests.scope.trace import ghost_of  # noqa: E402


def test_the_first_channel_floating_peaks_one_sample_back():
    """A0 holds A1's *previous* sample, since A1[n] is converted just
    before A0[n+1]."""
    real = tone(256 * 6)
    ghost = [real[0]] + real[:-1]          # A0[n+1] == A1[n]
    found = coupling_of(ghost, real, clock(6))
    assert found[1] == -1
    assert ghost_of(found, ("A0", "A1")) == "A0"


def test_the_second_channel_floating_peaks_in_line():
    """A1 holds A0's sample from the same pair, converted just before."""
    real = tone(256 * 6)
    found = coupling_of(real, list(real), clock(6))
    assert found[1] == 0
    assert ghost_of(found, ("A0", "A1")) == "A1"


def test_an_alignment_with_no_ghost_reading_is_not_guessed_at():
    """Shift +1 would mean a pin copying a conversion that has not
    happened. Left unnamed rather than blamed on a channel."""
    assert ghost_of((0.99, 1), ("A0", "A1")) is None
    assert ghost_of(None, ("A0", "A1")) is None


def test_the_named_channel_is_said_in_the_reading():
    real = tone(256 * 6)
    ghost = [real[0]] + real[:-1]
    said = describe_coupling(coupling_of(ghost, real, clock(6)), ("A0", "A1"))
    assert "A0 is very likely an unconnected pin reporting a copy of A1" in said
    assert "converted *after* it" in said


def test_the_in_line_case_admits_it_is_the_weaker_one():
    """Two microphones genuinely in phase peak at shift 0 too, so naming a
    channel there has to carry the doubt with it."""
    real = tone(256 * 6)
    said = describe_coupling(coupling_of(real, list(real), clock(6)), ("A0", "A1"))
    assert "A1 is very likely an unconnected pin" in said
    assert "genuinely in phase would look the same" in said


def test_a_weak_source_puts_its_ghost_in_the_ambiguous_band():
    """A ghost is a copy of its neighbour plus the converter's own noise,
    so the correlation falls as the source does. Measured with a lead
    plainly out: +0.998 on a strong tone, +0.984 on one four times weaker
    - which is under the threshold, so the magnitude alone called an
    unplugged pin "could be two microphones"."""
    from random import Random

    random = Random(13)
    weak = [int(248 + 20 * sin(2 * pi * 400 * i / 8929.0)) for i in range(256 * 6)]
    ghost = [weak[0]] + [value + int(random.uniform(-6, 6)) for value in weak[:-1]]

    found = coupling_of(ghost, weak, clock(6))
    assert COUPLED > abs(found[0]) >= 0.9, found


def test_the_ambiguous_band_leans_on_the_shift_not_the_magnitude():
    """Which is the half that survives a weak source. The sentence this
    replaced offered two microphones close together - which peak at shift
    0 - to explain a reading peaking at -1."""
    from random import Random

    random = Random(13)
    weak = [int(248 + 20 * sin(2 * pi * 400 * i / 8929.0)) for i in range(256 * 6)]
    ghost = [weak[0]] + [value + int(random.uniform(-6, 6)) for value in weak[:-1]]

    said = describe_coupling(coupling_of(ghost, weak, clock(6)), ("A0", "A1"))
    assert "A0 is the unconnected pin" in said
    assert "converted after A1" in said
    assert "not proof either way" in said
    assert "close together" not in said


def test_an_inverted_reading_in_the_band_still_talks_about_geometry():
    """There is no ghost alignment that inverts - a retained charge is a
    copy, not a mirror - so the room is the thing to weigh there."""
    from random import Random

    random = Random(5)
    left = tone(256 * 6)
    right = [int(-0.9 * (v - 248) + 248 + random.uniform(-20, 20)) for v in left]
    said = describe_coupling(coupling_of(left, right, clock(6)), ("A0", "A1"))
    assert "half a wavelength" in said
    assert "unconnected pin" not in said


def test_a_channel_tied_to_ground_is_not_reported_as_too_little_data():
    """The two read alike out of `coupling_of` - both give None - and mean
    opposite things. A channel that never moves cannot be correlated
    however long the run goes on, and saying "not enough recorded yet"
    about a pin somebody has deliberately tied down sends them back to
    record more of nothing."""
    said = describe_coupling(None, ("A0", "A1"), flat=("A0",))
    assert "A0 never moves" in said
    assert "tied to ground" in said
    assert "not enough recorded" not in said


def test_nothing_recorded_yet_still_says_so():
    assert describe_coupling(None, ("A0", "A1")) == "not enough recorded yet to say"


def test_a_grounded_pin_leaves_the_other_channel_readable():
    """The point of grounding it: a low impedance discharges the sample
    capacitor instead of holding a copy of the neighbour in it, so the
    working channel is still the working channel."""
    real = tone(256)
    trace = Trace()
    for capture in range(8):
        trace.add(capture * 0.12, pairs(a=[0] * 256, b=real, count=256))

    assert "tied to ground" in Scope._describe_channel(trace, 0)
    assert trace.swing(1) > 100
    assert "A0 never moves" in Scope._describe_coupling(trace)


# --- the three ways of being flat ----------------------------------------
#
# They read alike and are not the same fact. This said "nothing is driving
# the pin" about all of them, which was wrong about a supply rail somebody
# had wired in to measure: that pin was driven hard, to the top of the
# range.


def flat_at(value):
    trace = Trace()
    trace.add(0.0, pairs(a=value, b=tone(COUNT)))
    return Scope._describe_channel(trace, 0)


def test_a_pin_at_full_scale_is_not_called_undriven():
    said = flat_at(1023)
    assert "pinned at full scale" in said
    assert "5 V and 6 V read alike" in said
    assert "nothing is driving" not in said


def test_a_pin_at_zero_is_named_as_grounded():
    assert "tied to ground" in flat_at(0)


def test_a_steady_voltage_in_between_is_named_as_one():
    """What a rail under 5 V looks like - and what an output that has died
    with its bias stuck looks like."""
    said = flat_at(152)
    assert "steady 0.743 V" in said
    assert "supply rail" in said


def test_clipping_still_wins_over_all_three():
    trace = Trace()
    trace.add(0.0, pairs(a=(0, 1023), b=(500, 510), count=2))
    assert "clipping" in Scope._describe_channel(trace, 0)


def test_the_independence_reading_no_longer_assumes_ground():
    said = describe_coupling(None, ("A0", "A1"), flat=("A1",))
    assert "rail wired in on purpose" in said
    assert "no length of run will change that" in said


# --- the document --------------------------------------------------------


def test_the_diagnosis_document_is_on_the_disk_where_it_says():
    from colloquy.tests.scope.diagnosis_document import DiagnosingAMicrophone

    path = DiagnosingAMicrophone.folder / DiagnosingAMicrophone.file_name
    assert path.exists(), f"{path} is missing"
    assert "Diagnosing a microphone" in path.read_text(encoding="utf-8")


def test_the_document_carries_the_measurements_its_advice_rests_on():
    """A number with no source is what this repository has been bitten by
    before - see SUPPLY_SETUP.md, and one destroyed amplifier - so the
    figures travel with the advice rather than behind it."""
    from colloquy.tests.scope.diagnosis_document import DiagnosingAMicrophone

    text = (DiagnosingAMicrophone.folder / DiagnosingAMicrophone.file_name).read_text(
        encoding="utf-8"
    )
    for measured in ("94 to 95 per cent", "248.4", "151.3", "5.000 V", "294"):
        assert measured in text, f"{measured!r} is not in the document"


def test_the_document_hangs_off_the_scope_and_not_beside_it():
    """It is not a sibling of the test group's members. Somebody goes
    looking for it while standing at the bench with a quiet microphone,
    which is where the scope already is."""
    from colloquy.tests.scope.diagnosis_document import DiagnosingAMicrophone

    assert DiagnosingAMicrophone.document_name == "diagnosing a microphone"
    assert DiagnosingAMicrophone.folder.name == "scope"
