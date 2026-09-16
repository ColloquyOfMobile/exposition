# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_scope.py

"""The scope, with no board and no page.

A run needs a Mega with a lead on it. What can be checked here is the
part that decides whether the picture tells the truth, and for a scope
that is entirely **where the samples are put on the clock**.

The board captures a block and then sends it, never both at once, so a
recording is a row of 26.6 ms windows with a gap between each. Laying
them end to end would draw a continuous trace, be wrong about when
everything after the first block happened, and at a steady tone show a
phase jump at every boundary - a fault that is not in the wire. So the
gaps are the thing pinned hardest below.

The refusals are checked the same way the Goertzel ear's are: unbound
calls with small doubles, per pytest_tests/conftest.py, because building
the node needs the whole hardware graph behind it.
"""
from types import SimpleNamespace

import pytest

from colloquy.tests.scope import Scope
from colloquy.tests.scope.trace import Trace
from colloquy.tests.test_goertzel_ear import protocol

SAMPLE_RATE = 19230.8
COUNT = 512
BLOCK_SECONDS = COUNT / SAMPLE_RATE


def block(value=512, count=COUNT, sample_rate=SAMPLE_RATE):
    return protocol.Block(
        sample_rate=sample_rate, samples=tuple([value] * count)
    )


def ramp(count=COUNT, sample_rate=SAMPLE_RATE):
    return protocol.Block(
        sample_rate=sample_rate, samples=tuple(range(count))
    )


# --- where the samples land ----------------------------------------------


def test_a_block_starts_when_it_was_asked_for():
    trace = Trace()
    trace.add(2.0, block())
    xs = [x for x, _y in trace.columns()]
    assert xs[0] == 2.0


def test_samples_inside_a_block_are_evenly_spaced():
    """Contiguous and evenly spaced is what makes a waveform readable,
    and it is the one thing that is true inside a block."""
    trace = Trace()
    trace.add(0.0, block())
    xs = [x for x, _y in trace.columns()]
    steps = {round(b - a, 9) for a, b in zip(xs, xs[1:])}
    assert steps == {round(1.0 / SAMPLE_RATE, 9)}


def test_the_gap_between_blocks_is_kept():
    """The whole point. Two blocks asked for a second apart are a second
    apart in the recording, not 26.6 ms apart as they would be if the
    samples were laid end to end."""
    trace = Trace()
    trace.add(0.0, block())
    trace.add(1.0, block())
    xs = [x for x, _y in trace.columns()]
    assert xs[COUNT] == pytest.approx(1.0)
    # The last sample of the first block sits one step short of its own
    # length, so the hole between the two is the second less that.
    last = (COUNT - 1) / SAMPLE_RATE
    assert xs[COUNT] - xs[COUNT - 1] == pytest.approx(1.0 - last, abs=1e-6)


def test_blocks_are_not_laid_end_to_end():
    """Said as its own check because it is the tempting mistake: the last
    sample of a recording is where the clock says, not `n / fs` in."""
    trace = Trace()
    trace.add(0.0, block())
    trace.add(5.0, block())
    assert trace.span == pytest.approx(5.0 + BLOCK_SECONDS, abs=1e-3)
    assert trace.span != pytest.approx(2 * BLOCK_SECONDS, abs=1e-3)


def test_the_samples_are_the_boards_own_numbers():
    trace = Trace()
    trace.add(0.0, ramp())
    assert [y for _x, y in trace.columns()] == list(range(COUNT))


# --- what the recording says about itself --------------------------------


def test_duty_says_how_much_of_the_clock_is_really_in_it():
    """Half a second of wall clock holding one 26.6 ms block is 5%."""
    trace = Trace()
    trace.add(0.0, block())
    trace.add(0.5, block())
    assert trace.duty == pytest.approx(2 * BLOCK_SECONDS / (0.5 + BLOCK_SECONDS), abs=0.01)


def test_duty_of_an_empty_recording_is_not_a_division():
    assert Trace().duty == 0.0


def test_duty_never_exceeds_one():
    """Two blocks claiming to have been asked for at the same moment
    overlap. It cannot happen down a lead that is answering one command
    at a time, and a duty of 190% would be a worse thing to print than a
    clamped 100%."""
    trace = Trace()
    trace.add(0.0, block())
    trace.add(0.0, block())
    assert trace.duty == 1.0


