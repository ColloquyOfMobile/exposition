from time import sleep, time
from .u2d2 import U2D2
from .arduino import Arduino
from colloquy.base_thread import BaseThread
from .female import Female
from .male import Male
from .bar import Bar
from pathlib import Path
from .neopixels import Neopixels
from .commands import Commands
from .test import Test
from .html import HTML
from .bodies import Bodies
from .all_neopixels import AllNeopixels


class Hardware(BaseThread):
    def __init__(self, owner):

        super().__init__(owner)

        if self.is_simulated:
            self.log("Warning: The hardware is simulated.")

        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request

        self.dxl_ids = {
            "female1": 1,
            "female2": 3,
            "female3": 5,
        }
        self._is_opened = False
        self._commands = Commands(owner=self)

        self._arduino = Arduino(owner=self)
        self._u2d2 = U2D2(owner=self)
        self[self.u2d2.name] = self.u2d2

        self._mirrors = []
        self._drives = []
        self._males = (
            Male(owner=self, id_number=1),
            Male(owner=self, id_number=2),
        )
        self._speakers = []
        self._moving_elements = []

        self._females = (
            Female(owner=self, id_number=1),
            Female(owner=self, id_number=2),
            Female(owner=self, id_number=3),
        )
        self._bodies = Bodies(owner=owner, males=self.males, females=self.females)
        self._neopixels = AllNeopixels(owner=self, bodies=self._bodies)

        self._bar = Bar(owner=self)

        self._test = Test(owner=self)

        self[self.arduino.name] = self.arduino
        self.add(self.test)

        self[self.bar.name] = self.bar

        for female in self._females:
            self[female.name] = female
            self.drives.extend(female.drives)

        for male in self.males:
            self[male.name] = male
            self.drives.extend(male.drives)

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    @property
    def params(self):
        return self.owner.params

    @property
    def test(self):
        return self._test

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def opened(self):
        return self._opened

    @property
    def bodies(self):
        return self._bodies

    @opened.setter
    def opened(self, value):
        # Value is None only in a Close(), this is to avoid recursion.
        if value is not None:
            if self._opened is not None:
                self._opened.close()

        self._opened = value

    @property
    def drives(self):
        return self._drives

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "hardware"

    @property
    def arduino(self):
        return self._arduino

    @property
    def u2d2(self):
        return self._u2d2

    @property
    def bar(self):
        return self._bar

    @property
    def mirrors(self):
        return self._mirrors

    @property
    def males(self):
        return self._males

    @property
    def male1(self):
        return self._males[0]

    @property
    def male2(self):
        return self._males[1]

    @property
    def speakers(self):
        return self._speakers

    @property
    def females(self):
        return self._females

    @property
    def female1(self):
        return self._females[0]

    @property
    def female2(self):
        return self._females[1]

    @property
    def female3(self):
        return self._females[2]

    @property
    def moving_elements(self):
        return self._moving_elements

    @property
    def neopixels(self):
        return self._neopixels

    def wait_until_everything_is_still(self, timeout=30):
        """Blocking. Bounded the same way DXL.wait_for_servo() bounds a
        single servo: a jammed/unresponsive body must not hang whatever
        called this (graceful shutdown) forever."""
        start = time()
        while any(dxl.is_moving for dxl in self._u2d2.dxl_list):
            if time() - start > timeout:
                self.log(f"wait_until_everything_is_still timed out after {timeout}s.")
                return
            sleep(0.05)

    def disable_torque(self):
        for dxl in self._u2d2.dxl_list:
            dxl.torque_enabled.write(value=0)

    def open(self):
        self._is_opened = True

    def close(self):
        self._is_opened = False

    def loop(self):
        pass

    def setup(self):
        for bodies in self.bodies:
            bodies.start(started_by=self)
        self.bar.start(started_by=self)

    def setdown(self):
        for bodies in self.bodies:
            bodies.stop()

    @property
    def snapshot_children(self):
        children = {}
        children["bodies"] = self.bodies
        for body in self.bodies:
            children[body.name] = body
        children[self.bar.name] = self.bar
        return children

    # def snapshot(self, path):
    # states = super().snapshot(path=path)
    # _path = states["path"]
    # states["bodies"] = self.bodies.snapshot(path=_path)
    # for body in self.bodies:
    # states[body.name] = body.snapshot(path=_path)
    # states[self.bar.name] = self.bar.snapshot(path=_path)
    # return states
