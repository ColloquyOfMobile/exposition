from time import time
from threading import Lock
from colloquy.thread_element import ThreadElement

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

class Drives(ThreadElement):

    def __init__(self, owner, neopixel):
        name = f"{owner.name}_drives"
        ThreadElement.__init__(self, name=name, owner=owner)
        self._neopixel = neopixel
        self._o_drive = 0
        self._p_drive = 0
        self._update_interval = 2
        self._timestamp = time()

        self._step_o = 2
        self._step_p = 3

        self._max = 255
        self._min = 0

        self._satisfaction_lim = 10
        self._frustrated_lim = 235

        self._lock = Lock()

        self._orange = dict(red=255, green=165, blue=0, white=0)
        self._white = dict(red=0, green=0, blue=0, white=255)
        self._puce = dict(red=80, green=53, blue=60, white=125) #CC8899
        self._colors = {
            ("O",): self._orange,
            ("P",): self._puce,
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
    def puce(self):
        return self._puce

    @property
    def orange(self):
        return self._orange

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
            o_satisfaction_lim = self.o_drive < self._satisfaction_lim
            p_satisfaction_lim = self.p_drive < self._satisfaction_lim
            o_frustated = self.o_drive > self._frustrated_lim
            p_frustated = self.p_drive > self._frustrated_lim
            # print(f"{self.o_drive=}")
            # print(f"{self.p_drive=}")
            # print(f"{o_satisfaction_lim=}")
            # print(f"{p_satisfaction_lim=}")
            # print(f"{o_frustated=}")
            # print(f"{p_frustated=}")

            if o_satisfaction_lim and p_satisfaction_lim:
                return tuple()
            if o_frustated and p_frustated:
                return ("O", "P")
            if self.o_drive > self.p_drive:
                assert not o_satisfaction_lim
                return ("O", )
            if self.p_drive > self.o_drive:
                assert not p_satisfaction_lim
                return ("P", )
            if self.p_drive == self.o_drive:
                return ("O", "P")

            raise ValueError(f"Drive Error, {self.o_drive=}, {self.p_drive=}")

    @property
    def max(self):
        return self._max

    @property
    def o_drive(self):
        return self._o_drive

    @o_drive.setter
    def o_drive(self, value):
        assert isinstance(value, int)
        self._o_drive = value
        self._update_neopixel()

    @property
    def p_drive(self):
        return self._p_drive

    @p_drive.setter
    def p_drive(self, value):
        assert isinstance(value, int)
        self._p_drive = value
        self._update_neopixel()

    @property
    def is_unsatisfied(self):
        raise NotImplementedError(f"Use is_frustrated_lim instead!")
        return bool(self.state)

    @property
    def is_frustated(self):
        return bool(self.state)

    @property
    def satisfaction_lim(self):
        return self._satisfaction_lim

    def __enter__(self):
        """Setup before loop."""
        self.stop_event.clear()
        self._neopixel.on()

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

        if self.is_frustated:
            if not self.owner.search.is_started:
                print(f"The {self.owner.name} is unsatisfied {self.state}!")
                self.owner.search.start()
            return
        print(f"The {self.owner.name} is satisfied. => Not doing anything...")

    def decrease(self, drive):
        if "O" in drive:
            self.o_drive -= 20 * self._step_o
            print(f"Decreased O drive of {self.owner.name=}.")
        if "P" in drive:
            self.p_drive -= 20 * self._step_p
            print(f"Decreased P drive of {self.owner.name=}.")
        self._update_neopixel()

    def is_satisfied(self, drive):
        satisfied_drives = []
        for value in drive:
            if value == "O":
                is_satisfied = self.o_drive < self._satisfaction_lim
                satisfied_drives.append(is_satisfied)
                # print(f"Is {self.owner.name} O drive satisfied ? {is_satisfied}.")
            if "P" in drive:
                is_satisfied = self.p_drive < self._satisfaction_lim
                satisfied_drives.append(is_satisfied)
                # print(f"Is {self.owner.name} P drive satisfied ? {is_satisfied}.")
        if all(satisfied_drives):
            print(f"{self.owner.name} is satisfied.")

        return all(satisfied_drives)


    def satisfy(self):
        self.o_drive = self._satisfaction_lim
        self.p_drive = self._satisfaction_lim

    def _update_neopixel(self):
        state, brightness, color = self.value
        config = dict(
            brightness = brightness,
            **color,
            )
        self._neopixel.configure(**config)