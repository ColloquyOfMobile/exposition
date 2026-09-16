# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/scope/__init__.py

"""An oscilloscope: press start, record A0, press stop, look at it.

Three links and no question of its own. It records what arrives on one
ADC pin for as long as you leave it running, and when you stop it the
recording becomes a graph that can be paged through and zoomed. What is
on the pin, and what it means, is yours - this end has no opinion.

**Why it is not called `test_something`.** Every sibling here asks a
question and reports an answer: is this microphone deaf, is this body
wired to its own filter channel, can she read his pattern. This asks
nothing. It is an instrument in the sense a scope on a bench is an
instrument - you point it at a wire *because* you do not yet know what
you are looking for, which is exactly the situation in which a test that
has already decided what question to ask is no use. Calling it
`test scope` would promise a verdict that is deliberately not here.

**It is a manual test all the same**, and by `group.py`'s own rule rather
than in spite of it: what a run produces is a picture, and the instrument
that reads a picture is somebody's eye. Nothing here writes down whether
the trace was any good, because nothing here knows.

**The board is `Source code/Arduino/microphone_sampler/`**, unchanged and
with nothing to change - it already captures a block of samples and, more
to the point, *times* the block, so what comes back carries the rate it
was really taken at rather than one assumed at both ends. A pin, a ground
and a lead is the whole of the hardware.

**Blocks, and the gaps between them.** The board captures 512 samples and
then sends them, never both at once, because a UART write inside a
capture would stretch the window and put a step in the very signal being
looked at. So a recording is a row of 26.6 ms windows about 20 ms apart,
and roughly half the wall clock is in it - `duty` on the page says how
much, and `trace.py` says why the blocks are drawn where they fell rather
than laid end to end. Inside a block the samples are contiguous and
evenly spaced, which is what makes a waveform readable; across a boundary
the line is joining two moments and means nothing.

**It is independent of `test goertzel ear` on purpose**, though the same
board suits both. That one plays a tone, runs five Goertzel bins over
what comes back and judges what it hears; this one judges nothing. The
lead is chosen separately so that neither can move the other's - and only
one of them can hold a port at a time, so starting this one while that is
recording is refused in a sentence rather than left to pyserial.
"""
from time import time

import serial

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves
from colloquy.ui.graph_view import GraphView

from ..bench_com_port import BenchComPort
from ..test_goertzel_ear import protocol
from .trace import Trace


class ScopeComPort(BenchComPort):
    """Which lead the sampler board is on.

    See `BenchComPort` - the params key is the only thing that differs
    from the Goertzel ear's picker, and it differs on purpose: see the
    module docstring.
    """

    params_section = "scope"
    stand_in = "simulated scope port"


