from colloquy.base_thread import BaseThread
from ..angle import Angle
from ..angle.conversion import REDUCTIONS
from ..dxl_origin import DXLOrigin
from .search import Search
from .turn_back_and_forth_around_f1 import TurnBackAndForthAroundF1
from .turn_back_and_forth import TurnBackAndForth


class Bar(BaseThread):
    # What the rail does, and what it is for: it is the only thing that
    # brings a male and a female into each other's view.
    scenario_names = ("the-bar",)

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._position_memory = None

        self._dxl_origin = DXLOrigin(owner=self)
        self._angle = Angle(owner=self, reduction=REDUCTIONS["bar"])
        self.turn_back_and_forth_around_f1 = TurnBackAndForthAroundF1(owner=self)
        self.turn_back_and_forth = TurnBackAndForth(owner=self)

        self._dxl = owner.u2d2.dxls[self.name]

        self._search = Search(owner=self)

        self[self.search.name] = self.search
        self[self.dxl_origin.name] = self.dxl_origin
        self[self.angle.name] = self.angle
        self["set current position as dxl origin"] = (
            self.set_current_position_as_dxl_origin
        )

    @property
    def params(self):
        return self.owner.params

    @property
    def dxl_origin(self):
        return self._dxl_origin

    def meeting_angle(self, male, female):
        """How far the bar has to turn from its origin to bring this male
        in front of this female, in degrees of the bar."""
        return self.params["bar"]["interaction_origins"][male][female]

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
    def angle(self):
        """How far it has turned from its origin, in degrees of the bar."""
        return self._angle

    @property
    def travel(self):
        """End to end, in degrees of the bar.

        Read from params on every use, so a range edited on the page takes
        effect on its next crossing. Unlike a body, its origin is one end
        of the travel rather than the middle, so this runs 0 to +293 and
        never goes negative. 292.969 is the 10000 servo units it had
        before this layer existed, through its 1:3 reduction."""
        return self.params["bar"]["motion range"]

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

    def turn_to(self, degrees):
        self.angle.turn_to(degrees)

    def turn_to_max_position(self):
        self.angle.turn_to(self.travel)
        self._position_memory = "max"

    def turn_to_min_position(self):
        self.angle.turn_to(0)
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
        """The bar is the one that decides whether the bar is wandering.

        It has no appetite of its own, so the only thing that can tell it
        whether to move is what the males are doing: the rail exists to
        carry a calling male past a female, and with nobody calling there
        is nothing to carry. So it watches their search flags and follows
        them in both directions.

        Only the starting half was here before, which meant the first male
        to get hungry set the bar going for the rest of the run
        (CODE_DOCUMENTATION 4.1). Stopping is the half that makes the
        piece able to come to rest: males go quiet as their appetites
        fall, and when the last one does the bar stops where it stands
        rather than sliding back and forth in front of nobody.

        Deliberately asking `search.is_started` rather than
        `is_satisfied()`: what matters is whether he is *calling*, which
        is a thread that may still be winding down a moment after his
        drives changed. Reading the flag keeps the two in step.
        """
        anyone_calling = any(male.search.is_started for male in self.males)

        if anyone_calling:
            if not self.search.is_started:
                self.search.start(started_by=self)
            return

        if self.search.is_started:
            self.log("No male is calling - the bar stops wandering.")
            self.search.stop()

    def setup(self):
        self.dxl.init_hardware()
        return

    def setdown(self):
        return

    def get_states(self, *args):
        states = {
            "path": ("drivers", self.name),
            "name": self.name,
        }
        if args:
            raise NotImplementedError(self)
        return states

    def turn_to_origin(self):
        self.angle.turn_to_origin()

    def set_male_in_front_of_female(self, male, female):
        """Non-blocking: writes the goal position and returns immediately,
        so a caller that wants to stay responsive (interruptible by
        stop()/emergency_stop() rather than stuck in wait_for_servo()'s
        busy-loop) can poll is_moving itself instead."""
        self.angle.turn_to(self.meeting_angle(male, female))

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
                "angle": self.angle,
                "dxl origin": self.dxl_origin,
                self.dxl.name: self.dxl,
                "search": self.search,
            }
        )
        return self._with_scenarios(children)

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
