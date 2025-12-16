from time import time, sleep
from threading import Lock
from colloquy.base_thread import BaseThread
from threading import Thread, Event, Lock

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

class Drive(BaseThread):

    def __init__(self, owner, name):
        assert name in ("O", "P")
        self._name = name
        super().__init__(owner=owner)
        self._value = 0

        self._step = 1
        self._body = owner.owner
        
        self._max = 100
        self._min = 0
        
        seconds_in_4min = 60*4
        self._update_interval = seconds_in_4min/self._max        
        
        self._satisfaction_lim = 30 / self._update_interval
        
        seconds_in_3min = 60*3
        self._frustrated_lim = seconds_in_3min / self._update_interval

    # @property
    # def is_started(self):
        # if self._thread is None:
            # return False
        # return self._thread.is_alive()

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self._body

    @property
    def black(self):
        return dict(red=0, green=0, blue=0, white=0)

    @property
    def color(self):
        return dict(red=self.red, green=self.green, blue=self.blue, white=self.white)

    @property
    def value(self):
        return self._value

    @property
    def is_satisfied(self):
        with self._lock:
            return self.value < self._satisfaction_lim
    @property
    def is_frustated(self):
        with self._lock:
            return self.value > self._frustrated_lim

    def decrease(self):
        self._value -= 20 * self._step
        if self._value < 0:
            self._value = 0
        self.owner.update()

    def increment(self):
        self._value += self._step
        if self._value > self._max:
            self._value = self._max

        self.owner.update()

        if not self.is_satisfied:
            self.body.search.start(started_by=self)
            return

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

    # def _run_unsafe(self):
        # stop_event = self._stop_event.is_set
        # while not stop_event():
            # self.increment()
            # sleep(self._update_interval)