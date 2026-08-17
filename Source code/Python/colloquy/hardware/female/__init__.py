from .neopixels import Neopixels  # Head, BodyO, BodyP, Feet
from .drives import Drives
from pathlib import Path
from colloquy.base_thread import BaseThread
from .light_sensor import LightSensor
from ..dxl_origin import DXLOrigin
from .dxl_position import DXLPosition
from .search import Search
from .reinforcement import Reinforcement
from ..turn_back_and_forth import TurnBackAndForth
from .test import Test


class Female(BaseThread):
    def __init__(
        self,
        owner,
        id_number,
    ):
        self._name = f"female{id_number}"
        self._id_number = id_number
        super().__init__(owner=owner)
        self._position_memory = None

        self._motion_range = 2000
        self._dxl_origin = DXLOrigin(owner=self)
        self._position = DXLPosition(owner=self)

        self._light_sensor = LightSensor(owner=self, name="light sensor")
        self._dxl = owner.u2d2.dxls[self.name]
        self._arduino = owner.arduino

        self._drives = Drives(owner=self)
        self._search = Search(owner=self)
        self._reinforcement = Reinforcement(owner=self)
        self.turn_back_and_forth = TurnBackAndForth(owner=self)

        self._neopixels = Neopixels(owner=self)
        self._test = Test(owner=self)

        self[self.neopixels.name] = self.neopixels
        self[self.drives.name] = self.drives
        self[self.test.name] = self.test
        self[self.search.name] = self.search
        self[self.reinforcement.name] = self.reinforcement
        self[self.dxl_origin.name] = self.dxl_origin
        self[self.position.name] = self.position
        self["set current position as dxl origin"] = (
            self.set_current_position_as_dxl_origin
        )
        self[self.light_sensor.name] = self.light_sensor

    @property
    def params(self):
        return self.owner.params

    @property
    def dxl_origin(self):
        return self._dxl_origin

    @property
    def dxl(self):
        return self._dxl

    @property
    def test(self):
        return self._test

    @property
    def search(self):
        return self._search

    @property
    def reinforcement(self):
        return self._reinforcement

    @property
    def drives(self):
        return self._drives

    @property
    def id_number(self):
        return self._id_number

    @property
    def female(self):
        return self

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return self._name

    @property
    def neopixels(self):
        return self._neopixels

    @property
    def is_moving(self):
        return self.dxl.is_moving

    @property
    def light_sensor(self):
        return self._light_sensor

    @property
    def position(self):
        return self._position

    @property
    def goal_position(self):
        return self.dxl.goal_position

    @property
    def torque_enabled(self):
        return self.dxl.torque_enabled

    @property
    def read_pattern(self):
        return self.search.read_pattern

    def set_current_position_as_dxl_origin(self, request=None):
        self.dxl_origin.set(self.dxl.position.read())

    def is_satisfied(self):
        return self.drives.o_drive.is_satisfied or self.drives.p_drive.is_satisfied

    def turn_to_max_position(self):
        value = self._dxl_origin.get() + self._motion_range // 2
        self.dxl.goal_position.write(value)
        self._position_memory = "max"

    def turn_to_min_position(self):
        value = self._dxl_origin.get() - self._motion_range // 2
        self.dxl.goal_position.write(value)
        self._position_memory = "min"

    def toggle_position(self):
        if self._position_memory is None:
            self.turn_to_max_position()
            return

        if self._position_memory == "max":
            self.turn_to_min_position()
            return

        if self._position_memory == "min":
            self.turn_to_max_position()
            return

    def turn_to_origin(self):
        value = self._dxl_origin.get()
        self.dxl.goal_position.write(value)

    def loop(self):
        """Her whole life, one tick at a time: get hungry, look, answer.

        Only ever starts one thing, and only when nothing else is running -
        the search and the reinforcement that may follow it own the body
        while they last.
        """
        if self.search.is_started or self.reinforcement.is_started:
            return

        if self.reinforcement.thread_errors:
            # Reinforcement is a placeholder that fails on its first tick,
            # and BaseThread refuses to restart a thread that has errored.
            # Going quiet here is the honest outcome until it is written:
            # retrying would spin, and would bury the error that says why
            # she stopped under a new one every tick.
            return

        partner = self.search.take_partner()
        if partner is not None:
            # Her search ended because she recognised a male asking for
            # something she wants. Hand the pair over.
            self.reinforcement.partner = partner
            self.reinforcement.start(started_by=self)
            return

        if not self.is_satisfied():
            self.search.start(started_by=self)

    def setup(self):
        self.dxl.init_hardware()
        self.drives.start(started_by=self)

    def setdown(self):
        self.drives.stop()
        self.search.stop()
        self.reinforcement.stop()

    @property
    def snapshot_children(self):
        children = {}
        children["dxl origin"] = self.dxl_origin
        children[self.dxl.name] = self.dxl
        children["search"] = self.search
        children["reinforcement"] = self.reinforcement
        children["drives"] = self.drives
        children["neopixels"] = self.neopixels
        children["light sensor"] = self.light_sensor
        return children

