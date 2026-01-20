from time import time
from threading import Lock
from colloquy.thread_element import ThreadElement
from colloquy.drives import Drives

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

class FemaleDrives(Drives):

    def __init__(self, owner):
        Drives.__init__(self, owner=owner, neopixel=None)

    @property
    def head_neopixel(self):
        return self.owner.head_neopixel

    @property
    def body_neopixel(self):
        return self.owner.body_neopixel

    @property
    def feet_neopixel(self):
        return self.owner.feet_neopixel


    def _setup(self, **kwargs):
        self.head_neopixel.configure(**self.white, brightness=0)
        self.head_neopixel.on()


        self.body_neopixel.o_neopixel.configure(**self.orange, brightness=0)
        self.body_neopixel.p_neopixel.configure(**self.puce, brightness=0)
        self.body_neopixel.on()


        self.feet_neopixel.configure(**self.black, brightness=254)
        self.feet_neopixel.on()

    def _update_neopixel(self):
        self.head_neopixel.brightness = self.dominant_value

        self.body_neopixel.o_neopixel.brightness = self.o_drive
        self.body_neopixel.p_neopixel.brightness = self.p_drive


        self.feet_neopixel.color = self.dominant_color

        # Clamp the brigtness to avoid blink to 254.
        # Look like when the RGB value are all 255, the white LED is turned on, and RGB LEDs turned off. If white value is 0 then everything is turn off.
        # if brightness > 254:
            # brightness = 254

        # up_ring_config = dict(
            # brightness = brightness,
            # **self.white,
            # )

        # self.owner.up_ring.configure(**up_ring_config)

        # config = dict(
            # brightness = brightness,
            # **color,
            # )
        # self._neopixel.configure(**config)