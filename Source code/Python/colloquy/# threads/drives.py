from time import time
from threading import Lock
from colloquy.thread_element import ThreadElement

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

        # self._max == 254 in order to clamp the brigtness to avoid blink to 254.
        # Look like when the RGB value are all 255, the white LED is turned on, and RGB LEDs turned off. If white value is 0 then everything is turn off.
        self._max = 254
        self._min = 0

        self._satisfaction_lim = 10
        self._frustrated_lim = 235

        self._lock = Lock()

        self._orange = dict(red=255, green=80, blue=25, white=16)
        self._white = dict(red=0, green=0, blue=0, white=255)
        self._puce = dict(red=160, green=180, blue=0, white=40) #CC8899
        self._black = dict(red=0, green=0, blue=0, white=0) #CC8899
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
    def black(self):
        return self._black

    @property
    def puce(self):
        return self._puce

    @property
    def orange(self):
        return self._orange

    @property
    def white(self):
        return self._white

    @property
    def color(self):
        return dict(red=self.red, green=self.green, blue=self.blue, white=self.white)

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
    def dominant_value(self):
        return max((self._o_drive, self._p_drive))

    @property
    def dominant(self):
        if self._o_drive > self._p_drive:
            return self._o_drive
        return self._p_drive

    @property
    def dominant_color(self):
        if self._o_drive > self._p_drive:
            return self.orange
        return self.puce

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

    def __exit__(self, exc_type, exc_value, traceback_obj):
        if self.owner.search.is_started:
            self.owner.search.stop()
        return ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)

    def _loop(self):
        if time() - self._timestamp < self._update_interval:
            return
        self._timestamp = time()
        self._update()

    def _setup(self, **kwargs):
        self._neopixel.on()

    def _update(self):
        self.o_drive += self._step_o
        self.p_drive += self._step_p
        if self.o_drive > self._max:
            self.o_drive = self._max
        if self.p_drive > self._max:
            self.p_drive = self._max

        self._update_neopixel()

        if self.is_frustated:
            if not self.owner.search.is_started:
                self.owner.search.start()
            return

    def decrease(self, drive):
        if "O" in drive:
            self.o_drive -= 20 * self._step_o
        if "P" in drive:
            self.p_drive -= 20 * self._step_p
        self._update_neopixel()

    def is_satisfied(self, drive):
        satisfied_drives = []
        for value in drive:
            if value == "O":
                is_satisfied = self.o_drive < self._satisfaction_lim
                satisfied_drives.append(is_satisfied)
            if "P" in drive:
                is_satisfied = self.p_drive < self._satisfaction_lim
                satisfied_drives.append(is_satisfied)


        return all(satisfied_drives)


    def satisfy(self):
        self.o_drive = self._satisfaction_lim
        self.p_drive = self._satisfaction_lim

    def _update_neopixel(self):
        state, brightness, color = self.value

        # Trying to reduce brigtness to avoid blink
        # Look like when the RGB value are all 255, the white LED is turned on, and RGB LEDs turned off. If white value is 0 then everything is turn off.
        if brightness > 254:
            brightness = 254

        config = dict(
            brightness = brightness,
            **color,
            )
        self._neopixel.configure(**config)

    def _set_p_drive(self, **kwargs):
        value = kwargs["value"][0]
        self._p_drive = int(value)

    def _set_o_drive(self, **kwargs):
        value = kwargs["value"][0]
        self._o_drive = int(value)
        # raise NotImplementedError(f"{kwargs=}, {self.post_data=}")


    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()

        with tag("h4"):
            text(f"Drives:")

        with tag("div", style="padding-bottom:1rem;"):
            text(f"Set the drive here")
            with tag("ol"):
                with tag("li"):
                    text(f"{self._satisfaction_lim=}")
                with tag("li"):
                    text(f"{self._frustrated_lim=}")

        # if self.hardware.is_open:
        self._add_html_o_drive()
        self._add_html_p_drive()

    def _add_html_o_drive(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("label"):
                text(f"O drive [{self._min}-{self._max}]: ")
            doc.stag("input", type="number", name="value", value=self.o_drive, min=self._min, max=self._max, increment=1)
            with tag("button", name="action", value=f"{self.path.as_posix()}/set_o"):
                text(f"Set.")
            self.hardware.actions[f"{self.path.as_posix()}/set_o"] = self._set_o_drive

    def _add_html_p_drive(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("label"):
                text(f"P drive [{self._min}-{self._max}]: ")
            doc.stag("input", type="number", name="value", value=self.p_drive, min=self._min, max=self._max, increment=1)
            with tag("button", name="action", value=f"{self.path.as_posix()}/set_p"):
                text(f"Set.")
            self.hardware.actions[f"{self.path.as_posix()}/set_p"] = self._set_p_drive