from pathlib import Path
from colloquy.base_thread import BaseThread
from datetime import datetime
from colloquy.utils import timelap_to_string

from threading import Event
import traceback
from threading import Thread, Lock
from time import sleep, time
from ..utils import (
    read_and_store,
    post_process,
    plot_as_svg,
    plot_duration_histogram_as_svg,
    plot_counts_as_svg,
)
from .test_results import TestResults

class TestWithEveryThingMoving(BaseThread):
    def __init__(self, owner, result_folder, test_duration):
        super().__init__(owner=owner)
        self._default_duration = 5 * 60
        if self.name not in self.owner.params:
            self._params = self.owner.params[self.name] = {
                "duration": self._default_duration
            }
        else:
            self._params = self.owner.params[self.name]

        self._result_rows = None
        self._test_results = None

        self._start_time = None
        self._timelap = None
        if "duration" not in self.params:
            self.params["duration"] = self._default_duration
        self._duration = self.params["duration"]

        self._sensors_read = tuple(
            female.light_sensor.read for female in self.hardware.females
        )

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file_path = None
        self._file = None

    @property
    def params(self):
        return self._params

    @property
    def name(self):
        return "test with everything moving"

    @property
    def html(self):
        return self._html

    @property
    def duration(self):
        return self._duration

    def run(self):
        now = datetime.now()
        self._file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = self._file_path.open("a")
        super().run(run_with=run_with)

        # if self._started_by is None:
        # self.plot()

    def setup(self):
        self._file.write("seconds, female1, female2, female3" + "\n")
        self._start_time = time()
        self._result_rows = []

        self.hardware.bar.move_male1_in_front_of_female1_and_wait()

        for male in self.hardware.males:
            male.neopixels.ring.on()
            male.turn_back_and_forth.start(started_by=self)

        for female in self.hardware.females:
            female.turn_back_and_forth.start(started_by=self)

        self.hardware.bar.turn_back_and_forth.start(started_by=self)

    def setdown(self):
        self._start_time = None
        self.hardware.female1.turn_back_and_forth.stop()
        self.hardware.male1.turn_back_and_forth.stop()
        self.hardware.male1.neopixels.ring.off()
        self.hardware.male2.neopixels.ring.off()
        self.hardware.bar.turn_back_and_forth_around_f1.stop()
        self._test_results = TestResults(owner=self, result_rows=self._result_rows)

    def loop(self):
        timestamp = time() - self._start_time
        tokens = [timestamp]
        tokens.extend(read() for read in self._sensors_read)

        if self._result_rows is not None:
            self._result_rows.append(tokens)

        # line = ", ".join(str(token) for token in tokens)

        if timestamp > self._duration:
            self.stop()

    def plot(self):
        file_path = self._file_path
        output = file_path.with_name(f"post {file_path.stem}.csv")
        output, results = post_process(file=file_path, output=output)
        plot_as_svg(path=output)

        for column, data in results.items():
            durations = data["durations"]
            if len(durations) == 0:
                continue

            hist_output = file_path.with_name(f"hist {column} {file_path.stem}.svg")
            plot_duration_histogram_as_svg(output=hist_output, durations=durations)

            count_output = file_path.with_name(f"count {column} {file_path.stem}.svg")
            plot_counts_as_svg(
                output=count_output,
                counts=data["counts"],
                title=f"{column} pulse complementary cumulative histogram for a {timelap_to_string(seconds_elapsed=self._duration)} test.",
            )

    @property
    def snapshot_children(self):
        children = {}
        if self._test_results is not None:
            children[self._test_results.name] = self._test_results
        return children

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["duration"] = {
            "path": path + ("duration",),
            "name": "duration",
            "value": timelap_to_string(seconds_elapsed=self._duration),
        }

        if self._start_time is not None:
            seconds_elapsed = time() - self._start_time
            states["running during"] = {
                "path": path + ("running during",),
                "name": "running during",
                "value": timelap_to_string(seconds_elapsed=seconds_elapsed),
            }
            states["progress"] = {
                "path": path + ("progress",),
                "name": "progress",
                "value": f"{round(100 * seconds_elapsed / self._duration)}%",
            }
        return states