def test_counts_and_rate_come_off_the_blocks():
    trace = Trace()
    trace.add(0.0, block())
    trace.add(0.1, block())
    assert len(trace) == 2 * COUNT
    assert trace.blocks == 2
    assert trace.sample_rate == SAMPLE_RATE


def test_an_unparseable_rate_adds_nothing():
    """A board that has never captured reports fs=0. The parser refuses
    that line, and this must not be the thing that divides by it."""
    trace = Trace()
    trace.add(0.0, protocol.Block(sample_rate=0.0, samples=(1, 2, 3)))
    assert len(trace) == 0
    assert trace.blocks == 0


def test_the_extent_is_the_whole_recording():
    trace = Trace()
    trace.add(0.0, block(value=100))
    trace.add(0.1, block(value=900))
    assert trace.y_extent == (100, 900)


def test_an_empty_recording_has_no_extent():
    assert Trace().y_extent is None


def test_the_graph_reads_the_arrays_rather_than_a_copy():
    """`Columns` is a view. A recording is a hundred thousand samples and
    a picture of it draws four hundred; building the pairs would hold the
    lot twice for nothing."""
    from colloquy.ui.graph_view import Columns

    trace = Trace()
    trace.add(0.0, block())
    assert isinstance(trace.columns(), Columns)
    assert len(trace.columns()) == COUNT


# --- what the page says --------------------------------------------------


def test_a_flat_line_is_named_as_a_dead_pin():
    trace = Trace()
    trace.add(0.0, block(value=512))
    assert "nothing is driving the pin" in Scope._describe_signal(trace)


def test_touching_both_rails_is_named_as_clipping():
    trace = Trace()
    trace.add(0.0, protocol.Block(sample_rate=SAMPLE_RATE, samples=(0, 1023)))
    assert "clipping" in Scope._describe_signal(trace)


def test_an_ordinary_signal_is_just_its_extent():
    trace = Trace()
    trace.add(0.0, protocol.Block(sample_rate=SAMPLE_RATE, samples=(200, 300)))
    said = Scope._describe_signal(trace)
    assert "200 to 300" in said
    assert "-" not in said


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
    said = Scope._why_not_open(scope_with(None))
    assert "no port chosen" in said


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
    assert Scope._why_not_open(scope_with("COM3", ports=["COM3"], siblings=[idle])) is None


def test_a_sibling_with_no_lead_of_its_own_is_no_obstacle():
    """Most of the tests in the group have no `com_port` at all."""
    other = SimpleNamespace(name="test neopixels", is_started=True)
    assert Scope._why_not_open(scope_with("COM3", ports=["COM3"], siblings=[other])) is None


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

    def __init__(self, graph=None, trace=None):
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


def snapshot_of(graph=None, trace=None):
    return LoneScope(graph=graph, trace=trace)._snapshot_if_opened(())


def test_the_trace_link_survives_the_readings_beside_it():
    """The bug this pins: a `trace` leaf overwrote the `trace` node, so
    the graph could be reached by its URL and by no link on the page.

    With samples in it, because an empty recording returns before any of
    the readings that could shadow anything - a version of this test
    without them passed against the bug.
    """
    trace = Trace()
    trace.add(0.0, block())
    states = snapshot_of(graph=object(), trace=trace)
    assert callable(states["trace"]), (
        "the trace node was replaced by a reading of the same name"
    )


def test_no_reading_is_named_after_a_child():
    """The general form, so the next reading added here cannot do it again
    by picking the obvious name."""
    trace = Trace()
    trace.add(0.0, block())
    states = snapshot_of(graph=object(), trace=trace)
    for child in ("com port", "trace"):
        assert callable(states[child]), f"a reading was drawn over {child!r}"


def test_the_recording_line_says_where_the_picture_is():
    """It has to be said somewhere, and it cannot be said on a line called
    `trace` - so it is said on the line that counts the samples."""
    trace = Trace()
    trace.add(0.0, block())

    while_running = snapshot_of(graph=None, trace=trace)
    assert "drawn when you press stop" in while_running["recording"]["value"]

    afterwards = snapshot_of(graph=object(), trace=trace)
    assert "open 'trace'" in afterwards["recording"]["value"]
