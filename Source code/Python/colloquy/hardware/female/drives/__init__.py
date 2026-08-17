from time import time
from pathlib import Path
from threading import Lock
from colloquy.base import Base
from colloquy.hardware.drive import Drive, which_is_frustated
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

def build_map_to_compensate_brightness_to_human_eye():
    map_from_tj = (
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        16,
        16,
        16,
        16,
        16,
        16,
        16,
        16,
        20,
        20,
        20,
        20,
        20,
        20,
        20,
        20,
        24,
        24,
        24,
        24,
        24,
        24,
        24,
        28,
        28,
        28,
        28,
        28,
        28,
        32,
        32,
        32,
        32,
        32,
        32,
        36,
        36,
        36,
        36,
        36,
        40,
        40,
        40,
        40,
        40,
        40,
        44,
        44,
        44,
        44,
        44,
        48,
        48,
        48,
        48,
        52,
        52,
        52,
        52,
        52,
        56,
        56,
        56,
        56,
        60,
        60,
        60,
        60,
        64,
        64,
        64,
        64,
        68,
        68,
        68,
        68,
        72,
        72,
        72,
        72,
        76,
        76,
        76,
        76,
        80,
        80,
        80,
        80,
        84,
        84,
        84,
        88,
        88,
        88,
        88,
        92,
        92,
        92,
        96,
        96,
        96,
        100,
        100,
        100,
        104,
        104,
        104,
        104,
        108,
        108,
        108,
        112,
        112,
        112,
        116,
        116,
        116,
        120,
        120,
        120,
        124,
        124,
        124,
        128,
        128,
        128,
        132,
        132,
        136,
        136,
        136,
        140,
        140,
        140,
        144,
        144,
        148,
        148,
        148,
        152,
        152,
        152,
        156,
        156,
        160,
        160,
        160,
        164,
        164,
        168,
        168,
        168,
        172,
        172,
        176,
        176,
        176,
        180,
        180,
        184,
        184,
        184,
        188,
        188,
        192,
        192,
        196,
        196,
        200,
        200,
        200,
        204,
        204,
        208,
        208,
        212,
        212,
        216,
        216,
        216,
        220,
        220,
        224,
        224,
        228,
        228,
        232,
        232,
        236,
        236,
        240,
        240,
        244,
        244,
        248,
        248,
        252,
        252,
        255,
        255,
    )

    old_size = len(map_from_tj)
    old_max = max(map_from_tj)

    new_max = 100
    new_size = 101

    new_map = []

    for i in range(new_size):
        # position in original map
        old_index = int(i * (old_size - 1) / (new_size - 1))

        # rescale value from 0-255 to 0-100
        value = round(map_from_tj[old_index] * new_max / 255)

        new_map.append(value)

    return tuple(new_map)


class Drives(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)

        self._o_drive = Drive(owner=self, name="O")
        self._p_drive = Drive(owner=self, name="P")

        self[self.o_drive.name] = self.o_drive
        self[self.p_drive.name] = self.p_drive

        self._map_to_compensate_brightness_to_human_eye = (
            build_map_to_compensate_brightness_to_human_eye()
        )

    def __iter__(self):
        yield self._o_drive
        yield self._p_drive

    def which_is_frustated(self):
        """Which appetites she is short of - what decides whether a male
        she has just recognised is worth answering (see Search)."""
        return which_is_frustated(o_drive=self.o_drive, p_drive=self.p_drive)

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

    def loop(self):
        pass

    def setdown(self):
        female = self.owner
        female.neopixels.head.off()
        female.neopixels.body_o.off()
        female.neopixels.body_p.off()
        female.neopixels.feet.off()

    def setup(self):
        female = self.owner
        female.neopixels.head.on()
        female.neopixels.body_o.on()
        female.neopixels.body_p.on()
        female.neopixels.feet.on()
        for drive in self:
            drive.start(started_by=self)

    def update(self):
        female = self.owner

        o_value = self.o_drive.value
        p_value = self.p_drive.value

        female.neopixels.head.brightness.value = max(o_value, p_value)
        female.neopixels.body_o.brightness.value = (
            self.compensate_brightness_for_human_eye(o_value)
        )
        female.neopixels.body_p.brightness.value = (
            self.compensate_brightness_for_human_eye(p_value)
        )
        if o_value < p_value:
            female.neopixels.feet.color = self.orange
        else:
            female.neopixels.feet.color = self.puce

    def compensate_brightness_for_human_eye(self, value):
        return self._map_to_compensate_brightness_to_human_eye[value]

    @property
    def snapshot_children(self):
        children = {}
        children[self.o_drive.name] = self.o_drive
        children[self.p_drive.name] = self.p_drive
        return children
