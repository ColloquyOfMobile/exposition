# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/scope/__init__.py

"""A two-channel oscilloscope: start, record A0 and A1, stop, look.

Three links and no question of its own. It records what arrives on two
ADC pins for as long as you leave it running, and when you stop it the
recording becomes a graph of both, drawn against one clock, that can be
paged through and zoomed. What is on the pins, and what it means, is
yours - this end has no opinion.

**Two channels because one trace cannot answer the question that gets
asked of it.** A microphone producing nothing looks exactly like a quiet
room, and a trace with a small wobble on it is either a dead capsule or a
still afternoon - there is nothing in the picture to say which. Put a
second microphone on A1 in the same room and the comparison makes itself:
whatever the two are biased at, one swinging while the other does not is
a fact about a microphone and not about the room. That is why `swing` is
a reading of its own beside each channel.

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

**The board is `Source code/Arduino/microphone_sampler/`**, which times
its own captures, so what comes back carries the rate it was really taken
at rather than one assumed at both ends. Two pins, a common ground and a
lead is the whole of the hardware.

It gained a **`d`** command for this (firmware 2) rather than a second
channel on `b`. `b` is what `test_goertzel_ear` asks for, and it runs five
Goertzel bins over what comes back; handing that two interleaved
microphones would not fail, it would answer wrongly about a frequency
nobody played. So the single-channel reply is untouched to the last byte.
`d` fills the same buffer with interleaved pairs - the same 512
conversions, the same 27 ms window, the same reply size - and what is
halved is how many each channel gets, about 9.6 kSPS apiece.

**The two halves of a pair are one conversion apart**, about 52 us,
rather than simultaneous: there is one converter behind a multiplexer, so
simultaneous is not on offer at any price. It costs nothing for what this
is for, and would matter to anything measuring phase between the two,
which nothing here does.

**Blocks, and the gaps between them.** The board captures 512 samples and
then sends them, never both at once, because a UART write inside a
capture would stretch the window and put a step in the very signal being
looked at. So a recording is a row of 26.6 ms windows about 20 ms apart,
and roughly a third of the wall clock is in it - `duty` on the page says
how much, and `trace.py` says why the blocks are drawn where they fell rather
than laid end to end. Inside a block the samples are contiguous and
evenly spaced, which is what makes a waveform readable; across a boundary
the line is joining two moments and means nothing.

**The second channel need not be a second microphone.** It is two ADC
pins and a clock, so anything within the converter's range can go on the
other one - and the use that turned up first was a **supply rail**, wired
in beside a microphone that was suspected of being underfed, which settled
in one run what a meter would have settled in two hands. Watch what you
read off it though: a rail at or above the converter's own 5 V reference
pins at 1023, where 5 V and 6 V read alike, so that reading is a floor
rather than a measurement. The page says so rather than calling a hard
driven pin flat, which is what it used to do.

**It is independent of `test goertzel ear` on purpose**, though the same
board suits both. That one plays a tone, runs five Goertzel bins over
what comes back and judges what it hears; this one judges nothing. The
lead is chosen separately so that neither can move the other's - and only
one of them can hold a port at a time, so starting this one while that is
recording is refused in a sentence rather than left to pyserial.
"""
from datetime import datetime
from time import time

import serial

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves
from colloquy.ui.graph_view import GraphView

from ..bench_com_port import BenchComPort
from ..sampler_board import SamplerBoard, SamplerFlasher
from . import protocol, recording
from .diagnosis_document import DiagnosingAMicrophone
from .results import Results
from .trace import COUPLED, Trace, describe_coupling


class ScopeComPort(BenchComPort):
    """Which lead the sampler board is on.

    See `BenchComPort` - the params key is the only thing that differs
    from the Goertzel ear's picker, and it differs on purpose: see the
    module docstring.
    """

    params_section = "scope"
    stand_in = "simulated scope port"


