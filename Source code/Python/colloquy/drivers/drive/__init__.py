from time import sleep
from threading import Lock
from colloquy.base_thread import BaseThread
from colloquy.input import Input

"""logic35_systems.ino: line 86
//act_drive
const int   internal_drive_LL = 600;      //interested floor, in samples     600 = 30 seconds
const int   internal_drive_UL = 3600;     //desperate floor, in samples     3600 = 3 minutes
const int   internal_drive_MAX = 4800;    //in samples                      4800 = 4 minutes
const int   internal_drive_adjustment_O = 1;
const int   internal_drive_adjustment_P  = 1;
int         internal_drive_O = 0;
int         internal_drive_P = 0;
int         internal_drive_state = 0;     //Undefined, Neither[Inert], O, P, OP
"""

"""logic35_systems.ino: line 196
const int color_orange[4] = {80, 255, 25, 16}; //GRBW/orangish
const int color_puce[4] = {180, 160, 0, 40}; //GRBW//greenish
"""


def which_is_frustated(o_drive, p_drive):
    """Which appetites a body is currently short of: (), ("O",), ("P",) or
    ("O","P").

    Shared by males and females, exactly as TJ's updateInternalDriveState()
    (internal.ino) is common to every unit: a male blinks this state, and a
    female answers only a male asking for something in it (Logic_fem.ino
    switches on her own state). It used to live on the male's Drives alone,
    so a female had no drive state at all and nothing to compare a decoded
    pattern against.

    Same five rules as the original, in a different order - "both
    satisfied" and "both frustrated" cannot hold at once, since the
    interested floor is below the desperate floor, so the order between
    those two is free.
    """
    with o_drive.lock, p_drive.lock:
        if o_drive.is_satisfied and p_drive.is_satisfied:
            return tuple()
        if o_drive.is_frustated and p_drive.is_frustated:
            return ("O", "P")
        if o_drive.value > p_drive.value:
            return ("O",)
        if p_drive.value > o_drive.value:
            return ("P",)
        if p_drive.value == o_drive.value:
            return ("O", "P")

        raise ValueError(f"Drive Error, {o_drive=}, {p_drive=}")


class Drive(BaseThread):
    # One appetite climbing, in the only terms it can be watched in:
    # how fast, and what changes colour on the way.
    scenario_names = ("one-appetite-rising",)

    def __init__(self, owner, name):
        assert name in ("O", "P")
        self._name = f"{owner.owner.name}'s {name} drive"  # name
        super().__init__(owner=owner)
        self._lock = Lock()

        self._value = self.body.params["drive start values"][self.body.name][name]

        self._step = 1
        self._body = owner.owner

        self._max = 100
        self._min = 0

        seconds_in_4min = 60 * 4
        self._update_interval = seconds_in_4min / self._max

        self._satisfaction_lim = 30 / self._update_interval

        seconds_in_3min = 60 * 3
        self._frustrated_lim = seconds_in_3min / self._update_interval

        self._input = Input(owner=self)

        self[self.input.name] = self.input

    @property
    def lock(self):
        return self._lock

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self.owner.owner

    @property
    def black(self):
        return dict(red=0, green=0, blue=0, white=0)

    @property
    def color(self):
        return dict(red=self.red, green=self.green, blue=self.blue, white=self.white)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    @property
    def input(self):
        return self._input

    @property
    def is_satisfied(self):
        return self.value < self._satisfaction_lim

    @property
    def is_frustated(self):
        return self.value > self._frustrated_lim

    def commit(self, value):
        self._value = int(value)
        if self._value > self._max:
            self._value = self._max
        self.owner.update()

    def decrease(self):
        with self.lock:
            self._value -= 20 * self._step
            if self._value < 0:
                self._value = 0
        self.owner.update()

    def increment(self):
        with self.lock:
            self._value += self._step
            if self._value > self._max:
                self._value = self._max

        self.owner.update()

    def loop(self):
        self.increment()
        sleep(self._update_interval)

    def setup(self):
        pass

    def setdown(self):
        pass

    def satisfy(self):
        self.o_drive = self._satisfaction_lim
        self.p_drive = self._satisfaction_lim

    @property
    def snapshot_children(self):
        return self._with_scenarios({})

    def snapshot_as_child(self, path):
        states = self._snapshot_base_states(path)
        if self._is_opened:
            states.update(
                {
                    "value": self.value,
                }
            )
        return states
