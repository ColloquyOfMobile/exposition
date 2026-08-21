from datetime import datetime
from time import time

import pandas as pd

from colloquy.base_thread import BaseThread
from colloquy.utils import timelap_to_string

from ..utils import plot_sensor_by_angle_as_svg
from ..results import Results
from colloquy.ui import leaves


class TestForFalsePositives(BaseThread):
    # What the room looks like during it - which is nothing at all, in
    # the dark, for five minutes.
    scenario_names = ("false-positives-test",)
    """Every female sweeps in the dark, and every reading is filed under
    the angle she was pointing at when it was taken.

    The question is whether a female ever reads "light" when there is
    none. Her decoder calls a sample lit whenever it clears one fixed
    threshold (CODE_DOCUMENTATION 8.2), so anything in the room that is
    brighter from one direction - a window, a doorway, a monitor, the
    ceiling - can put a false bit into a pattern she is reading, and no
    amount of pattern logic recovers from that.

    So: every light in the installation off, all three females sweeping
    their own travel, and the sensor read as fast as the Arduino will
    answer. A sweeping body passes the same angle many times over a run,
    from both directions, so each angle ends up with a spread of readings
    taken at the same aim - which is what says whether that aim is steady.

    Each female gets her own graph, angle across, sensor value up, with
    two lines: the average reading at that angle, and the spread (max
    minus min) there. The threshold is drawn across both. A flat average
    well under it with a small spread is a sensor to trust; a bump in the
    average is something bright from that direction; a tall spread is an
    aim where the reading is not repeatable.

    The graphs are written next to the run's CSV under local/test
    results/, and every run is on the page under "results" - which is the
    only way to see them without opening that folder by hand.

    Run it with the installation stopped - it refuses otherwise, since
    every body running turns its own lights on and moves on its own, which
    is the opposite of what this measures.
    """

    # One degree per bin. A female sweeps 58.6 degrees, so that is around
    # sixty bins across her travel, and she moves 0.14 degrees between two
    # readings taken 15ms apart - far inside a bin.
    ANGLE_BIN = 1.0

    DURATIONS = (60, 5 * 60, 15 * 60, 30 * 60)

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
        # Fixed, unlike its siblings, which carry their duration in their
        # name: this one's duration is chosen on the page, and a node that
        # renames itself when you set it would move out from under the
        # link you are standing on.
        return "test for false positives in the dark"

    @property
    def duration(self):
        return self._duration

    @property
    def females(self):
        return self.drivers.females

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
        for node in (
            self.drivers,
            self.drivers.bar,
            *self.drivers.males,
            *self.females,
        ):
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
        self._file.write("seconds, body, angle, value\n")

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

        # The whole point of the run: nothing lit anywhere, including the
        # males' rings, which the sibling tests leave on.
        self.drivers.neopixels.turn_all_off()

        for female in self.females:
            female.turn_back_and_forth.start(started_by=self)

    def loop(self):
        elapsed = time() - self._start_time

        for female in self.females:
            # Angle first: it is the cheaper read of the two, and the
            # sensor value is the one that has to be attributed to where
            # she was pointing.
            angle = female.angle.get()
            value = female.light_sensor.read()
            self._file.write(f"{elapsed}, {female.name}, {angle}, {value}\n")
            self._sample_count += 1

        if elapsed > self._duration:
            self._outcome = f"finished, {self._sample_count} readings"
            self.stop()

    def setdown(self):
        for female in self.females:
            female.turn_back_and_forth.stop()
        self._start_time = None
        if self._outcome:
            self.log(f"Outcome: {self._outcome}")
        self._file.close()

    def plot(self, file_path=None):
        """One graph per female, next to the CSV.

        Defaults to the run that just finished; `results` passes an older
        run's CSV to redraw it - after the threshold in params has moved,
        say, since the threshold is drawn into the picture.
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
            output = file_path.with_name(f"{female.name} {file_path.stem}.svg")
            plotted = plot_sensor_by_angle_as_svg(
                output=output,
                df=df,
                body=female.name,
                threshold=threshold,
                bin_width=self.ANGLE_BIN,
            )
            if plotted is None:
                continue
            above = int(df[(df["body"] == female.name)]["value"].gt(threshold).sum())
            self.log(f"{female.name}: {above} readings above the threshold.")

    @property
    def results(self):
        return self._results

    @property
    def snapshot_children(self):
        children = {self._results.name: self._results}
        for female in self.females:
            children[female.turn_back_and_forth.name] = female.turn_back_and_forth
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        for key, command in self._commands.items():
            states[key] = command

        leaf = leaves.into(states, path)

        leaf("duration", timelap_to_string(seconds_elapsed=self._duration))
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
