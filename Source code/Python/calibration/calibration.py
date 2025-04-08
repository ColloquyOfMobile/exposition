from utils import CustomDoc
from colloquy import ColloquyDriver
from parameters import Parameters
from pathlib import Path
from .commands import BarMoveAndWait, BodyMoveAndWait, BodyToggleNeopixel, BodyToggleSpeaker
from .commands import BodyMoveToOriginAndWait, BarMoveToPositionAndWait, BarMoveToOriginAndWait, BodyConfigureNeopixel
PARAMETERS = Parameters().as_dict()

class Calibration():
    def __init__(self, wsgi, owner, path):
        self._wsgi = wsgi
        self._doc = None
        self.path = path
        self._owner = owner
        self._commands = {}
        self._elements = {}

    @property
    def doc(self):
        return self._doc

    @property
    def colloquy_driver(self):
        return self._owner.colloquy_driver

    @property
    def commands(self):
        return self._commands

    def add_command(self, element, command):
        element = element.name
        if element not in self._elements:
            self._elements[element] = set()
        self._commands[command.name] = command
        self._elements[element].add(command)

    def open(self):
        colloquy = self.colloquy_driver
        for body in colloquy.bodies:
            for command_class in [
                BodyMoveAndWait,
                BodyToggleNeopixel,
                BodyToggleSpeaker,
                BodyMoveToOriginAndWait,
                BodyConfigureNeopixel,
                ]:
                command = command_class(owner=self, body=body)
                self.add_command(body, command)

        self.add_command(
            element=colloquy.bar,
            command=BarMoveAndWait(owner=self)
            )
        self.add_command(
            element=colloquy.bar,
            command=BarMoveToOriginAndWait(owner=self)
            )

        for position, actors in self.colloquy_driver.interactions.items():
            position = position + self.colloquy_driver.bar.dxl_origin
            command = BarMoveToPositionAndWait(owner=self, position=position, actors=actors)
            self.add_command(element=colloquy.bar, command=command)

    def close(self):
        pass

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

    def _write_body(self, **kwargs):
        doc, tag, text = self._doc.tagtext()
        with tag("body"):
            with tag("h1",):
                text("Colloquy of Mobiles")
            with tag("div",):
                with tag("a", href=".."):
                    text("<- back")
            with tag("h2",):
                text("Calibration:")
            command = kwargs.get("command")
            if command is not None:
                with tag("h3"):
                    text("logs:")
                yield doc.read().encode()
                string_command = command[0]
                command = self._commands[string_command]
                for log in command(**kwargs):
                    print(log)
                    with tag("div"):
                        text(log)
                    yield doc.read().encode()

                with tag("div"):
                    text(f"Finished processing command '{string_command}'")
                yield doc.read().encode()


            for name in sorted(self._elements):
                commands = self._elements[name]
                with tag("h3",):
                    text(f"{name}:")
                for command in sorted(commands):
                    command.write_html()
            yield doc.read().encode()

    def add_html_link(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("h2",):
            with tag("a", href=f"{self.path.as_posix()}"):
                text("Calibration.")