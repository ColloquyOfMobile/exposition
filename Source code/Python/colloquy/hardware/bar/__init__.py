from pathlib import Path
from colloquy.base_thread import BaseThread
from ..dxl_origin import DXLOrigin
from .dxl_position import DXLPosition
from .search import Search
from .turn_back_and_forth_around_f1 import TurnBackAndForthAroundF1
from .turn_back_and_forth import TurnBackAndForth


class Bar(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._position_memory = None

        self._motion_range = 10000
        self._dxl_origin = DXLOrigin(owner=self)
        self._position = DXLPosition(owner=self)
        self.turn_back_and_forth_around_f1 = TurnBackAndForthAroundF1(owner=self)
        self.turn_back_and_forth = TurnBackAndForth(owner=self)

        self._dxl = owner.u2d2.dxls[self.name]

        self._search = Search(owner=self)

        self[self.search.name] = self.search
        self[self.dxl_origin.name] = self.dxl_origin
        self[self.position.name] = self.position
        self["set current position as dxl origin"] = (
            self.set_current_position_as_dxl_origin
        )

    @property
    def params(self):
        return self.owner.params

    @property
    def dxl_origin(self):
        return self._dxl_origin

    @property
    def male1_in_front_of_f1(self):
        origin = self.params["bar"]["dxl origin"]
        return self.params["bar"]["interaction_origins"]["male1"]["female1"] + origin

    @property
    def dxl(self):
        return self._dxl

    @property
    def search(self):
        return self._search

    @property
    def drives(self):
        return self._drives

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return "bar"

    @property
    def is_moving(self):
        return self.dxl.is_moving

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
    def males(self):
        return self.owner.males

    def set_current_position_as_dxl_origin(self, request=None):
        self.dxl_origin.set(self.dxl.position.read())

    def turn_to_max_position(self):
        value = self._dxl_origin.get() + self._motion_range
        self.dxl.goal_position.write(value)
        self._position_memory = "max"

    def turn_to_min_position(self):
        value = self._dxl_origin.get()
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

    def loop(self):
        if self.search.is_started:
            return

        for male in self.males:
            if male.search.is_started:
                self.search.start(started_by=self)
                return

    def setup(self):
        self.dxl.init_hardware()
        return

    def setdown(self):
        return

    def get_states(self, *args):
        states = {
            "path": ("hardware", self.name),
            "name": self.name,
        }
        if args:
            raise NotImplementedError(self)
        return states

    def turn_to_origin(self):
        value = self._dxl_origin.get()
        self.dxl.goal_position.write(value)

    def set_male_in_front_of_female(self, male, female):
        """Non-blocking: writes the goal position and returns immediately,
        so a caller that wants to stay responsive (interruptible by
        stop()/emergency_stop() rather than stuck in wait_for_servo()'s
        busy-loop) can poll is_moving itself instead."""
        origin = self.params["bar"]["dxl origin"]
        position = self.params["bar"]["interaction_origins"][male][female] + origin
        self.dxl.goal_position.write(position)

    def move_male_in_front_of_female_and_wait(self, male, female):
        self.set_male_in_front_of_female(male, female)
        self.dxl.wait_for_servo()

    def move_male1_in_front_of_female1_and_wait(self):
        self.move_male_in_front_of_female_and_wait("male1", "female1")

    def move_male1_in_front_of_female2_and_wait(self):
        self.move_male_in_front_of_female_and_wait("male1", "female2")

    def move_male1_in_front_of_female3_and_wait(self):
        self.move_male_in_front_of_female_and_wait("male1", "female3")

    @property
    def snapshot_children(self):
        children = {}
        children.update(
            {
                "dxl origin": self.dxl_origin,
                self.dxl.name: self.dxl,
                "search": self.search,
            }
        )
        return children

    def _snapshot_if_opened(self, path):
        # The move-and-wait commands used to live in snapshot_children,
        # which is walked with .snapshot_as_child() (see Base._snapshot_
        # if_opened) whenever this node is itself opened - fine for the
        # real Base children above, but a bare bound method has no such
        # method and crashes the instant this node is opened directly.
        # Inject them the same way BaseThread injects "start"/"stop".
        states = super()._snapshot_if_opened(path)
        states["move male1 in front of female1 and wait"] = (
            self.move_male1_in_front_of_female1_and_wait
        )
        states["move male1 in front of female2 and wait"] = (
            self.move_male1_in_front_of_female2_and_wait
        )
        states["move male1 in front of female3 and wait"] = (
            self.move_male1_in_front_of_female3_and_wait
        )
        return states
