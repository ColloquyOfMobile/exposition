# from colloquy.wsgi.root.body.action_item import ActionItem
from time import time
from colloquy.utils import timelap_to_string

from colloquy.base_thread import BaseThread

# from .handle_html import HTML
from .test_with_only_female_moving import TestWithOnlyFemaleMoving
from .test_with_female_and_male_moving import TestWithFemaleAndMaleMoving
from .test_with_female_male_and_bar_moving import TestWithFemaleMaleAndBarMoving
from .test_with_everything_moving import TestWithEveryThingMoving
from .test_for_false_positives import TestForFalsePositives
from .test_seeing_male1_as_the_bar_turns import TestSeeingMale1AsTheBarTurns
from colloquy.ui import leaves


class TestLightSensorValues(BaseThread):
    # The sequence has no behaviour of its own: its scenario is the six
    # it runs, pulled in as sub-scenarios on one clock, which is what
    # the -> lines in it are for.
    scenario_names = ("light-sensor-sweep-test",)
    def __init__(self, owner, result_folder):
        super().__init__(owner)
        # self.opened = None
        self._queue = None
        self._running_test = None
        self._start_time = None

        if self.name not in self.owner.params:
            self._params = self.owner.params[self.name] = {}
        else:
            self._params = self.owner.params[self.name]

        test_duration = 30  # seconds

        # self._html = HTML(owner=self)
        self.test_with_only_female_moving = TestWithOnlyFemaleMoving(
            owner=self,
            result_folder=result_folder,
            test_duration=test_duration,
        )
        self.test_with_female_and_male_moving = TestWithFemaleAndMaleMoving(
            owner=self,
            result_folder=result_folder,
            test_duration=test_duration,
        )
        self.test_with_female_male_and_bar_moving = TestWithFemaleMaleAndBarMoving(
            owner=self,
            result_folder=result_folder,
            test_duration=30,  # 15*60,
        )
        self.test_with_everything_moving = TestWithEveryThingMoving(
            owner=self,
            result_folder=result_folder,
            test_duration=30 * 60,
        )
        self.test_for_false_positives = TestForFalsePositives(
            owner=self,
            result_folder=result_folder,
            # Its own duration is chosen on the page; this is where it
            # starts, and what the sequence below budgets for it.
            test_duration=5 * 60,
        )
        self.test_seeing_male1_as_the_bar_turns = TestSeeingMale1AsTheBarTurns(
            owner=self,
            result_folder=result_folder,
            # As its sibling: where its duration starts, and what the
            # sequence below budgets for it.
            test_duration=5 * 60,
        )
        self._drivers = self.owner.drivers

        # self[self.html.name] = self.html.handle_request
        # self.add(self.test1)

        self._threaded_tests = [
            self.test_with_only_female_moving,
            self.test_with_female_and_male_moving,
            self.test_with_female_male_and_bar_moving,
            self.test_with_everything_moving,
            self.test_for_false_positives,
            self.test_seeing_male1_as_the_bar_turns,
        ]

        self._duration = sum(test.duration for test in self._threaded_tests)

    @property
    def params(self):
        return self._params

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "test light sensor values"

    @property
    def workspace(self):
        return self

    @property
    def drivers(self):
        return self._drivers

    def setup(self):
        self._start_time = time()
        self._queue = list(self._threaded_tests)
        self._running_test = test = self._queue.pop(0)
        test.start(started_by=self)

    def setdown(self):
        self._start_time = None
        self._queue = None
        self._running_test = None
        self.drivers.male1.neopixels.ring.off()
        for test in self._threaded_tests:
            test.stop()
            test.join()
        for test in self._threaded_tests:
            # _file_path is only set once a sub-test's own run() actually
            # started (before setup()/loop() even run) - a sub-test still
            # sitting in the queue when this stops early (e.g. an
            # emergency stop mid-sequence) never got that far and has no
            # data to plot.
            if test._file_path is None:
                continue
            test.plot()

    def loop(self):
        if self._running_test.is_started:
            return
        if not self._queue:
            self.stop()
            return
        self._running_test = test = self._queue.pop(0)
        test.start(started_by=self)

    @property
    def snapshot_children(self):
        children = {}
        for test in self._threaded_tests:
            children[test.name] = test
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._start_time is not None:
            seconds_elapsed = time() - self._start_time
            states["running during"] = leaves.value(
                path,
                "running during",
                timelap_to_string(seconds_elapsed=seconds_elapsed),
            )
            states["progress"] = leaves.value(
                path,
                "progress",
                f"{round(100 * seconds_elapsed / self._duration)}%",
            )
            states["total duration"] = leaves.value(
                path,
                "total duration",
                timelap_to_string(seconds_elapsed=self._duration),
            )
        super()._snapshot_if_opened(path)
        return states
