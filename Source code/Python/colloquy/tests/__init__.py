# from colloquy.wsgi.root.body.action_item import ActionItem
import traceback
from colloquy.base import Base
from pathlib import Path
import traceback


from .html import HTML

# from .test1 import Test1
from .test_drive_light_values import TestDriveLightValues
from .test_male_patterns import TestMalePatterns
from .test_light_sensor_values import TestLightSensorValues
from .test_read_pattern import TestReadPattern
from .test_movements import TestMovements
from .test_graph_zoom import TestGraphZoom
from .test_neopixels import TestNeopixels
from .test_sensors import TestSensors


class Tests(Base):
    def __init__(self, owner):
        super().__init__(owner)
        self._hardware = self.owner.hardware
        if self.name not in self.owner.params:
            self._params = self.owner.params[self.name] = {}
        else:
            self._params = self.owner.params[self.name]

        self._html = HTML(owner=self)
        result_folder = Path("local/test results")
        if not result_folder.exists():
            result_folder.mkdir()
        self.test_drive_light_values = TestDriveLightValues(owner=self)
        self.test_male_patterns = TestMalePatterns(owner=self)
        self.test_light_sensor_values = TestLightSensorValues(
            owner=self, result_folder=result_folder
        )
        self.test_read_pattern = TestReadPattern(
            owner=self, result_folder=result_folder
        )
        self.test_movements = TestMovements(owner=self, result_folder=result_folder)
        self.test_graph_zoom = TestGraphZoom(owner=self)
        self.test_neopixels = TestNeopixels(owner=self, result_folder=result_folder)
        self.test_sensors = TestSensors(owner=self, result_folder=result_folder)

        self[self.html.name] = self.html.handle_request
        # self.add(self.test1)

        self._threaded_tests = {
            self.test_drive_light_values,
            self.test_male_patterns,
            self.test_light_sensor_values,
            self.test_read_pattern,
            self.test_movements,
            self.test_neopixels,
            self.test_sensors,
        }

    # def __call__(self, request):
    # request = Path(request)
    # if not request.parts:
    # raise NotImplementedError

    # key, *leftover = request.parts

    # if key in self:
    # self[key](request="/".join(leftover))
    # return

    # raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

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
        return "tests"

    @property
    def workspace(self):
        return self

    @property
    def hardware(self):
        return self._hardware

    def stop(self):
        for test in self._threaded_tests:
            test.stop()

    @property
    def snapshot_children(self):
        children = {}
        for test in self._threaded_tests:
            children[test.name] = test
        children[self.test_graph_zoom.name] = self.test_graph_zoom
        return children

    # def snapshot(self, path, focus_path):
    # states = super().snapshot(path=path)
    # _path = states["path"]
    # states[self.test_drive_light_values.name] = self.test_drive_light_values.snapshot(path=_path)
    # states[self.test_male_patterns.name] = self.test_male_patterns.snapshot(path=_path)
    # states[self.test_light_sensor_values.name] = self.test_light_sensor_values.snapshot(path=_path)
    # return states

    # def snapshot_as_child(self, path):
    # states = super().snapshot(path=path)
    # _path = states["path"]
    # if self._is_opened:
    # states[self.test_drive_light_values.name] = self.test_drive_light_values.snapshot(path=_path)
    # states[self.test_male_patterns.name] = self.test_male_patterns.snapshot(path=_path)
    # states[self.test_light_sensor_values.name] = self.test_light_sensor_values.snapshot(path=_path)
    # return states
