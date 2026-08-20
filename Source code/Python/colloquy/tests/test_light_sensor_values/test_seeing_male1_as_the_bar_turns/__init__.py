from datetime import datetime
from time import time

import pandas as pd

from colloquy.base_thread import BaseThread
from colloquy.utils import timelap_to_string

from ..results import Results
from ..utils import (
    add_offsets,
    plot_sensor_by_alignment_offset_as_svg,
    plot_sensor_map_as_svg,
)
from colloquy.ui import leaves


class TestSeeingMale1AsTheBarTurns(BaseThread):
    # Including what the second graph is for and why a simulated run
    # cannot answer the question it asks.
    scenario_names = ("seeing-male1-test",)
    """Male1 stands still with his ring lit, and the bar carries him past
    every female while each one's sensor is read.

    The sibling test asks whether a female reads light where there is
    none. This asks the other half of the same question: whether she reads
    light where there *is* some - and at what relative placing of the two
    bodies she starts to.

    So: every light off except male1's ring, male1 alone held still at his
    origin, the bar sweeping its whole travel back and forth, and all
    three females swaying theirs throughout. He is the fixed thing; the
    two angles that decide whether she can see him both move, so a run
    covers their combinations rather than one slice of them.

    Each female gets two graphs.

    The first is her reading against the **alignment offset**: how far the
    bar is from putting him at her station, less her own aim (see
    `add_offsets`). Zero is the two of them lined up, for all three of
    them - the offset is measured from her own meeting angle, not from the
    bar's origin, which happens to be female1's and would otherwise put
    the other two humps at 64.5 and 126 degrees. The reading should climb
    towards zero and fall away either side. A hump off centre is an
    interaction origin that wants correcting; no hump at all is a sensor,
    an aim or a threshold to look at.

    The second is the map, and it is there because that subtraction is an
    assumption: that her sway and the bar's travel are measured in the
    same rotational sense and add up, which is a fact about how she is
    mounted rather than anything params or this code knows. It draws the
    two angles against each other with the reading as colour. Bright cells
    along a diagonal say they do add up and the first graph is the right
    way to read her; a bright rectangle says they are two independent
    windows and the first graph is smeared by the width of both; a
    diagonal the other way says the offset wants a plus where it has a
    minus.

    Run it with the installation stopped - it refuses otherwise, since
    every body running turns its own lights on and moves on its own, which
    is the opposite of what this measures.
    """

    # One degree per bin, as the sibling uses. The bar travels 293
    # degrees, so about three hundred bins across a run.
    ANGLE_BIN = 1.0

    # The map has two axes to fill instead of one, so its cells are wider
    # - a run that gives thirty readings to a degree of offset gives far
    # fewer to a degree of offset at a degree of aim.
    MAP_BIN = 2.0

    DURATIONS = (60, 5 * 60, 15 * 60, 30 * 60)

    LIT_MALE = "male1"

    def __init__(self, owner, result_folder, test_duration):
        super().__init__(owner=owner)

        self._duration = test_duration
        self._start_time = None
        self._sample_count = 0
        self._outcome = None

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file_path = None
        self._file = None
        self._results = Results(owner=self, dir_path=self._dir_path)

        self._commands = {}
        for seconds in self.DURATIONS:
            label = timelap_to_string(seconds_elapsed=seconds)
            self._commands[f"run for {label}"] = self._make_duration_setter(seconds)

    @property
    def name(self):
        # Fixed, like its sibling's: the duration is chosen on the page,
        # and a node that renames itself when you set it would move out
        # from under the link you are standing on.
        return "test seeing male1 as the bar turns"

    @property
    def duration(self):
        return self._duration

    @property
    def females(self):
        return self.hardware.females

    @property
    def male(self):
        return getattr(self.hardware, self.LIT_MALE)

    @property
    def bar(self):
        return self.hardware.bar

    @property
    def results(self):
        return self._results

    def _make_duration_setter(self, seconds):
        def setter(request=None):
            if self.is_started:
                self.log("Ignoring the new duration: stop the run first.")
                return
            self._duration = seconds

        return setter

    def _busy_bodies(self):
        """Anything already driving the bodies or their lights."""
        busy = []
        for node in (self.hardware, self.bar, *self.hardware.males, *self.females):
            if node.is_started:
                busy.append(node.name)
        return busy

    def run(self):
        now = datetime.now()
        self._file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = self._file_path.open("a")
        super().run(run_with=run_with)

        if self._started_by is None:
            try:
                self.plot()
            except Exception as error:
                # Outside BaseThread.run()'s own try/except, which has
                # already returned by now - so without this a failed plot
                # kills the thread with nothing on the page to say so, and
                # the run's data looks like it was never recorded.
                self.log(f"Plotting failed: {error!r}")
                self.thread_errors.append(error)

    def setup(self):
        self._start_time = time()
        self._sample_count = 0
        self._outcome = None
        self._file.write("seconds, body, bar angle, angle, value\n")

        busy = self._busy_bodies()
        if busy:
            self._outcome = f"refused: {', '.join(busy)} already running"
            self.log(
                f"Refusing to run: {', '.join(busy)} already running - stop the "
                "installation first, or it will light the very lights this test "
                "needs off and move the bodies while it measures them."
            )
            self.stop()
            return

        # One light in the room, and it is his. Everything off first,
        # including male2's ring, so nothing else can be what she sees.
        self.hardware.neopixels.turn_all_off()

        # He is the one thing held still: at his origin, lit, facing
        # out. Waited for, since a sample taken while he is still
        # swinging into place is filed under an aim he does not have yet.
        self.male.turn_to_origin()
        self.bar.turn_to_origin()
        self.male.dxl.wait_for_servo()
        self.bar.dxl.wait_for_servo()

        self.male.neopixels.ring.on()

        # Both of the angles the graphs are read against sweep, so a run
        # covers their combinations rather than one slice of them: the
        # bar carries him round and round, and each female sways her own
        # travel throughout.
        self.bar.turn_back_and_forth.start(started_by=self)
        for female in self.females:
            female.turn_back_and_forth.start(started_by=self)

    def loop(self):
        elapsed = time() - self._start_time

        # Once per row of females rather than once per female: it is the
        # same bar, and reading it three times would file three different
        # angles for one instant of one sweep.
        bar_angle = self.bar.angle.get()

        for female in self.females:
            angle = female.angle.get()
            value = female.light_sensor.read()
            self._file.write(
                f"{elapsed}, {female.name}, {bar_angle}, {angle}, {value}\n"
            )
            self._sample_count += 1

        if elapsed > self._duration:
            self._outcome = f"finished, {self._sample_count} readings"
            self.stop()

    def setdown(self):
        self.bar.turn_back_and_forth.stop()
        for female in self.females:
            female.turn_back_and_forth.stop()
        self.male.neopixels.ring.off()
        self._start_time = None
        if self._outcome:
            self.log(f"Outcome: {self._outcome}")
        self._file.close()

    def plot(self, file_path=None):
        """One graph per female, next to the CSV.

        Defaults to the run that just finished; `results` passes an older
        run's CSV to redraw it - after the threshold in params has moved,
        say, or an interaction origin, since both are drawn into the
        picture.
        """
        if file_path is None:
            file_path = self._file_path
        if file_path is None:
            return

        df = pd.read_csv(file_path, skipinitialspace=True)
        if df.empty:
            self.log("Nothing recorded, so nothing to plot.")
            return

        threshold = self.colloquy.params["photosensor_threashold"]
        for female in self.females:
            # Per female, since the offsets are measured from her own
            # meeting angle - the bar's origin is female1's, not theirs.
            # Computed here rather than recorded, so a run already on disk
            # re-plots the same way.
            meeting = self.bar.meeting_angle(self.LIT_MALE, female.name)
            rows = add_offsets(df[df["body"] == female.name], meeting_angle=meeting)
            if rows.empty:
                continue

            plot_sensor_by_alignment_offset_as_svg(
                output=file_path.with_name(f"{female.name} {file_path.stem}.svg"),
                df=rows,
                body=female.name,
                threshold=threshold,
                meeting_angle=meeting,
                bin_width=self.ANGLE_BIN,
            )
            plot_sensor_map_as_svg(
                output=file_path.with_name(f"{female.name} map {file_path.stem}.svg"),
                df=rows,
                body=female.name,
                threshold=threshold,
                bin_width=self.MAP_BIN,
            )
            above = int(rows["value"].gt(threshold).sum())
            self.log(f"{female.name}: {above} readings above the threshold.")

    @property
    def snapshot_children(self):
        children = {
            self._results.name: self._results,
            self.bar.turn_back_and_forth.name: self.bar.turn_back_and_forth,
        }
        for female in self.females:
            children[female.turn_back_and_forth.name] = female.turn_back_and_forth
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        for key, command in self._commands.items():
            states[key] = command

        leaf = leaves.into(states, path)

        leaf("duration", timelap_to_string(seconds_elapsed=self._duration))
        leaf("lit male", self.LIT_MALE)
        if self._start_time is not None:
            seconds_elapsed = time() - self._start_time
            leaf(
                "running during",
                timelap_to_string(seconds_elapsed=seconds_elapsed),
            )
            leaf("progress", f"{round(100 * seconds_elapsed / self._duration)}%")
            leaf("readings", self._sample_count)
        if self._outcome:
            leaf("outcome", self._outcome)
        return states
