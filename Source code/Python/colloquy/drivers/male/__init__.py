from .neopixels import Neopixels  # Head, BodyO, BodyP, Feet
from .drives import Drives
from colloquy.base_thread import BaseThread

from .light_sensor import LightSensor
from ..angle import Angle
from ..angle.conversion import REDUCTIONS
from ..dxl_origin import DXLOrigin
from .search import Search
from ..turn_back_and_forth import TurnBackAndForth


class Male(BaseThread):
    # One male from switch-on. Both males read the same one; they differ
    # only in their blinking pattern and in the second they start.
    scenario_names = ("male-body",)

    def __init__(self, owner, id_number):
        self._name = f"male{id_number}"
        self._id_number = id_number
        super().__init__(owner=owner)
        self._position_memory = None
        # Plain tuples, not the circular deques this used to hold: Blink
        # now sends each pattern once from its first bit and then goes
        # dark (light_pattern_timing.py), so nothing rotates them any
        # more, and a sequence that starts wherever the last burst left
        # off is exactly what the gap exists to prevent.
        self._light_patterns = {
            state: tuple(bits)
            for state, bits in self.colloquy.light_patterns[self.name].items()
        }

        self._dxl_origin = DXLOrigin(owner=self)
        self._angle = Angle(owner=self, reduction=REDUCTIONS["male"])

        self._light_sensors = {
            letter: LightSensor(owner=self, letter=letter) for letter in "abcd"
        }
        self._dxl = owner.u2d2.dxls[self.name]
        self._arduino = owner.arduino

        self._drives = Drives(owner=self)
        self._search = Search(owner=self)
        self.turn_back_and_forth = TurnBackAndForth(owner=self)

        self._neopixels = Neopixels(owner=self)

        self[self.neopixels.name] = self.neopixels
        self[self.drives.name] = self.drives
        self[self.search.name] = self.search
        self[self.dxl_origin.name] = self.dxl_origin
        self[self.angle.name] = self.angle
        self["set current position as dxl origin"] = (
            self.set_current_position_as_dxl_origin
        )
        for light_sensor in self._light_sensors.values():
            self[light_sensor.name] = light_sensor

    @property
    def params(self):
        return self.owner.params

    @property
    def dxl_origin(self):
        return self._dxl_origin

    @property
    def dxl(self):
        return self._dxl

    @property
    def ring(self):
        return self.neopixels.ring

    @property
    def search(self):
        return self._search

    @property
    def drives(self):
        return self._drives

    @property
    def id_number(self):
        return self._id_number

    @property
    def female(self):
        return self

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return self._name

    @property
    def neopixels(self):
        return self._neopixels

    @property
    def light_sensors(self):
        return self._light_sensors

    @property
    def is_moving(self):
        return self.dxl.is_moving

    @property
    def angle(self):
        """Where he is pointing, in degrees from his origin."""
        return self._angle

    @property
    def sweep(self):
        """How far he swings, end to end, in degrees.

        Read from params on every use, so a range edited on the page takes
        effect on his next sway. His 58.594 degrees is the 2000 servo
        units he was given before this layer existed, through his 1:3
        reduction - the same sway a female makes, which is what the rig
        says and what this file said the other way round for a while."""
        return self.params[self.name]["motion range"]

    @property
    def goal_position(self):
        return self.dxl.goal_position

    @property
    def torque_enabled(self):
        return self.dxl.torque_enabled

    def get_blink_pattern(self):
        # print(f"{self.drives.which_is_frustated()=}")
        return self._light_patterns[self.drives.which_is_frustated()]

    def set_current_position_as_dxl_origin(self, request=None):
        self.dxl_origin.set(self.dxl.position.read())

    def is_satisfied(self):
        """Is he inert - wanting nothing, and so not searching?

        Both appetites, not either. This is TJ's `internal_drive_state ==
        1 [Neither/Inert]`, which `updateInternalDriveState()`
        (internal.ino) reaches only when *both* drives are below the
        interested floor: `(internal_drive_LL > internal_drive_O) &&
        (internal_drive_LL > internal_drive_P)`.

        It said `or` until 2026-08-25, which made a body with one
        appetite full and one empty count as satisfied - so it would not
        search, while `which_is_frustated()` (the same five rules as TJ's,
        one place over) said it wanted the full one and a male in that
        state would blink asking for it. A body advertising a want it had
        decided not to act on.

        Expressed through `which_is_frustated()` rather than spelled out
        again, so the two cannot drift apart a second time: an empty
        tuple *is* the inert state.
        """
        return not self.drives.which_is_frustated()

    def turn_to_origin(self):
        self.angle.turn_to_origin()

    def turn_to(self, degrees):
        self.angle.turn_to(degrees)

    def turn_to_max_position(self):
        self.angle.turn_to(self.sweep / 2)
        self._position_memory = "max"

    def turn_to_min_position(self):
        self.angle.turn_to(-self.sweep / 2)
        self._position_memory = "min"

    def toggle_position(self):
        if self._position_memory is None:
            self.turn_to_max_position()
            return

        if self._position_memory == "max":
            self.turn_to_min_position()
            return

        if self._position_memory == "min":
            self.turn_to_max_position()
            return

    def loop(self):
        """Search while he wants something, and stop when he stops.

        The stop half was missing: he started calling the first time an
        appetite climbed and then called for the rest of the run, whatever
        his drives did afterwards (CODE_DOCUMENTATION 1.2). TJ's
        `Logic_male.ino` transmits only while `internal_drive_state` is
        not the inert one, and goes quiet the moment it is - so does this
        now, and the bar watches these flags to decide whether to keep
        wandering (`Bar.loop()`).
        """
        if self.is_satisfied():
            if self.search.is_started:
                self.log(f"{self.name} wants nothing now - stopping his search.")
                self.search.stop()
            return

        if not self.search.is_started:
            self.search.start(started_by=self)

    def setup(self):
        self.dxl.init_hardware()
        self.drives.start(started_by=self)

    def setdown(self):
        self.drives.stop()
        self.search.stop()

    @property
    def snapshot_children(self):
        children = {}
        children["angle"] = self.angle
        children["dxl origin"] = self.dxl_origin
        children[self.dxl.name] = self.dxl
        children["search"] = self.search
        children["drives"] = self.drives
        children["neopixels"] = self.neopixels
        for light_sensor in self._light_sensors.values():
            children[light_sensor.name] = light_sensor
        return self._with_scenarios(children)

