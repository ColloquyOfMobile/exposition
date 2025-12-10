from time import time, sleep
from threading import Lock
from colloquy.base import Base
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

class Drive(Base):

    def __init__(self, owner, name):
        assert name in ("O", "P")
        self._name = name
        Base.__init__(self, owner=owner)
        self._value = 0
        self._update_interval = 2
        self._thread = None
        self._stop_event = Event()

        self._step = 2
        
        # self._max == 254 in order to clamp the brigtness to avoid blink to 254.
        # Look like when the RGB value are all 255, the white LED is turned on, and RGB LEDs turned off. If white value is 0 then everything is turn off.
        self._max = 254
        self._min = 0

        self._satisfaction_lim = 10
        self._frustrated_lim = 235

        self._lock = Lock()

    @property
    def is_started(self):
        if self._thread is None:
            return False
        return self._thread.is_alive()
    
    @property
    def name(self):
        return self._name

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

        if self.is_frustated:
            self.owner.search.start()
            return

    def satisfy(self):
        self.o_drive = self._satisfaction_lim
        self.p_drive = self._satisfaction_lim
    
    def shutdown(self):
        print(f"Shutdown {self=}")
        self.stop()

    def start(self, request=None):
        self._stop_event.clear()
        self._thread = thread = Thread(target=self.run, name=self.path.as_posix())
        thread.start()

    def stop(self, request=None):
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join()
    
    def run(self):
        try:
            self._run_unsafe()
        except Exception as error:
            self._error = error
            raise 
    
    def _run_unsafe(self):
        stop_event = self._stop_event.is_set        
        while not stop_event():
            self.increment()
            sleep(0.1)
