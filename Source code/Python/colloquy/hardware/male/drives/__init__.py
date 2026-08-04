from time import time
from pathlib import Path
from threading import Lock
from colloquy.base import Base
from colloquy.hardware.drive import Drive
from colloquy.base_thread import BaseThread

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


class Drives(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._name = f"{owner.name}'s drives"

        self._o_drive = Drive(owner=self, name="O")
        self._p_drive = Drive(owner=self, name="P")
        # self._started_by = None
        # self._errors = []

        self[self.o_drive.name] = self.o_drive
        self[self.p_drive.name] = self.p_drive

        self._lock = Lock()

    def __iter__(self):
        yield self._o_drive
        yield self._p_drive

    def which_is_frustated(self):
        # raise NotImplementedError(f"Update to return a tuple for the states")

        with self.o_drive.lock, self.p_drive.lock:
            # o_satisfaction_lim = self.o_drive < self._satisfaction_lim
            # p_satisfaction_lim = self.p_drive < self._satisfaction_lim
            # o_frustated = self.o_drive > self._frustrated_lim
            # p_frustated = self.p_drive > self._frustrated_lim

            if self.o_drive.is_satisfied and self.p_drive.is_satisfied:
                return tuple()
            if self.o_drive.is_frustated and self.p_drive.is_frustated:
                return ("O", "P")
            if self.o_drive.value > self.p_drive.value:
                return ("O",)
            if self.p_drive.value > self.o_drive.value:
                return ("P",)
            if self.p_drive.value == self.o_drive.value:
                return ("O", "P")

            raise ValueError(f"Drive Error, {self.o_drive=}, {self.p_drive=}")

    @property
    def o_drive(self):
        return self._o_drive

    @property
    def p_drive(self):
        return self._p_drive

    @property
    def name(self):
        return self._name

    @property
    def puce(self):
        return dict(red=160, green=180, blue=0, white=40)

    @property
    def orange(self):
        return dict(red=255, green=80, blue=25, white=16)

    @property
    def white(self):
        return dict(red=0, green=0, blue=0, white=255)

    # @property
    # def is_started(self):
    # return self.owner.is_started

    def loop(self):
        pass

    def setdown(self):
        male = self.owner
        male.neopixels.o_drive_level.off()
        male.neopixels.p_drive_level.off()
        male.neopixels.up_ring.off()

    def setup(self):
        male = self.owner
        male.neopixels.o_drive_level.on()
        male.neopixels.p_drive_level.on()
        male.neopixels.up_ring.on()
        for drive in self:
            drive.start(started_by=self)

    def update(self):
        male = self.owner

        o_value = self.o_drive.value
        p_value = self.p_drive.value

        male.neopixels.up_ring.brightness.value = max(o_value, p_value)
        male.neopixels.o_drive_level.brightness.value = o_value
        male.neopixels.p_drive_level.brightness.value = p_value

    def set_o_to_0_p_to_100(self):
        self._o_drive.value = 0
        self._p_drive.value = 100
        self.update()

    def set_p_to_0_o_to_100(self):
        self._o_drive.value = 100
        self._p_drive.value = 0
        self.update()

    def set_o_and_p_to_30(self):
        self._o_drive.value = 30
        self._p_drive.value = 30
        self.update()

    def set_o_and_p_to_100(self):
        self._o_drive.value = 100
        self._p_drive.value = 100
        self.update()

    @property
    def snapshot_children(self):
        children = {}
        children["set O=0 and P=100"] = self.set_o_to_0_p_to_100
        children["set O=100 and P=0"] = self.set_p_to_0_o_to_100
        children["set O=30 and P=30"] = self.set_o_and_p_to_30
        children["set O=100 and P=100"] = self.set_o_and_p_to_100
        children[self.o_drive.name] = self.o_drive
        children[self.p_drive.name] = self.p_drive
        return children
