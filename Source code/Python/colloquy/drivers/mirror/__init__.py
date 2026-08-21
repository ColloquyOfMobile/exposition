# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/mirror/__init__.py

from colloquy.base import Base

from ..angle import Angle
from ..angle.conversion import REDUCTIONS
from ..dxl_origin import DXLOrigin


class Mirror(Base):
    """A female's mirror: the servo she uses to send a male's own light
    back to him.

    Nothing drives it yet. In TJ's firmware the mirror wiggles for the
    whole of a reinforcement exchange (`act_reflect_VERTICAL_wiggle()`,
    act_mirror.ino) and what it returns is what the male measures to
    decide whether the exchange is working - see CODE_DOCUMENTATION
    section 9. This node exists so the servo can be found, calibrated and
    jogged by hand in the meantime, in the same degrees as everything
    else.

    Deliberately a plain node and not a thread, and deliberately not
    touched by `Female.setup()`: the three mirror servos (ids 2, 4 and 6,
    the gaps between the females and the males) may not be wired yet, and
    nothing should try to enable torque on them until somebody asks. "init
    hardware" on the dxl node is that asking.

    They turn one for one with their servo - the one axis in the
    installation that does, every body being geared 1:3.
    """

    def __init__(self, owner, id_number):
        self._name = f"mirror{id_number}"
        super().__init__(owner=owner)
        self._id_number = id_number

        self._dxl = owner.owner.u2d2.dxls[self._name]
        self._dxl_origin = DXLOrigin(owner=self)
        self._angle = Angle(owner=self, reduction=REDUCTIONS["mirror"])

        self[self.dxl_origin.name] = self.dxl_origin
        self[self.angle.name] = self.angle
        self["set current position as dxl origin"] = (
            self.set_current_position_as_dxl_origin
        )

    @property
    def name(self):
        return self._name

    @property
    def id_number(self):
        return self._id_number

    @property
    def female(self):
        return self.owner

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def params(self):
        return self.owner.params

    @property
    def dxl(self):
        return self._dxl

    @property
    def dxl_origin(self):
        return self._dxl_origin

    @property
    def angle(self):
        """How far it has turned from its origin, in degrees."""
        return self._angle

    @property
    def is_moving(self):
        return self.dxl.is_moving

    @property
    def sweep(self):
        """How far it can turn, end to end, in degrees.

        Zero until somebody measures it: nothing drives a mirror yet, and
        nobody has established how far one turns before it fouls. Zero
        means the two ends below are both the origin, so a stray click
        cannot drive an unmeasured mirror into something."""
        return self.params[self.name]["motion range"]

    def turn_to(self, degrees):
        self.angle.turn_to(degrees)

    def turn_to_origin(self):
        self.angle.turn_to_origin()

    def turn_to_max_position(self):
        self.angle.turn_to(self.sweep / 2)

    def turn_to_min_position(self):
        self.angle.turn_to(-self.sweep / 2)

    def set_current_position_as_dxl_origin(self, request=None):
        self.dxl_origin.set(self.dxl.position.read())

    @property
    def snapshot_children(self):
        return {
            "angle": self.angle,
            "dxl origin": self.dxl_origin,
            self.dxl.name: self.dxl,
        }

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["set current position as dxl origin"] = (
            self.set_current_position_as_dxl_origin
        )
        states["turn to origin"] = self.turn_to_origin
        states["turn to one end"] = self.turn_to_max_position
        states["turn to the other end"] = self.turn_to_min_position
        return states
