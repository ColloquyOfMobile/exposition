from pathlib import Path
import urllib
import os
import sys

#
from colloquy.base_thread import BaseThread
from .events import Events
from .base import Base
from .tests import Tests

# from .server import Server
from .hardware import Hardware
from .cli import CLI
from .tests import Tests
from .exposition import Exposition
from .params import Params
from .virtual_hardware import VirtualHardware


class Colloquy(BaseThread):
    def __init__(self):
        super().__init__(owner=None)

        self._params = Params.load(Path("local/params.json"))

        self._is_opened = False
        self._request = None
        self._args = None
        self._virtual_hardware = None

        self._hardware = Hardware(owner=self)
        self._tests = Tests(owner=self)
        self._exposition = Exposition(owner=self)

        self["hardware"] = self._hardware

        self._events = Events(shutdown=BaseThread._shutdown)

    @property
    def light_patterns(self):
        # During search the male blinks.
        # The blink pattern define 2 things:
        # - the male identity: 1 or 2
        # - which kind of interation the male is look for (drive state): "O" or "P" or both
        # Extracted from TJ's arduino code "logic35_system.ino, line 87."
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
    def cli(self):
        return self._cli

    @property
    def exposition(self):
        return self._exposition

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
        return {
            "hardware": self._hardware,
            "exposition": self._exposition,
            "tests": self._tests,
        }

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
