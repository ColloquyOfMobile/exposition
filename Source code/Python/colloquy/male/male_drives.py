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

class MaleDrives(Drives):

    def __init__(self, owner, neopixel):
        Drives.__init__(self, owner=owner, neopixel=neopixel)
        

    def _setup(self, **kwargs):
        self.owner.up_ring.on()
        self._neopixel.on()

    def _update_neopixel(self):
        state, brightness, color = self.value
        
        # Clamp the brigtness to avoid blink to 254.
        # Look like when the RGB value are all 255, the white LED is turned on, and RGB LEDs turned off. If white value is 0 then everything is turn off.
        if brightness > 254:
            brightness = 254
            
        up_ring_config = dict(
            brightness = brightness,
            **self.white,
            )
            
        self.owner.up_ring.configure(**up_ring_config)
        
        config = dict(
            brightness = brightness,
            **color,
            )
        self._neopixel.configure(**config)
    
    