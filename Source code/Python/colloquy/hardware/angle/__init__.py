# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/angle/__init__.py

from colloquy.base import Base
from colloquy.hardware.value_setter2 import ValueSetter2

from .conversion import degrees_to_ticks, ticks_to_degrees
from colloquy.ui import leaves


class Angle(Base):
    """Where a body is pointing, in degrees of the body itself.

    Zero is the body's own origin - the position `dxl origin` records as
    "facing forward" - and the sign says which way it turned from there.
    So a female swaying reads -29 to +29, a male the same, and the bar
    runs from 0 up to +293 as it carries the males along.

    Two things are hidden here so that nobody outside has to hold them in
    their head: the servo's units, and the reduction between the servo and
    the body (see conversion.py - a female, a male and the bar all turn
    three times slower than their servo; a mirror turns with its own).
    Which is which is exactly what a call site should not have to know: it
    was got wrong for the male here for a while, and every angle he
    reported was three times the angle he had turned.

    The raw registers stay reachable under the body's own `dxl` node, for
    when what is wrong is the servo rather than the aim.
    """

    # What the jog buttons on the page step by. Coarse then fine, which is
    # the order calibration actually goes in.
    JOGS = (-10, -1, 1, 10)

    def __init__(self, owner, reduction):
        super().__init__(owner=owner)
        self._reduction = reduction
        self._setter = ValueSetter2(
            owner=self,
            # Wide enough for the bar's whole travel either way; a body
            # cannot be commanded past a turn, which no body has.
            min_value=-360,
            max_value=361,
            set_func=self.turn_to,
            get_func=self.rounded,
        )

        self["get"] = self.get
        self["turn to origin"] = self.turn_to_origin

    @property
    def name(self):
        return "angle"

    @property
    def body(self):
        return self.owner

    @property
    def dxl(self):
        return self.owner.dxl

    @property
    def reduction(self):
        return self._reduction

    @property
    def origin(self):
        """The servo reading this body calls zero degrees."""
        return self.owner.dxl_origin.get()

    def get(self, request=None):
        """Where the body is now, in degrees from its origin."""
        return self._to_degrees(self.dxl.position.read())

    def rounded(self, request=None):
        """The same, as a whole degree - what the page's setter works in."""
        return round(self.get())

    @property
    def goal(self):
        """Where it has been told to go, in the same terms."""
        return self._to_degrees(self.dxl.goal_position.read())

    @property
    def is_moving(self):
        return self.dxl.is_moving

    def turn_to(self, degrees):
        """Send the body to an angle. Non-blocking, like every other write
        in this codebase: the goal is written and the servo gets there in
        its own time."""
        self.dxl.goal_position.write(self.to_ticks(degrees))

    def turn_to_origin(self, request=None):
        self.turn_to(0)

    def jog(self, degrees):
        """Step by an angle, measured from where the body is *going* rather
        than where it is: pressing +1 twice while it is still moving should
        add up to two degrees, not to one and a bit."""
        self.turn_to(self.goal + degrees)

    def wait(self, timeout=None):
        self.dxl.wait_for_servo(timeout=timeout)

    def to_ticks(self, degrees):
        """The servo position for an angle of this body."""
        return self.origin + degrees_to_ticks(degrees, self._reduction)

    def to_degrees(self, ticks):
        """The angle of this body for a servo position."""
        return self._to_degrees(ticks)

    def _to_degrees(self, ticks):
        return ticks_to_degrees(ticks - self.origin, self._reduction)

    def commit(self, value):
        self.turn_to(float(value))

    def _make_jog(self, degrees):
        def command(request=None):
            self.jog(degrees)

        return command

    @property
    def snapshot_children(self):
        return {self._setter.name: self._setter}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["turn to origin"] = self.turn_to_origin
        for degrees in self.JOGS:
            states[f"turn {degrees:+d}"] = self._make_jog(degrees)

        leaf = leaves.into(states, path)

        leaf("angle", f"{self.get():.1f}\N{DEGREE SIGN}")
        leaf("goal", f"{self.goal:.1f}\N{DEGREE SIGN}")
        # The two numbers this node exists to keep out of everyone's way,
        # kept visible for calibration: what the servo actually reads, and
        # what it reads when this body is at zero.
        leaf("servo position", self.dxl.position.read())
        leaf("servo origin", self.origin)
        return states
