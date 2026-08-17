from pathlib import Path
import urllib
import os
import sys

#
from colloquy.base_thread import BaseThread
from .events import Events
from .base import Base
from .tests import Tests

from .hardware import Hardware
from .exposition import Exposition
from .params import Params
from .params_browser import ParamsNode
from .virtual_hardware import VirtualHardware
from .logs import Logs


class Colloquy(BaseThread):
    def __init__(self):
        super().__init__(owner=None)

        self._params = Params.load(Path("local/params.json"))
        self._params_view = ParamsNode(owner=self, key="params", params_dict=self._params)

        self._is_opened = False
        self._request = None
        self._args = None
        self._virtual_hardware = None

        self._hardware = Hardware(owner=self)
        self._tests = Tests(owner=self)
        self._exposition = Exposition(owner=self)
        self._logs = Logs(owner=self)

        self["hardware"] = self._hardware
        self["params"] = self._params_view
        self["logs"] = self._logs

        self._events = Events(shutdown=BaseThread._shutdown)

    @property
    def light_patterns(self):
        # During search the male blinks.
        # The blink pattern define 2 things:
        # - the male identity: 1 or 2
        # - which kind of interation the male is look for (drive state): "O" or "P" or both
        # Extracted from TJ's arduino code "logic35_system.ino, line 87."
        #
        # The `tuple()` entry is TJ's com_pattern_I_R / com_pattern_II_R - "R"
        # for reinforcement, a separate message, not "no drive". His firmware
        # neither transmits nor decodes it (in the inert state a male sends no
        # light at all, MALE_setSearchLight()); it is kept here only because
        # which_is_frustated() can still return an empty tuple if both drives
        # are satisfied while a male is blinking. Females must not compare
        # against it - see readable_light_patterns.
        return {
            "male1": {
                tuple(): (1, 1, 0, 0, 1, 1, 0, 0, 0, 1),
                ("O",): (1, 1, 0, 0, 0, 0, 0, 1, 1, 1),
                ("P",): (1, 1, 0, 0, 0, 0, 1, 1, 1, 0),
                ("O", "P"): (1, 1, 0, 0, 0, 1, 0, 1, 0, 1),
            },
            "male2": {
                tuple(): (1, 1, 0, 0, 1, 1, 1, 0, 0, 0),
                ("O",): (1, 1, 0, 0, 0, 1, 1, 1, 0, 0),
                ("P",): (1, 1, 0, 0, 1, 0, 0, 0, 1, 1),
                ("O", "P"): (1, 1, 0, 0, 1, 0, 1, 0, 1, 0),
            },
        }

    @property
    def readable_light_patterns(self):
        """The patterns a female compares her sensor against: the six a male
        can actually send (each male x O, P, both).

        Deliberately narrower than light_patterns, and matching TJ's own
        receiver, which only ever tests those six (sense_light_pattern.ino).
        Including the two "R" entries breaks identity decoding outright:
        male1's R sequence is male2's O sequence rotated, and since the
        matcher tries every rotation the two cannot be told apart - male2
        asking for O then always decodes as male1, whatever the sensor saw.
        """
        return {
            male: {
                drive: pattern for drive, pattern in patterns.items() if drive
            }
            for male, patterns in self.light_patterns.items()
        }

    @property
    def tests(self):
        return self._tests

    @property
    def colloquy(self):
        return self

    @property
    def name(self):
        return "colloquy"

    @property
    def hardware(self):
        return self._hardware

    @property
    def events(self):
        return self._events

    @property
    def params(self):
        return self._params

    @property
    def exposition(self):
        return self._exposition

    @property
    def logs(self):
        return self._logs

    @property
    def is_started(self):
        return not self.events.shutdown.is_set()

    @property
    def virtual_hardware(self):
        if self._virtual_hardware is None:
            self._virtual_hardware = VirtualHardware(owner=self)
        return self._virtual_hardware

    def open(self):
        self._is_opened = True

    def close(self):
        raise NotImplementedError
        self._is_opened = False

    def run(
        self,
    ):
        return self.server()

    def _call_root(self):
        print("Available command:")
        for name in self:
            print(f"- {name}")

    @property
    def snapshot_children(self):
        children = {
            "hardware": self._hardware,
            "exposition": self._exposition,
            "tests": self._tests,
            "params": self._params_view,
            "logs": self._logs,
        }
        if self.is_simulated:
            # Only when there is a simulation to look at - and only then is
            # it built at all, since the property below constructs it on
            # first access.
            children[self.virtual_hardware.name] = self.virtual_hardware
        return children

    def get_focus(self, *args, obj, path=None):
        if path is None:
            path = list()

        # self.snapshot(path=path, focus_path=focus_path)
        if args:
            key, *leftovers = args
            if key != "call":
                path.append(key)
                if key not in obj.snapshot_children:
                    raise NotImplementedError(f"{obj.snapshot_children=}, {obj=}")
                obj = obj.snapshot_children[key]
                return self.get_focus(*leftovers, obj=obj, path=path)

            return obj.snapshot(path=tuple(path), focus_path=tuple(path)), leftovers

        return obj.snapshot(path=tuple(path), focus_path=tuple(path)), tuple()

    def get_states(self, *args):
        states = self.snapshot(path=tuple(), focus_path=tuple())
        focus, leftovers = self.get_focus(*args, obj=self)

        if leftovers:
            self.update(*leftovers, focus=focus)

            states = self.snapshot(path=tuple(), focus_path=focus["path"])
            focus, leftovers = self.get_focus(*args, obj=self)

        states = self.snapshot(path=tuple(), focus_path=focus["path"])
        focus, leftovers = self.get_focus(*args, obj=self)
        return focus

    def update(self, *args, focus):
        if not isinstance(focus, dict):
            return focus(*args)
        if args:
            key, *leftovers = args
            if key not in focus:
                raise NotImplementedError(
                    key,
                    focus["name"],
                )
            return self.update(*leftovers, focus=focus[key])
        return focus

    def shutdown_neopixels(self):
        neopixels = self._hardware.neopixels
        assert neopixels
        for neopixel in neopixels:
            neopixel.off()
        # raise NotImplementedError

    def move_to_origin(self):
        self._hardware.bodies.turn_all_bodies_origin()
        self._hardware.bar.turn_to_origin()
        self._hardware.wait_until_everything_is_still()

    def disable_torque(self):
        self._hardware.disable_torque()

    def emergency_stop(self):
        """Immediately halt all motion: no homing, no coordinated move
        (unlike shutdown()'s move_to_origin - commanding more movement is
        the opposite of what an emergency stop should do). Disable torque
        first since that's the actual physical halt, then signal every
        thread to stop.

        Deliberately does not wait/join: once torque is off, a stale
        goal_position no longer converges, so DXL.is_moving can read True
        forever - a thread stuck in wait_for_servo() won't notice torque
        was cut and will keep busy-spinning until its own 30s timeout. The
        request handling this must return immediately regardless, since
        the single-threaded dev server can't serve anything else (including
        another emergency-stop click) while blocked in a request.
        """
        self._hardware.disable_torque()
        self.shutdown()
