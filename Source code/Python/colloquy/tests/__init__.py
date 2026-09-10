# from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.base import Base
from pathlib import Path

from .test_drive_light_values import TestDriveLightValues
from .test_male_patterns import TestMalePatterns
from .test_light_sensor_values import TestLightSensorValues
from .test_read_pattern import TestReadPattern
from .test_goertzel_ear import TestGoertzelEar
from .test_reinforcement import TestReinforcement
from .test_search import TestSearch
from .test_female_search import TestFemaleSearch
from .test_movements import TestMovements
from colloquy.ui.graph_view import GraphView, dummy_marks, dummy_series
from .test_neopixels import TestNeopixels
from .test_sensors import TestSensors
from .test_microphone_signal import TestMicrophoneSignal
from .test_audio_subsystem import TestAudioSubsystem
from .test_audio_at_12v import TestAudioAt12V
from .test_audio_loop import TestAudioLoop
from .test_audio_bringup import TestAudioBringup

from .group import TestGroup

AUTOTESTS = (
    "Press start and come back to the answer. Each of these writes down "
    "what it found - a CSV, a plot, a grid of verdicts, a diagnosis - so "
    "nobody has to be standing here while it runs. Some take forty "
    "minutes, which is exactly why they are the ones that can be left."
)

MANUAL_TESTS = (
    "You are the instrument. These produce light, sound and movement "
    "rather than a file: the answer is what you see, hear, or feel with a "
    "hand over a sensor, and one of them cannot even start its second "
    "half until somebody has moved a supply lead. Stay for these."
)


class Tests(Base):
    """The hardware tests, in two groups.

    The groups are `autotests` and `manual tests`, and the rule they are
    filed by is in `group.py`: does the run reach its answer on its own,
    or is a person the measuring instrument? That is the one thing worth
    knowing before pressing start, and a flat list of fourteen could not
    say it.

    Not to be confused with `pytest_tests/`, which is the other thing
    called tests here - pure-logic unit tests that never touch hardware.
    These are nodes in the tree, started from the page like any other
    command, and they move real or virtual servos over real time.
    """

    def __init__(self, owner):
        super().__init__(owner)
        self._drivers = self.owner.drivers
        if self.name not in self.owner.params:
            self._params = self.owner.params[self.name] = {}
        else:
            self._params = self.owner.params[self.name]

        result_folder = Path("local/test results")
        if not result_folder.exists():
            result_folder.mkdir()

        # The two groups are built first: a test's owner is its group, not
        # this node, so that its path - and so its URL - says which kind
        # it is.
        self._autotests = TestGroup(
            owner=self, name="autotests", summary=AUTOTESTS
        )
        self._manual_tests = TestGroup(
            owner=self, name="manual tests", summary=MANUAL_TESTS
        )

        # --- autotests: they write the answer down ------------------------
        auto = self._autotests
        self.test_light_sensor_values = TestLightSensorValues(
            owner=auto, result_folder=result_folder
        )
        self.test_read_pattern = TestReadPattern(
            owner=auto, result_folder=result_folder
        )
        self.test_reinforcement = TestReinforcement(
            owner=auto, result_folder=result_folder
        )
        self.test_search = TestSearch(owner=auto, result_folder=result_folder)
        self.test_female_search = TestFemaleSearch(
            owner=auto, result_folder=result_folder
        )
        self.test_movements = TestMovements(owner=auto, result_folder=result_folder)
        self.test_audio_subsystem = TestAudioSubsystem(
            owner=auto, result_folder=result_folder
        )
        self.test_audio_loop = TestAudioLoop(owner=auto, result_folder=result_folder)
        self.test_audio_bringup = TestAudioBringup(
            owner=auto, result_folder=result_folder
        )

        # --- manual tests: somebody has to be here ------------------------
        manual = self._manual_tests
        self.test_drive_light_values = TestDriveLightValues(owner=manual)
        self.test_male_patterns = TestMalePatterns(owner=manual)
        self.test_neopixels = TestNeopixels(owner=manual, result_folder=result_folder)
        self.test_sensors = TestSensors(owner=manual, result_folder=result_folder)
        # No result folder: half of what this one measures is a trace
        # in the Arduino IDE's plotter, on a port this process is
        # deliberately not holding, so a file of the other half would
        # record only the half that was never in doubt.
        self.test_microphone_signal = TestMicrophoneSignal(owner=manual)
        # It does keep a file, unlike the one above, and stays a manual
        # test all the same: what a run records is five bins over time
        # with every press marked on them, which is worth comparing with
        # last week's, while whether the tone was ever in the room is
        # still something only a person in it can say. The distinction
        # `group.py` files by is who does the perceiving, not whether
        # anything gets written down.
        self.test_goertzel_ear = TestGoertzelEar(
            owner=manual, result_folder=result_folder
        )
        self.test_audio_at_12v = TestAudioAt12V(
            owner=manual, result_folder=result_folder
        )

        auto.fill(
            tests=(
                self.test_light_sensor_values,
                self.test_read_pattern,
                self.test_reinforcement,
                self.test_search,
                self.test_female_search,
                self.test_movements,
                self.test_audio_subsystem,
                self.test_audio_loop,
                self.test_audio_bringup,
            ),
            # Thomas's boards live on an office desk and the installation
            # will never have them. Only his, now: the Goertzel ear went
            # to `manual tests` and stopped being gated at the same time,
            # for `test_audio_at_12v`'s reason - it is one Mega on one
            # lead and it travels, so the question is which lead, asked
            # and answered on its own page.
            bench_only=(self.test_audio_subsystem.name,),
        )
        manual.fill(
            tests=(
                self.test_drive_light_values,
                self.test_male_patterns,
                self.test_neopixels,
                self.test_sensors,
                self.test_microphone_signal,
                self.test_goertzel_ear,
                self.test_audio_at_12v,
            ),
            # Nothing bench-only here, and `test audio at 12v` is why it
            # stopped being so. The supply it measures is the piece's, so
            # the board gets carried *to* the installation and run beside
            # it - a gate on the hostname hid the test on the one machine
            # somebody would be standing at with a screwdriver. Whether
            # it is talking to a board or the stand-in is a question
            # about the chosen lead now, asked and answered on its own
            # page (`board is real`). See bench_board.py.
        )

        self[auto.name] = auto
        self[manual.name] = manual

        # Not a test of the piece and not startable hardware: the graph
        # tool itself, on dummy data, so it can be paged around without
        # waiting on a several-minute run. Filing it under either heading
        # would make the heading mean less, so it stays a direct child of
        # `tests`. See group.py. Three lines because that is the shape a
        # real run has.
        self.test_graph = GraphView(
            owner=self,
            series=[
                (name, dummy_series(seed=seed))
                for name, seed in (("female1", 7), ("female2", 8), ("female3", 9))
            ],
            # One on each of the dummy pulses, so the `go to` links and
            # `next mark` have something to arrive at.
            marks=dummy_marks(),
            name="test graph",
        )
        self[self.test_graph.name] = self.test_graph

        self._threaded_tests = set(auto.tests) | set(manual.tests)

    @property
    def params(self):
        return self._params

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def name(self):
        return "tests"

    @property
    def workspace(self):
        return self

    @property
    def drivers(self):
        return self._drivers

    @property
    def autotests(self):
        return self._autotests

    @property
    def manual_tests(self):
        return self._manual_tests

    def stop(self):
        for test in self._threaded_tests:
            test.stop()

    @property
    def snapshot_children(self):
        return {
            self._autotests.name: self._autotests,
            self._manual_tests.name: self._manual_tests,
            self.test_graph.name: self.test_graph,
        }
