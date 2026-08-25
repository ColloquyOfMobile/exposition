# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_search/__init__.py

"""Does a female read a male while everything is moving?

`test_read_pattern` answers "can she read him at all", and it answers it
by holding the pair still and pointing them at each other. That is the
right way round to start, and it is not the room: in the room the bar is
sliding, she is swaying, he is swaying, and she has him in view for a few
seconds at a time. This run is the same question asked under those
conditions, and it is the only one of the two that can produce a **miss**
- a male plainly in her view, blinking, and nothing decoded.

**Only reading is measured.** No sound, no reinforcement, no interaction.
If a female's search does recognise a male she is short of, the find is
logged and her search is started again, because what would follow it is
reinforcement and there is none (CODE_DOCUMENTATION 2.9). So the run goes
on producing readings instead of stopping at the first one that matters.

**Drives are yours to set, and the run will not set them.** Every body's
`drives` node hangs off this test, and there are two presets below for
the states worth starting from. The run refuses to be interesting if
anything is inert: a satisfied male does not call, and a satisfied female
does not look. It says so at startup rather than sitting there quietly.

**What starts what.** The test starts each male's `search` and each
female's `search` directly, and starts the **bar body thread** rather
than the bar's search - because the bar is the thing that decides whether
the bar wanders, by watching the males' search flags (`Bar.loop()`), and
that decision is half of what this run is here to exercise. Deliberately
*not* starting the `Male`/`Female` body threads: their `setup()` starts
`Drives`, whose whole job is to climb, and a run whose drive states drift
under it cannot say what was expected of a reading.

**The head is borrowed as a readout**, as in `test_read_pattern`: it goes
to the colour of whichever male was decoded for five seconds and then
goes out. During a run it therefore says "she just read somebody", not
"this is how hungry she is".
"""
from datetime import datetime
from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

from . import events

# Test-only indicator colours, the same two test_read_pattern uses so
# that a head means the same thing in both runs.
HEAD_COLOR_BY_MALE = {
    "male1": dict(red=0, green=0, blue=255, white=0),
    "male2": dict(red=255, green=0, blue=0, white=0),
}

# A readout to be seen across a room, not a body saying how hungry it is.
INDICATOR_BRIGHTNESS = 100

# How long the head stays lit after a decode. Asked for as five seconds;
# it is also a little longer than one send cycle (4.35s), so consecutive
# reads of the same male run together into a steady light rather than
# flickering once a burst.
HEAD_SECONDS = 5.0

# How often the alignment is recomputed. Every check reads the bar's
# position and all five bodies' off the servo bus, which is far too much
# to do on BaseThread's 10ms tick - and an alignment moves at servo
# speed, so four times a second is already finer than the thing being
# measured. Decode events are noticed on every tick regardless: those
# cost nothing, being a timestamp already in memory.
GEOMETRY_INTERVAL = 0.25

# How many events the page keeps. Long enough to hold a few minutes of a
# run, since what tells a stray glitch from a systematic one is the run
# of events either side of it.
EVENT_HISTORY = 80