class Scope(BaseThread):
    # Nothing in the room. It listens to a pin and draws what it heard,
    # so there is nothing for somebody standing in front of the
    # installation to be told will happen - the same reason `Repository`
    # has none. See pytest_tests/test_scenarios.py.
    scenario_names = ()

    # Long enough to cover a capture, a 2 kB reply and a board that is
    # thinking about it; short enough that a dead lead is reported rather
    # than sat on.
    REPLY_TIMEOUT = 2.0

    # About ten megabytes of arrays, and a minute and a half of wall clock
    # at the rate one lead can carry. A cap on samples rather than on
    # duration because samples are what cost memory, and a slow link would
    # otherwise buy itself a longer recording by having recorded less of
    # it.
    #
    # It stops and says so rather than dropping the oldest, which would
    # quietly turn a recording somebody believed was whole into its last
    # minute.
    MAX_SAMPLES = 1_000_000

    def __init__(self, owner):
        super().__init__(owner=owner)

        self._com_port = ScopeComPort(owner=self)
        self[self._com_port.name] = self._com_port
        self._port_handler = None

        self._trace = Trace()
        self._graph = None
        self._started_at = None
        self._greeting = None
        self._outcome = None

    @property
    def name(self):
        return "scope"

    @property
    def params(self):
        return self.colloquy.params

    @property
    def com_port(self):
        return self._com_port

    @property
    def baudrate(self):
        return self.params[ScopeComPort.params_section]["baudrate"]

    @property
    def trace(self):
        return self._trace

    @property
    def port_handler(self):
        """A real serial port, or none at all - there is no stand-in.

        For the Goertzel ear's reason, and it is sharper here: a simulated
        scope would draw a picture of nothing, and a picture is convincing
        in a way a row of zeroes is not.
        """
        if self._port_handler is None:
            self._port_handler = serial.Serial(
                baudrate=self.baudrate, timeout=self.REPLY_TIMEOUT
            )
            self._port_handler.port = self.params[
                ScopeComPort.params_section
            ]["communication port"]
        return self._port_handler

    def use_port(self, com_port):
        """Point the link at a newly chosen lead. `BenchComPort` asks its
        owner to do this rather than reaching into the handler itself."""
        self.port_handler.port = com_port

    # --- the line ---------------------------------------------------------

    def _why_not_open(self):
        """Why recording would fail, or None.

        Instant, and reading only what is already known: a refusal that
        has to open a port to say whether a port can be opened is not a
        refusal.
        """
        chosen = self.params[ScopeComPort.params_section]["communication port"]
        if chosen is None:
            return "no port chosen - pick the sampler board under 'com port'"

        available = self.com_port.ports
        if chosen not in available:
            return (
                f"{chosen!r} is not a port on this machine - available: "
                f"{', '.join(available) or 'none, is the board plugged in?'}"
                " - pick one under 'com port'"
            )

        holder = self._who_holds_the_lead(chosen)
        if holder is not None:
            return (
                f"{holder} is running and has {chosen} open - only one of "
                "the two can hold a lead, so stop it first"
            )
        return None

    def _who_holds_the_lead(self, chosen):
        """A sibling test already reading this same port, or None.

        Among this group's own tests rather than over every thread in the
        process, which is the filter the flasher settled on for the same
        shape of question: anything wider finds threads that have nothing
        to do with this lead.
        """
        for test in getattr(self.owner, "tests", ()):
            if test is self or not test.is_started:
                continue
            port = getattr(test, "com_port", None)
            if port is not None and getattr(port, "chosen", None) == chosen:
                return test.name
        return None

    def _open_if_needed(self):
        if not self.port_handler.is_open:
            self.port_handler.open()
            # It reboots when the port opens and greets on the way up.
            self._greeting = None
            deadline = time() + 4.0
            while time() < deadline and self._greeting is None:
                raw = self.port_handler.readline()
                if raw and raw.startswith(b"microphone_sampler"):
                    self._greeting = raw.decode("ascii", "replace").strip()

    def _read_block(self):
        """Ask for one capture and read it back.

        Returns the moment it was *asked for* along with the block, which
        is what `Trace` places the samples at - see there.
        """
        handler = self.port_handler
        handler.reset_input_buffer()
        asked_at = time()
        handler.write(b"b\n")

        deadline = asked_at + self.REPLY_TIMEOUT
        while time() < deadline:
            if self._stop_event.is_set():
                return asked_at, None
            raw = handler.readline()
            if not raw:
                continue
            block = protocol.parse_block(raw.decode("ascii", "replace").strip())
            if block is not None:
                return asked_at, block
        return asked_at, None

    # --- the run ----------------------------------------------------------

    def setup(self):
        self._outcome = None
        self._graph = None
        # A fresh recording every time, and the old graph with it. A scope
        # shows what is on the pin now, and carrying the last run's
        # samples into this one would make a picture nobody could date.
        self._trace = Trace()

        refusal = self._why_not_open()
        if refusal is not None:
            self._refuse(refusal)
            return

        try:
            self._open_if_needed()
        except serial.SerialException as error:
            self._refuse(f"could not open the lead - {error}")
            return

        self._started_at = time()
        if self._greeting is None:
            # Not fatal - the greeting is missed whenever the port was
            # already open, and the blocks are what matter. Said, because
            # a board running some other sketch is the likeliest reason
            # for silence and the page should not have to be guessed at.
            self._outcome = (
                "recording, but the board did not greet - if nothing "
                "arrives, check microphone_sampler is the sketch on it"
            )
        else:
            self._outcome = "recording"

    def loop(self):
        """Ask for the next block the moment the last one is in.

        No read interval, unlike the Goertzel ear's quarter second. That
        one is refreshing a page and more often would be waste; this one
        is recording, and every pause it takes is a hole in the result.
        """
        if len(self._trace) >= self.MAX_SAMPLES:
            self._outcome = (
                f"stopped at {len(self._trace):,} samples, the most one "
                "recording holds - press start again for a new one"
            )
            self.stop()
            return

        asked_at, block = self._read_block()
        if block is None:
            self._refuse(
                "the board stopped answering - check the lead is still "
                "plugged in"
            )
            return

        self._trace.add(asked_at - self._started_at, block)

    def setdown(self):
        self._draw_the_trace()
        try:
            if self._port_handler is not None and self._port_handler.is_open:
                self._port_handler.close()
        except Exception as error:  # noqa: BLE001 - a quiet board, not a crash
            self.log(f"Could not close the sampler board's port: {error}")

    def _draw_the_trace(self):
        """Turn the recording that has just ended into a graph.

        At the end rather than as blocks arrive, and the reason is plainer
        here than anywhere else it is given in this tree: a `GraphView`
        holds which page and which zoom the reader is on, and this reads a
        block twenty times a second. A picture rebuilt that often is not a
        picture anybody can look at.

        A run that recorded nothing leaves no node at all, rather than an
        empty picture with controls that cannot move.
        """
        if not len(self._trace):
            return
        self._graph = GraphView(
            owner=self,
            points=self._trace.columns(),
            name="trace",
        )

    def _refuse(self, reason):
        self._outcome = f"refused: {reason}"
        self.log(f"Refusing to run: {reason}")
        self.stop()

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {self._com_port.name: self._com_port}
        if self._graph is not None:
            children[self._graph.name] = self._graph
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf(
            "port",
            self.params[ScopeComPort.params_section]["communication port"]
            or "not set",
        )
        leaf("sketch", "Source code/Arduino/microphone_sampler/")
        if self._greeting:
            leaf("board says", self._greeting)

        refusal = self._why_not_open()
        leaf("can record", "yes" if refusal is None else f"no - {refusal}")

        trace = self._trace
        if not len(trace):
            leaf(
                "recording",
                "nothing yet - press start, leave it running, press stop",
            )
            return self._with_outcome(leaf, states)

        # The state of the picture goes on this line rather than on one of
        # its own, and that is not tidiness. A leaf is written into the
        # same dict the children are, so a leaf named `trace` *replaces*
        # the `trace` node in it - the link becomes a sentence describing
        # the link. Nothing here may be named after a child.
        leaf(
            "recording",
            f"{len(trace):,} samples in {trace.blocks} blocks over "
            f"{trace.span:.1f}s at {trace.sample_rate:.0f} a second"
            + (
                " - open 'trace'"
                if self._graph is not None
                else " - drawn when you press stop"
            ),
        )
        # What the gaps cost, said rather than left to be discovered by
        # somebody zooming into a boundary and finding a straight line
        # where the signal should have been.
        leaf(
            "duty",
            f"{trace.duty * 100:.0f}% of the wall clock is inside a block - "
            "the board cannot sample and send at once, so the line across "
            "a gap joins two moments and is not a signal",
        )
        leaf("signal", self._describe_signal(trace))
        return self._with_outcome(leaf, states)

    @staticmethod
    def _describe_signal(trace):
        """The extent of the whole recording, and the two faults it tells.

        Not a measurement of anything. A flat line is a pin with nothing
        driving it and a line touching both rails is an input being
        clipped, and both read as a perfectly ordinary trace until
        somebody looks at the numbers.
        """
        low, high = trace.y_extent
        said = f"{low} to {high} of 1023 ADC counts"
        if low == high:
            return f"{said} - flat, nothing is driving the pin"
        if low <= 0 and high >= 1023:
            return f"{said} - touching both rails, the input is clipping"
        return said

    def _with_outcome(self, leaf, states):
        if self._outcome is not None:
            leaf("outcome", self._outcome)
        return states
