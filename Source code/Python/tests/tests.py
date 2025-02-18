from pathlib import Path
import csv
import time
import traceback
from datetime import datetime, timedelta
from time import sleep
from colloquy_driver import ColloquyDriver
from parameters import Parameters
from utils import CustomDoc
from pathlib import Path
from time import sleep
from threading import Thread, Event

PARAMETERS = Parameters().as_dict()
# PARAMETERS.pop("dynamixel network")

class Tests:

    classes = {
        "colloquy_driver": ColloquyDriver
    }

    def __init__(self, wsgi, name="tests"):
        self._name = name
        self._wsgi = wsgi
        self.wsgi_path = Path(self._name)
        self._colloquy_driver = None
        self._commands = {
        }
        self.run = RunCommand(owner=self)
        self.stop = StopCommand(owner=self)
        self.colloquy_thread = None


    @property
    def colloquy_driver(self):
        return self._colloquy_driver

    @property
    def commands(self):
        return self._commands

    @property
    def wsgi(self):
        return self._wsgi

    def open(self):
        if self._colloquy_driver is None:
            self._colloquy_driver = self.classes["colloquy_driver"](params=PARAMETERS)
        self._colloquy_driver.start()

    def close(self):
        if self.colloquy_thread is not None:
            self.colloquy_driver.stop_event.set()
            self.colloquy_thread.join()
        self._colloquy_driver.stop()

    def __call__(self, **kwargs):
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
            with tag("h2",):
                text(f"{self._name.title()}:")
            command = kwargs.get("command")
            if command is not None:
                with tag("h3"):
                    text("logs:")
                string_command = command[0]
                command = self._commands[string_command]
                for log in command(**kwargs):
                    print(log)
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
            with tag("a", href=self.wsgi_path.as_posix()):
                text(f"{self._name.title()}.")


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
        owner.colloquy_driver.stop_event.set()
        owner.colloquy_thread.join()
        yield "Stopped."

class RunCommand(Command):

    def __init__(self, owner):
        Command.__init__(self, owner, name="run")

    def __call__(self, **kwargs):
        owner = self._owner
        owner.stop_event = Event()
        self._doc = CustomDoc()
        doc, tag, text = self._wsgi.doc.tagtext()
        # self._wsgi.start_response('200 OK', [('Content-Type', 'text/html')])
        owner.colloquy_thread = Thread(target=owner.colloquy_driver.run)
        owner.colloquy_thread.start()
        yield "Started..."