class TestSearch(BaseThread):
    # What this does to the room for as long as it runs.
    scenario_names = ("search-reading-test",)

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._events = []

        self._read_ok = 0
        self._read_wrong = 0
        self._misses = 0
        self._founds = 0

        # Per female: the answer she is currently holding, the span she
        # is in view for, and when her head should go out.
        self._current_reading = {}
        self._view_span = {}
        self._head_until = {}

        self._last_geometry = 0.0
        self._in_view = {}
        self._warnings = []

        self["set males asking O, females wanting P"] = self._preset_no_match
        self["set every drive to full"] = self._preset_everything_full

    @property
    def name(self):
        return "test search"

    @property
    def males(self):
        return self.drivers.males

    @property
    def females(self):
        return self.drivers.females

    # --- drive presets ---------------------------------------------------

    def _preset_no_match(self, request=None):
        """Everybody searching, and no female wanting what any male asks.

        The state to run a *reading* test in. Both sexes are well clear of
        the inert floor, so everything moves and everything calls, while
        every male asks for O and every female is short only of P.

        Which does **not** mean no female ever finds anybody, and the
        difference is the useful part: she acts on what she *read*, not on
        what was sent, so a misread of "O" as "P" does overlap and does
        end her search. Under this preset every `found` event is therefore
        a misread by construction - a second, independent count of the
        thing the run is measuring, arrived at without comparing anything.
        """
        for male in self.males:
            male.drives.set_p_to_0_o_to_100()
        for female in self.females:
            female.drives.o_drive.value = 0
            female.drives.p_drive.value = 100
            female.drives.update()

    def _preset_everything_full(self, request=None):
        """Every appetite at full: everyone asks for both, so every female
        matches every male she reads. Use it to exercise the find - which
        this test logs and then undoes - rather than to measure reading."""
        for body in list(self.males) + list(self.females):
            body.drives.o_drive.value = 100
            body.drives.p_drive.value = 100
            body.drives.update()

    # --- the run ---------------------------------------------------------

    def run(self):
        now = datetime.now()
        file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h"
            f"_{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = file_path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._start_time = time()
        self._file.write(
            "seconds, event, female, male in view, expected drive, "
            "detected male, detected drive, correct, seconds in view, reading\n"
        )
        self._events = []
        self._read_ok = self._read_wrong = self._misses = self._founds = 0
        self._current_reading = {female.name: None for female in self.females}
        self._view_span = {female.name: None for female in self.females}
        self._head_until = {}
        self._last_geometry = 0.0

        self._warn_about_inert_bodies()

        # Each male and each female searches; the bar is left to work out
        # for itself whether it should be moving, which is the behaviour
        # under test as much as the reading is.
        for male in self.males:
            male.search.start(started_by=self)
        for female in self.females:
            female.search.start(started_by=self)
        self.drivers.bar.start(started_by=self)

    def _warn_about_inert_bodies(self):
        """Say, once, which bodies are going to do nothing.

        A satisfied male never calls and a satisfied female never looks,
        so a run started with the drives left where the last test put them
        produces a long clean CSV of nothing at all. Deliberately a
        warning and not a refusal: a run with one male quiet is a
        perfectly good way to test the other one.
        """
        self._warnings = []
        for body in list(self.males) + list(self.females):
            if body.is_satisfied():
                self._warnings.append(
                    f"{body.name} wants nothing and will not search - "
                    "set its drives above the interested floor"
                )
        for warning in self._warnings:
            self.log(f"WARNING: {warning}")

    def setdown(self):
        for female in self.females:
            self._clear_head(female)
        self._start_time = None
        self._file.close()

    def loop(self):
        now = time()

        # Cheap every tick: a decode is a timestamp already in memory.
        if (now - self._last_geometry) >= GEOMETRY_INTERVAL:
            self._last_geometry = now
            self._refresh_geometry()

        for female in self.females:
            self._poll_female(female, now)

        self._expire_heads(now)

    # --- what she can see ------------------------------------------------

    def _refresh_geometry(self):
        """Which male, if any, is lined up on each female right now.

        The same three conditions the simulator uses to decide whether her
        sensor sees anything (`virtual_serial_port._sensor_value`): she is
        near her own origin, he is near his, and the bar is within a
        threshold of their meeting angle. Worth knowing that on the
        simulator this cannot be wrong, because the simulator *is* this
        rule - the prediction only means something on real hardware,
        which is the whole reason for running this there.
        """
        bar = self.drivers.bar
        thresholds = self.colloquy.params["near origin threshold"]

        try:
            bar_angle = bar.angle.get()
            male_angles = {male.name: male.angle.get() for male in self.males}
            female_angles = {f.name: f.angle.get() for f in self.females}
        except Exception as error:
            # A servo read can fail transiently; losing one alignment
            # sample is not worth ending a forty-minute run over.
            self.log(f"Could not read positions for the alignment check: {error}")
            return

        for female in self.females:
            in_view = None
            if abs(female_angles[female.name]) < thresholds["female"]:
                for male in self.males:
                    if abs(male_angles[male.name]) >= thresholds["male"]:
                        continue
                    meeting = bar.meeting_angle(male.name, female.name)
                    if abs(bar_angle - meeting) < thresholds["bar"]:
                        in_view = male
                        break
            self._in_view[female.name] = in_view

    def _blinking_male_in_view(self, female):
        """The male she could be reading: in view *and* actually sending."""
        male = self._in_view.get(female.name)
        if male is None:
            return None
        if not male.search.blink.is_started:
            return None
        return male

    # --- one female, one tick --------------------------------------------

    def _poll_female(self, female, now):
        read_pattern = female.search.read_pattern
        male = self._blinking_male_in_view(female)

        self._track_view_span(female, male, now)

        # One event per *episode*, not per decode. read_pattern decodes on
        # every tick it can - about 60ms - and holds the answer for two
        # send cycles afterwards, so a female with a male steadily in view
        # produces a new successful decode fifteen times a second. Logging
        # each of them turned half a second of her reading male2 correctly
        # into fourteen identical rows, which is one fact written fourteen
        # times. So an event is a *change* in what she is holding: a new
        # answer, or the same answer after having lost it. Same reasoning
        # as test_read_pattern's readings.episodes(), applied at the point
        # of writing rather than afterwards.
        current = read_pattern.last_match
        if current != self._current_reading[female.name]:
            self._current_reading[female.name] = current
            if current is not None:
                self._log_read(female, male, current, now)

        self._restart_search_if_it_found_somebody(female, now)

    def _track_view_span(self, female, male, now):
        """Open, extend and close the window in which she could have read.

        A span is one continuous stretch with the same blinking male lined
        up on her. It closes when he leaves, when a different male takes
        his place, or when she reads - and a span that closes long enough
        to have carried a whole burst, with nothing decoded in it, is a
        miss.
        """
        span = self._view_span[female.name]

        if male is None:
            if span is not None:
                self._close_view_span(female, now)
            return

        if span is None:
            self._view_span[female.name] = [male.name, now, 0, False]
            return

        if span[0] != male.name:
            # The bar carried a different male into her view.
            self._close_view_span(female, now)
            self._view_span[female.name] = [male.name, now, 0, False]
            return

        # Still the same male. Report a long silent span while it is
        # happening rather than only when it ends, so a female who never
        # reads anybody shows up on the page during the run and not after
        # it. `span[3]` keeps it to one miss per span.
        if not span[3] and span[2] == 0 and (now - span[1]) >= events.MISS_AFTER:
            span[3] = True
            self._log_miss(female, span[0], now - span[1], now)

    def _close_view_span(self, female, now):
        span = self._view_span[female.name]
        self._view_span[female.name] = None
        if span is None:
            return
        male_name, started_at, reads, reported = span
        if reads == 0 and not reported and (now - started_at) >= events.MISS_AFTER:
            self._log_miss(female, male_name, now - started_at, now)

    def _restart_search_if_it_found_somebody(self, female, now):
        """Her search ends itself on a male she is short of. Undo that.

        Not a fault - it is `Search.loop()` doing what the installation
        wants. But the next step is reinforcement, which does not exist,
        and a run that stopped reading at the first good match would
        measure almost nothing. So the find is recorded and she is sent
        back to looking.
        """
        if female.search.is_started:
            return

        partner = female.search.take_partner()
        if partner is not None:
            male_name, drive = partner
            self._founds += 1
            self._write(
                events.FOUND,
                female=female.name,
                reading=events.describe_found(female.name, male_name, drive),
                now=now,
            )

        female.search.start(started_by=self)

    # --- writing it down --------------------------------------------------

    def _log_read(self, female, male, match, now):
        if match is None:
            return
        detected_male, detected_drive = match

        span = self._view_span[female.name]
        if span is not None:
            span[2] += 1

        in_view = male.name if male is not None else None
        expected_drive = male.drives.which_is_frustated() if male is not None else None

        reading = events.describe_read(
            female.name, in_view, expected_drive, detected_male, detected_drive
        )
        correct = events.is_correct(reading)
        if correct:
            self._read_ok += 1
        else:
            self._read_wrong += 1

        self._light_head(female, detected_male, now)
        self._write(
            events.READ,
            female=female.name,
            in_view=in_view,
            expected_drive=expected_drive,
            detected_male=detected_male,
            detected_drive=detected_drive,
            correct=correct,
            seconds_in_view=(now - span[1]) if span is not None else None,
            reading=reading,
            now=now,
        )

    def _log_miss(self, female, male_name, seconds, now):
        self._misses += 1
        self._write(
            events.MISS,
            female=female.name,
            in_view=male_name,
            seconds_in_view=seconds,
            reading=events.describe_miss(female.name, male_name, seconds),
            now=now,
        )

    def _write(
        self,
        kind,
        female,
        reading,
        now,
        in_view=None,
        expected_drive=None,
        detected_male=None,
        detected_drive=None,
        correct=None,
        seconds_in_view=None,
    ):
        seconds = now - self._start_time
        self._events.append((seconds, kind, reading))
        del self._events[:-EVENT_HISTORY]

        # Drive states are written as their label, never as the tuple:
        # ('O', 'P') carries a comma, which splits a row into two extra
        # columns in a file whose whole job is to be read afterwards.
        # test_read_pattern learnt that one the hard way.
        in_span = "" if seconds_in_view is None else f"{seconds_in_view:.1f}"
        self._file.write(
            f"{seconds}, {kind}, {female}, {in_view}, "
            f"{events.drive_label(expected_drive)}, "
            f"{detected_male}, {events.drive_label(detected_drive)}, "
            f"{correct}, {in_span}, {reading}\n"
        )

    # --- the readout ------------------------------------------------------

    def _light_head(self, female, detected_male, now):
        head = female.neopixels.head
        # Set explicitly: this test does not run her Drives thread, and a
        # segment's brightness starts at 0, so without this the arduino is
        # sent a correctly-coloured black.
        head.brightness.value = INDICATOR_BRIGHTNESS
        head.color = HEAD_COLOR_BY_MALE.get(detected_male, head.color)
        head.on()
        self._head_until[female.name] = now + HEAD_SECONDS

    def _expire_heads(self, now):
        for name, until in list(self._head_until.items()):
            if now < until:
                continue
            del self._head_until[name]
            for female in self.females:
                if female.name == name:
                    self._clear_head(female)

    def _clear_head(self, female):
        female.neopixels.head.off()

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        # Everything a tester needs while a run is going, without leaving
        # the test's own page: each body's drives to change what it is
        # asking for, each body's search to stop one of them by hand, and
        # the bar to watch it decide.
        #
        # Keyed by body name rather than by the node's own name. All five
        # searches call themselves "search", and all three females call
        # their drives "drives" (only a male's carries his name), so
        # keying by `node.name` would silently keep just the last of each
        # - two of the three females would simply be missing from the
        # page. The label under the link is still the node's own name;
        # the key is what makes the row and its URL unambiguous.
        children = {}
        for body in list(self.males) + list(self.females):
            children[f"{body.name} drives"] = body.drives
            children[f"{body.name} search"] = body.search
        children["bar"] = self.drivers.bar
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["set males asking O, females wanting P"] = self._preset_no_match
        states["set every drive to full"] = self._preset_everything_full

        leaf = leaves.into(states, path)

        # What each body is asking for right now, in one place: this is
        # what decides whether anything happens at all, and it is
        # otherwise five clicks away.
        leaf(
            "who is calling",
            ", ".join(
                f"{male.name}: {events.drive_label(male.drives.which_is_frustated())}"
                for male in self.males
            ),
        )
        leaf(
            "who is looking",
            ", ".join(
                f"{f.name}: {events.drive_label(f.drives.which_is_frustated())}"
                for f in self.females
            ),
        )

        if self._warnings:
            states["warnings"] = leaves.pre(
                path, "warnings", "\n".join(self._warnings)
            )

        if self._start_time is None:
            return states

        leaf("bar is wandering", "yes" if self.drivers.bar.search.is_started else "no")
        leaf(
            "in view now",
            ", ".join(
                f"{name}: {male.name if male else '-'}"
                for name, male in sorted(self._in_view.items())
            )
            or "not checked yet",
        )
        leaf(
            "events",
            f"{self._read_ok} read correctly / {self._read_wrong} read wrong / "
            f"{self._misses} missed / {self._founds} found",
        )

        lines = events.tally_lines(
            (kind, reading) for _seconds, kind, reading in self._events
        )
        states["what went wrong"] = leaves.pre(
            path,
            "what went wrong",
            "\n".join(lines) if lines else "nothing wrong yet",
        )
        states["last events"] = leaves.pre(
            path,
            "last events",
            "\n".join(
                f"{seconds:6.1f}s  {reading}"
                for seconds, _kind, reading in reversed(self._events)
            )
            or "nothing yet",
        )
        return states
