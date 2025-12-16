from time import time
from threading import Lock
from colloquy.base import Base
from colloquy.hardware.drive import Drive

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

class Drives(Base):

    def __init__(self, owner):
        Base.__init__(self, owner=owner)
        self._o_drive = Drive(owner=self, name="O")
        self._p_drive = Drive(owner=self, name="P")
        self._started_by = None
        self._error = None

    def __iter__(self):
        yield self._o_drive
        yield self._p_drive

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, value):
        print(value)
        self._error = value
        if self._started_by is not None:
            self._started_by.error = value

    @property
    def o_drive(self):
        return self._o_drive

    @property
    def p_drive(self):
        return self._p_drive

    @property
    def name(self):
        return "drives"

    @property
    def puce(self):
        return dict(red=160, green=180, blue=0, white=40)

    @property
    def orange(self):
        return dict(red=255, green=80, blue=25, white=16)

    @property
    def white(self):
        return dict(red=0, green=0, blue=0, white=255)

    @property
    def is_started(self):
        return self.owner.is_started

    def stop(self):
        female = self.owner
        for drive in self:
            drive.start(started_by=self)
        female.head.off()
        female.body_o.off()
        female.body_p.off()
        female.feet.off()

    def start(self, started_by):
        self._started_by = started_by
        female = self.owner
        female.head.on()
        female.body_o.on()
        female.body_p.on()
        female.feet.on()
        for drive in self:
            drive.start(started_by=self)

    def update(self):
        female = self.owner

        o_value = self.o_drive.value
        p_value = self.p_drive.value

        female.head.brightness.value = max(o_value, p_value)
        female.body_o.brightness.value = o_value
        female.body_p.brightness.value = p_value
        if o_value < p_value:
            female.feet.color = self.orange
        else:
            female.feet.color = self.puce