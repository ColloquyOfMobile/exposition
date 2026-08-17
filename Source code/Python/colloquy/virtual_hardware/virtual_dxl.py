from colloquy.base import Base
from threading import Lock, Thread
from time import sleep


class VirtualDXL(Base):
    """One simulated dynamixel: a register bank plus a mover thread.

    Movement follows the servo's own `profile velocity` register rather
    than a fixed rate, so a simulated sweep takes about as long as the
    real one and changing the profile changes it here too. Every body used
    to travel at the same 400 units/s whatever it was configured for,
    which made simulated timing worthless for anything the rest of this
    codebase cares about - how long a body faces another, how long a
    female has to read a pattern.
    """

    # One simulated step every _TICK seconds.
    _TICK = 0.025

    # X-series numbers: one unit of profile velocity is 0.229 rev/min, and
    # a revolution is 4096 position units - so velocity 20, which
    # DXL.init_hardware() writes, is about 313 units/s. A body's 2000-unit
    # sweep therefore takes ~6.4s and the bar's 10000-unit crossing ~32s.
    _UNITS_PER_SECOND_PER_VELOCITY = 0.229 * 4096 / 60

    # Profile velocity 0 means "as fast as the servo will go", not "don't
    # move". Roughly the no-load speed of an XM430.
    _MAX_UNITS_PER_SECOND = 3000

    def __init__(self, owner, dxl_id):
        self._name = f"virtual_dxl_{dxl_id}"
        super().__init__(owner=owner)
        self._dict = {
            "drive mode": None,
            "temperature": 25,
            "position": 0,
            "goal position": 0,
            "operating mode": 0,
            "profile velocity": 0,
            "profile acceleration": 0,
            "torque enabled": 0,
        }
        self._dxl_id = dxl_id
        self._thread = None
        self._lock = Lock()

    @property
    def name(self):
        return self._name

    @property
    def position(self):
        return self["position"]

    @property
    def speed(self):
        """Units per second at the currently configured profile velocity."""
        velocity = self._dict["profile velocity"]
        if not velocity:
            return self._MAX_UNITS_PER_SECOND
        return min(
            velocity * self._UNITS_PER_SECOND_PER_VELOCITY,
            self._MAX_UNITS_PER_SECOND,
        )

    def get(self, label):
        return self._dict[label]

    def set(self, label, value):
        self._dict[label] = value

        # A write only ever starts motion; whether motion is possible is
        # decided in one place, below. Writing a goal position with torque
        # off used to raise NotImplementedError from inside the serial
        # stand-in, killing whichever thread happened to be writing - a
        # real servo simply holds the value and moves once torque is on,
        # which is what happens now (DXL.init_hardware() writes registers
        # in exactly that order).
        if label in ("goal position", "torque enabled"):
            self._start_moving()

    def _start_moving(self):
        if not self._dict["torque enabled"]:
            return
        if self._dict["position"] == self._dict["goal position"]:
            return
        if self._thread is not None and self._thread.is_alive():
            return

        self._thread = thread = Thread(
            target=self.run, name=self.path.as_posix(), daemon=True
        )
        thread.start()

    def run(self):
        """Step toward the goal until it is reached exactly.

        Landing exactly on the goal rather than "within two steps" matters
        because DXL.is_moving() compares against its own threshold of 20
        units: a fast profile makes a step bigger than that, so a servo
        that stopped short would have been reported as moving forever.
        """
        while True:
            position = self._dict["position"]
            goal = self._dict["goal position"]

            if position == goal or not self._dict["torque enabled"]:
                return

            step = max(1, round(self.speed * self._TICK))
            remaining = goal - position
            if abs(remaining) <= step:
                self._dict["position"] = goal
            elif remaining > 0:
                self._dict["position"] = position + step
            else:
                self._dict["position"] = position - step

            sleep(self._TICK)
