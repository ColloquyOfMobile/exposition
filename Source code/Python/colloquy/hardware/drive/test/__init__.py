from time import time, sleep
from threading import Lock
from colloquy.base_thread import BaseThread
from threading import Thread, Event
from .html import HTML

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


class Test(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)

        self[self.html.name] = self.html.handle_request

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "test"

    # @property
    # def body(self):
    # return self.owner.body

    # @property
    # def black(self):
    # return self.owner.black

    # @property
    # def color(self):
    # return self.owner.color

    # @property
    # def value(self):
    # return self.owner.value

    # @property
    # def is_satisfied(self):
    # return self.owner.is_satisfied

    # @property
    # def is_frustated(self):
    # return self.owner.is_frustated

    # def decrease(self):
    # return self.owner.decrease()

    # def increment(self):
    # return self.owner.increment()

    def loop(self):
        self.owner.increment()
        sleep(self._update_interval)

    def setup(self):
        pass

    def setdown(self):
        pass

    def _break_condition(self):
        if self.error is not None:
            self.log(f"Break condition: {self.error=}.")
            return True
        if self._stop_event.is_set():
            self.log(f"Break condition: {self._stop_event.is_set()=}.")
            return True
        if self._shutdown.is_set():
            self.log(f"Break condition: {self._shutdown.is_set()=}.")
            return True
        # if not self.owner.is_started:
        # self.log(f"Break condition: {not self.owner.is_started=}.")
        # return True

    # def satisfy(self):
    # self.o_drive = self._satisfaction_lim
    # self.p_drive = self._satisfaction_lim

    # def _run_unsafe(self):
    # stop_event = self._stop_event.is_set
    # while not stop_event():
    # self.increment()
    # sleep(self._update_interval)
