from datetime import datetime
from time import time

import pandas as pd

from colloquy.base_thread import BaseThread
from colloquy.utils import timelap_to_string

from ..results import Results
from ..utils import plot_sensor_by_bar_offset_as_svg
from colloquy.ui import leaves


class TestSeeingMale1AsTheBarTurns(BaseThread):
    """Male1 stands still with his ring lit, and the bar carries him past
    every female while each one's sensor is read.

    The sibling test asks whether a female reads light where there is
    none. This asks the other half of the same question: whether she reads
    light where there *is* some - and at what relative placing of the two
    bodies she starts to.

    So: every light off except male1's ring, male1 held at his origin, all
    three females held at theirs, and the bar sweeping its whole travel
    back and forth. Nothing moves but the bar, which means the only thing
    changing what a female can see is how far round the bar has carried
    male1 towards her.

    Each female gets her own graph: the bar's angle minus her own across,
    sensor value up, the average reading at that offset and the spread
    there, with the threshold drawn across it. Somewhere on it there
    should be a hump - the offsets at which she can see him - rising
    through the threshold and falling away again.

    Where that hump sits is the second thing this measures. The graph
    marks where params says the bar puts male1 in front of her, which is 0
    for female1 (her meeting angle *is* the bar's origin) and 64.5 and 126
    degrees for female2 and female3. A hump centred away from that marker
    is an interaction origin that wants correcting; a graph with no hump
    at all is a female who never sees him, which is a sensor, an aim or a
    threshold to look at.

    Run it with the installation stopped - it refuses otherwise, since
    every body running turns its own lights on and moves on its own, which
    is the opposite of what this measures.
    """

    # One degree per bin, as the sibling uses. The bar travels 293
    # degrees, so about three hundred bins across a run.
    ANGLE_BIN = 1.0

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
            self.plot()

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

        # Everything that is not the bar is placed and left there, so a
        # reading can be attributed to the bar's angle alone. Waited for:
        # a sample taken while a body is still swinging into place is
        # filed under an aim it does not have yet.
        self.male.turn_to_origin()
        for female in self.females:
            female.turn_to_origin()
        self.bar.turn_to_origin()

        self.male.dxl.wait_for_servo()
        for female in self.females:
            female.dxl.wait_for_servo()
        self.bar.dxl.wait_for_servo()

        self.male.neopixels.ring.on()
        self.bar.turn_back_and_forth.start(started_by=self)

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

        # What the graph is against: where the bar is, relative to where
        # she is aimed. Computed here rather than recorded, so a run
        # already on disk re-plots the same way.
        df["bar offset"] = df["bar angle"] - df["angle"]

        threshold = self.colloquy.params["photosensor_threashold"]
        for female in self.females:
            output = file_path.with_name(f"{female.name} {file_path.stem}.svg")
            plotted = plot_sensor_by_bar_offset_as_svg(
                output=output,
                df=df,
                body=female.name,
                threshold=threshold,
                meeting_angle=self.bar.meeting_angle(self.LIT_MALE, female.name),
                bin_width=self.ANGLE_BIN,
            )
            if plotted is None:
                continue
            rows = df[df["body"] == female.name]
            above = int(rows["value"].gt(threshold).sum())
            self.log(f"{female.name}: {above} readings above the threshold.")

    @property
    def snapshot_children(self):
        return {
            self._results.name: self._results,
            self.bar.turn_back_and_forth.name: self.bar.turn_back_and_forth,
        }

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