class Scope(SamplerBoard, BaseThread):
    # Nothing in the room. It listens to a pin and draws what it heard,
    # so there is nothing for somebody standing in front of the
    # installation to be told will happen - the same reason `Repository`
    # has none. See pytest_tests/test_scenarios.py.
    scenario_names = ()

    # Long enough to cover a capture, a 2 kB reply and a board that is
    # thinking about it; short enough that a dead lead is reported rather
    # than sat on.
    REPLY_TIMEOUT = 2.0

    # Pairs, not samples - so it is twelve bytes each (a double of clock
    # and two counts) and about twelve megabytes, which at 9.6 kSPS a
    # channel and a third of the clock spent sending is two or three
    # minutes. A cap on samples rather than on duration because samples
    # are what cost memory, and a slow link would otherwise buy itself a
    # longer recording by having recorded less of it.
    #
    # It stops and says so rather than dropping the oldest, which would
    # quietly turn a recording somebody believed was whole into its last
    # minute.
    MAX_SAMPLES = 1_000_000

    # What `SamplerBoard` measures the board's greeting against. Firmware
    # 1 has `b` and nothing else; `d` and the second channel arrived in 2,
    # and a board on 1 answers a two-channel request with a refusal.
    MINIMUM_FIRMWARE = protocol.MINIMUM_FIRMWARE
    FIRMWARE_NEEDED_FOR = "both channels"

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()
        self._results = Results(owner=self, dir_path=self._dir_path)
        self._diagnosis = DiagnosingAMicrophone(owner=self)

        self._com_port = ScopeComPort(owner=self)
        self[self._com_port.name] = self._com_port
        self._port_handler = None
        # The other half of knowing what is on this lead: `ask the board`
        # says what is there, this puts the right thing there. See
        # sampler_board.py - a recording with one flat line is equally a
        # dead microphone, a missing lead and an old sketch, and until
        # both of these existed this page could only rule out the first.
        self._flasher = SamplerFlasher(owner=self)
        self[self._flasher.name] = self._flasher
        self["ask the board"] = self.ask_the_board

        self._trace = Trace()
        self._graph = None
        self._started_at = None
        self._greeting = None
        self._firmware = None
        self._refused_the_command = False
        self._written_to = None
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
    def results(self):
        return self._results

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

    # `_open_if_needed` and the greeting it reads are `SamplerBoard`'s:
    # `test goertzel ear` had the same fifteen lines, and the two now
    # share the board rather than a copy of how to greet it.

    def _read_block(self):
        """Ask for one capture of both channels and read it back.

        Returns the moment it was *asked for* along with the pairs, which
        is what `Trace` places the samples at - see there.
        """
        handler = self.port_handler
        handler.reset_input_buffer()
        asked_at = time()
        handler.write(b"d\n")

        deadline = asked_at + self.REPLY_TIMEOUT
        while time() < deadline:
            if self._stop_event.is_set():
                return asked_at, None
            raw = handler.readline()
            if not raw:
                continue
            line = raw.decode("ascii", "replace").strip()
            pairs = protocol.parse_pairs(line)
            if pairs is not None:
                return asked_at, pairs
            if protocol.is_refusal(line):
                # The board understood the link perfectly and does not
                # know the command. Kept, because the loop must not call
                # that silence - see `_why_nothing_came`.
                self._refused_the_command = True
                return asked_at, None
        return asked_at, None

    # --- the run ----------------------------------------------------------

    def setup(self):
        self._outcome = None
        self._graph = None
        self._refused_the_command = False
        self._written_to = None
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

        if self._firmware is not None and self._firmware < protocol.MINIMUM_FIRMWARE:
            # Up front, because the board will otherwise answer every
            # capture with a refusal and record nothing, for as long as
            # somebody leaves it running.
            self._refuse(
                f"the board is on firmware {self._firmware} and the second "
                f"channel needs {protocol.MINIMUM_FIRMWARE} - reflash "
                "Source code/Arduino/microphone_sampler/ (firmware 1 knows "
                "A0 only, and answers a two-channel request with an error)"
            )
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
                f"stopped at {len(self._trace):,} samples a channel, the most one "
                "recording holds - press start again for a new one"
            )
            self.stop()
            return

        asked_at, pairs = self._read_block()
        if pairs is None:
            self._refuse(self._why_nothing_came())
            return

        self._trace.add(asked_at - self._started_at, pairs)

    def _why_nothing_came(self):
        """Which of the two faults it was, in the board's own words.

        They are opposite in kind and the remedies are nowhere near each
        other: a lead that has come out is silence, and a board that does
        not know the command is a *reply*. Reading the reply as silence is
        what sent somebody to check a cable that was never the problem -
        the board was answering the whole time, in firmware 1, about a
        command it has never had.
        """
        if self._refused_the_command:
            version = self._firmware if self._firmware is not None else "1"
            return (
                f"the board answered that it does not know the two-channel "
                f"command - it is on firmware {version}, and the second "
                f"channel needs {protocol.MINIMUM_FIRMWARE}. Reflash "
                "Source code/Arduino/microphone_sampler/"
            )
        return "the board stopped answering - check the lead is still plugged in"

    def setdown(self):
        self._draw_the_trace()
        self._write_the_trace()
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
            series=self._trace.series(),
            name="trace",
        )

    def _write_the_trace(self):
        """Put the run beside every other one.

        Named for when it happened, like every other test here. A run that
        recorded nothing writes nothing - a file of one header line is a
        run somebody would open.

        Failing to write must not be what ends a run: the readings are
        already on the page and the picture is already drawn, so a full
        disk or a folder somebody has moved is worth a line in the log
        rather than a traceback out of `setdown`.
        """
        if not len(self._trace):
            return
        now = datetime.now()
        path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h"
            f"_{now.minute:02}min_{now.second:02}s.csv"
        )
        try:
            self._written_to = recording.write(self._trace, path)
        except OSError as error:  # noqa: BLE001 - a disk, not a fault
            self.log(f"Could not write the run to {path}: {error}")
            self._written_to = None

    def _refuse(self, reason):
        self._outcome = f"refused: {reason}"
        self.log(f"Refusing to run: {reason}")
        self.stop()

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {
            self._com_port.name: self._com_port,
            # Beside the picker, because they are the same question asked
            # twice: which board is on this lead, and is it the right one.
            self._flasher.name: self._flasher,
            "ask the board": self.ask_the_board,
        }
        if self._graph is not None:
            children[self._graph.name] = self._graph
        # Always, unlike the graph: the runs on the disk are there to be
        # compared with, and the reason to look at them is usually before
        # doing another one rather than after.
        children[self._results.name] = self._results
        # Always, and beside the results rather than behind them: nobody
        # goes looking for a document about diagnosing microphones until
        # they are already standing at the bench with a quiet one, which
        # is `HARDWARE_SETUP.md`'s reason for hanging where it does.
        children[self._diagnosis.name] = self._diagnosis
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
        # `board says` and `firmware`, both from `SamplerBoard`. The
        # version is on its own line rather than left inside the greeting
        # because it is what decides whether there is a second channel at
        # all, and a recording with one flat line is exactly what an old
        # board looks like from the graph.
        self._board_readings(leaf)

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
            f"{len(trace):,} samples per channel in {trace.captures} "
            f"captures over {trace.span:.1f}s at {trace.sample_rate:.0f} a "
            f"second each"
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
        for index, channel in enumerate(trace.names):
            leaf(channel, self._describe_channel(trace, index))
        leaf("compared", self._compare(trace))
        leaf("independent", self._describe_coupling(trace))
        if self._written_to is not None:
            leaf(
                "written to",
                f"{self._written_to.name} ({recording.describe(self._written_to)})"
                " - under 'results', and it is the only way this run leaves "
                "this machine",
            )
        return self._with_outcome(leaf, states)

    @staticmethod
    def _describe_channel(trace, index):
        """One channel's extent and swing, and the faults they tell.

        Not a measurement of anything. Three things read as a perfectly
        ordinary trace until somebody looks at the numbers: a flat line is
        a pin with nothing driving it, a line touching both rails is an
        input being clipped, and a pin with *nothing connected* does not
        read silence at all - it wanders over most of the range, which
        looks livelier than a working microphone in a quiet room.
        """
        low, high = trace.extent(index)
        swing = trace.swing(index)
        said = f"{low} to {high} of 1023, swing {swing}"
        if low <= 0 and high >= 1023:
            return f"{said} - touching both rails, the input is clipping"
        if swing:
            return said

        # Three ways to be flat, and they are not the same fact. This
        # said "nothing is driving the pin" about all of them, which was
        # wrong about a supply rail somebody had deliberately wired in to
        # measure - it was driven hard, to the top of the range.
        if high >= 1023:
            return (
                f"{said} - pinned at full scale. Whatever is on this pin is "
                "at or above the converter's own 5 V reference, so this is a "
                "floor and not a measurement: 5 V and 6 V read alike"
            )
        if low <= 0:
            return f"{said} - flat at zero, which is a pin tied to ground"
        return (
            f"{said} - a steady {low * 5 / 1023:.3f} V with nothing moving "
            "on it. A supply rail being measured looks like this, and so "
            "does an output that has died with its bias stuck"
        )

    @staticmethod
    def _describe_coupling(trace):
        """Are the two channels telling you two things? See `trace.py`."""
        flat = tuple(
            name
            for index, name in enumerate(trace.names)
            if trace.swing(index) == 0
        )
        return describe_coupling(trace.coupling(), trace.names, flat)

    @staticmethod
    def _compare(trace):
        """The two channels against each other, which is the whole point.

        A ratio and not a verdict. One microphone against another in the
        same room is the only comparison available that the room cannot
        spoil - a quiet afternoon halves both - so the number worth
        printing is how many times one out-swung the other, with what that
        might mean left where it belongs.

        Deliberately not called a pass or a fail. The quiet one may be
        dead, unplugged, unpowered, on a pin that is not connected, or
        simply further from whatever is making the noise, and this end
        cannot tell those apart. What it *can* do is say plainly when
        there is nothing to compare.
        """
        swings = [trace.swing(index) for index in range(len(trace.names))]
        loudest = max(swings)
        if loudest == 0:
            return "both flat - nothing is arriving on either pin"

        quietest = min(swings)
        loud = trace.names[swings.index(loudest)]
        quiet = trace.names[swings.index(quietest)]
        if quietest == 0:
            return (
                f"{quiet} is flat while {loud} swings {loudest} - the "
                f"difference is in the microphone or its wiring, not the room"
            )
        ratio = loudest / quietest
        if ratio < 1.5:
            coupled = trace.coupling()
            if coupled is not None and abs(coupled[0]) >= COUPLED:
                # The reading that was dangerously wrong: with one lead
                # unplugged the two swings match to a tenth, because one
                # of them *is* the other. See `_describe_coupling`.
                return (
                    f"{loud} and {quiet} swing within {ratio:.1f}x of each "
                    f"other, but see 'independent' - they are not two "
                    f"readings, so this says nothing about two microphones"
                )
            return (
                f"{loud} and {quiet} swing within {ratio:.1f}x of each "
                f"other - both are hearing the room"
            )
        return (
            f"{loud} out-swings {quiet} by {ratio:.1f}x - too much to be "
            f"the room, which reaches both. Swap the two leads: if the "
            f"quiet one follows, it is the microphone"
        )

    def _with_outcome(self, leaf, states):
        if self._outcome is not None:
            leaf("outcome", self._outcome)
        return states
