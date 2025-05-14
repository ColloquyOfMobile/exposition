from time import time
from threading import Lock
from colloquy.thread_driver import ThreadDriver

"""logic35_systems.ino
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

class DrivesHandler(ThreadDriver):

    def __init__(self, owner, neopixel):
        name = f"{owner.name}_drives"
        ThreadDriver.__init__(self, name=name, owner=owner)
        self._neopixel = neopixel
        self.o_drive = 0
        self.p_drive = 0
        self._update_interval = 2
        self._timestamp = time()

        self._step_o = 2
        self._step_p = 3

        self._max = 255
        self._min = 0

        self._satisfied = 10
        self._frustrated = 235

        self._lock = Lock()

        self._orange = dict(red=255, green=165, blue=0, white=0)
        self._white = dict(red=0, green=0, blue=0, white=255)
        self._puce = dict(red=80, green=53, blue=60, white=125) #CC8899
        self._colors = {
            ("O",): self._puce,
            ("P",): self._orange,
            tuple(): self._puce,
            ("O", "P",): self._puce,
        }

    def __getitem__(self, key):
        for_max = list()
        with self._lock:
            if not key:
                return  max(self.o_drive, self.p_drive)

            if "O" in key:
                for_max.append(self.o_drive)
            if "P" in key:
                for_max.append(self.p_drive)
            return max(for_max)

    @property
    def color(self):
        return self._colors[self.state]

    @property
    def value(self):
        state = self.state
        return state, self[state], self._colors[state]


    @property
    def state(self):
        # raise NotImplementedError(f"Update to return a tuple for the states")
        with self._lock:
            o_satisfied = self.o_drive < self._satisfied
            p_satisfied = self.p_drive < self._satisfied
            o_frustated = self.o_drive > self._frustrated
            p_frustated = self.p_drive > self._frustrated

            if o_satisfied and p_satisfied:
                return tuple()
            if o_frustated and p_frustated:
                return ("O", "P")
            if self.o_drive > self.p_drive:
                assert not o_satisfied
                return ("O", )
            if self.p_drive > self.o_drive:
                assert not p_satisfied
                return ("P", )
            if self.p_drive == self.o_drive:
                return ("O", "P")

            raise ValueError(f"Drive Error, {self.o_drive=}, {self.p_drive=}")

    @property
    def is_unsatisfied(self):
        return bool(self.state)

    def __enter__(self):
        """Setup before loop."""
        self.stop_event.clear()

    def _loop(self):
        if time() - self._timestamp < self._update_interval:
            return
        self._timestamp = time()
        self._update()

    def _update(self):
        self.o_drive += self._step_o
        self.p_drive += self._step_p
        if self.o_drive > self._max:
            self.o_drive = self._max
        if self.p_drive > self._max:
            self.p_drive = self._max

        self._update_neopixel()

        print(f"Update drives: O={self.o_drive}, P={self.p_drive}")

        if self.is_unsatisfied:
            if not self.owner.search.is_started:
                print(f"The {self.owner.name} is unsatisfied {self.state}!")
                self.owner.search.start()
            return
        print(f"The {self.owner.name} is satisfied. => Not doing anything...")

    def decrease(self, drive):
        if "O" in drive:
            self.o_drive -= 10 * self._step_o
            print(f"Decreased O drive of {self.path.as_posix()=}.")
        if "P" in drive:
            self.p_drive -= 10 * self._step_p
            print(f"Decreased P drive of {self.path.as_posix()=}.")


    def satisfy(self):
        self.o_drive =  self._satisfied
        self.p_drive =  self._satisfied

    def _update_neopixel(self):
        state, brightness, color = self.value
        # color = self._light_colors[state]
        config = dict(
            brightness = brightness,
            **color,
            )
        self._neopixel.configure(**config)