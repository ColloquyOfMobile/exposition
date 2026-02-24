from .u2d2 import U2D2
from .arduino import Arduino
from colloquy.base_thread import BaseThread
from .female import Female
from pathlib import Path
from .neopixels import Neopixels
from .commands import Commands
from .test import Test
from .html import HTML


class Hardware(BaseThread):

    def __init__(self, owner):

        super().__init__(owner)

        if self.is_simulated:
            self.log(f"Warning: The hardware is simulated.")
        
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        self.dxl_ids = {
            "female1": 1,
            "female2": 3,
            "female3": 5,
        }
        self._opened = None
        self._commands = Commands(owner=self)

        self._arduino = Arduino(owner=self)
        self._u2d2 = U2D2(owner=self)
        self[self.u2d2.name] = self.u2d2
        self._bar = None

        self._mirrors = []
        self._drives = []
        self._males = []
        self._speakers = []
        self._moving_elements = []

        self._female1 = Female(owner=self, id_number=1)
        self._female2 = Female(owner=self, id_number=2)
        self._female3 = Female(owner=self, id_number=3)
        self._females = [
            self._female1,
            self._female2,
            self._female3,
            ]

        self._test = Test(owner=self)
        
        self[self.arduino.name] = self.arduino
        self.add(self.test)

        for female in self._females:
            self[female.name] = female
            self.drives.extend(female.drives)
        


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
    def test(self):
        return self._test

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def opened(self):
        return self._opened

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
    def speakers(self):
        return self._speakers

    @property
    def females(self):
        return self._females

    @property
    def female1(self):
        return self._female1

    @property
    def female2(self):
        return self._female2

    @property
    def female3(self):
        return self._female3

    @property
    def moving_elements(self):
        return self._moving_elements

    @property
    def neopixels(self):
        neopixels = []
        for body in self.bodies:
            neopixels.extend(body.neopixels)
        return neopixels

    @property
    def bodies(self):
        bodies = []
        for body in self.females:
            bodies.append(body)
        for body in self.males:
            bodies.append(body)
        return bodies

    def loop(self):
        pass

    def setup(self):
        for bodies in self.hardware.bodies:
            bodies.start(started_by=self)

    def setdown(self):
        for bodies in self.hardware.bodies:
            bodies.stop()