from pathlib import Path
import csv
import time
import traceback
from datetime import datetime, timedelta
from time import sleep
from colloquy import ColloquyDriver
from parameters import Parameters
from utils import CustomDoc
from pathlib import Path
from time import sleep
from threading import Thread, Event
from calibration import Calibration
from colloquy.logger import Logger

PARAMETERS = Parameters().as_dict()
# PARAMETERS.pop("dynamixel network")

class Tests:

    classes = {
        "colloquy": ColloquyDriver
    }

    def __init__(self, wsgi, name="tests"):
        self._owner = None
        self._name = name
        self._wsgi = wsgi
        self.path = Path(self._name)
        self.active = None
        self._elements = set()
        self._threads = set()
        self._colloquy = self.classes["colloquy"](owner=self, params=PARAMETERS)
        self._commands = {}
        handlers = [
            Calibration(wsgi=wsgi, owner=self, path=self.path/"calibration"),
        ]
        self.handlers = {
            handler.path: handler
            for handler in handlers
            }
        self.run = RunCommand(owner=self)
        self.stop = StopCommand(owner=self)
        self._log = Logger(owner=self)
        # self.colloquy_thread = None


    def __eq__(self, other):
        return other.name == self.name

    def __lt__(self, other):
        return self.name < other.name

    def __call__(self, **kwargs):
        if self._wsgi.path != self.path:
            self.activate()
            yield from self.active(**kwargs)
            return

        if self.active is not None:
            self.active.close()
            self.active = None

        self._doc = CustomDoc()
        doc, tag, text = self._doc.tagtext()
        self._wsgi.start_response('200 OK', [('Content-Type', 'text/html')])

        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            with tag("head"):
                with tag("title"):
                    text(f"Colloquy of Mobiles")
                doc.asis(
                    '<meta name="viewport"'
                    ' content="width=device-width,'
                    " initial-scale=1,"
                    ' interactive-widget=resizes-content" />'
                )


            for response in self._write_body(**kwargs):
                yield response

        response = doc.read()
        yield response.encode()

    @property
    def owner(self):
        return self._owner

    @property
    def log(self):
        return self._log

    @property
    def threads(self):
        return self._threads

    @property
    def elements(self):
        return self._elements

    @property
    def name(self):
        return self._name

    @property
    def colloquy(self):
        return self._colloquy

    @property
    def commands(self):
        return self._commands

    @property
    def wsgi(self):
        return self._wsgi

    def open(self):
        self.threads.clear()
        self._colloquy.open()

    def close(self):
        self._colloquy.close()
        for thread in self.threads:
            thread.join()

    def _write_header(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("div", style="display:flex;"):
            with tag("div", style="display:flex; align-items:center; padding-right:1ch;"):
                with tag("a", href=".."):
                    text("<- back")
            with tag("h1", style="display:flex; justify-items:center;"):
                text("Colloquy of Mobiles")


    def _write_body(self, **kwargs):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("body"):
            self._write_header()

            for handler in sorted(self.handlers.values()):
                handler.add_html_link()

            with tag("h2",):
                text(f"{self._name.title()}:")

            command = kwargs.get("command")
            if command is not None:
                with tag("h3"):
                    text("logs:")
                string_command = command[0]
                command = self._commands[string_command]
                for log in command(**kwargs):
                    print(f"{log=}")
                    with tag("div"):
                        text(log)
                    yield doc.read().encode()

                yield doc.read().encode()
            with tag("h3",):
                text("commands:")
            self._write_commands()
            yield doc.read().encode()


    def _write_commands(self):
        doc, tag, text = self._doc.tagtext()
        for command_path in sorted(self._commands):
            command = self._commands[command_path]
            command.write_html()

    def add_html_link(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("h2",):
            with tag("a", href=self.path.as_posix()):
                text(f"{self._name.title()}.")

    def activate(self):
        path = Path(*self._wsgi.path.parts[:2])
        # self._colloquy.stop()
        if self.active is not None:
            if self.active.path == path:
                return
            self.active.close()
        self.active = self.handlers[path]
        self.active.open()


class Command:

    def __init__(self, owner, name):
        self._name = name
        self._owner = owner
        self._wsgi = owner.wsgi
        owner.commands[self._name] = self

    def write_html(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("form", action="", method="post"):
            doc.stag("input", type="submit", name="command", value=self._name)

class StopCommand(Command):

    def __init__(self, owner):
        Command.__init__(self, owner, name="stop")

    def __call__(self, **kwargs):
        owner = self._owner
        owner.colloquy.stop()
        yield "Stopped."

class RunCommand(Command):

    def __init__(self, owner):
        Command.__init__(self, owner, name="run")

    def __call__(self, **kwargs):
        owner = self._owner
        owner.stop_event = Event()
        self._doc = CustomDoc()
        doc, tag, text = self._wsgi.doc.tagtext()
        owner.colloquy.start()
        yield "Started..."