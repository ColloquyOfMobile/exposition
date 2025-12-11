from pathlib import Path
import urllib
import os
import sys

from utils import CustomDoc
from .events import Events
from .base import Base
from .tests import Tests
from .server import Server
from .hardware import Hardware
from .parameters import Parameters
from .cli import CLI
from .log import Log
from .tests import Tests
from .exposition import Exposition

class Colloquy(Base):

    def __init__(self):
        super().__init__(owner=None)

        self._request = None
        self._args = None
        self._log = Log(owner=self)

        self._params = Parameters(owner=self)

        self._hardware = Hardware(owner=self)
        self._tests = Tests(owner=self)
        self._exposition = Exposition(owner=self)

        self._server = Server(owner=self)
        self._cli = CLI(owner=self)

        self["server"] = self._server
        self["hardware"] = self._hardware

        self._events = Events()

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
    def log(self):
        return self._log

    @property
    def hardware(self):
        return self._hardware

    @property
    def server(self):
        return self._server

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

    def run(self, ):
        return self.server()

    def shutdown(self):
        self.tests.shutdown()
        self.hardware.shutdown()
        self.exposition.shutdown()

    def _call_root(self):
        print("Available command:")
        for name in self:
            print(f"- {name}")
        # raise NotImplementedError(f"{self=}")