from yattag import Doc, indent
from serial.tools import list_ports
from .virtual_colloquy_driver import VirtualColloquyDriver
from utils import CustomDoc
from parameters import Parameters
from pathlib import Path
from time import sleep

PARAMETERS = Parameters().as_dict()

class Develop():
    def __init__(self, wsgi):
        self._wsgi = wsgi
        self._doc = None
        self._name = "develop"
        self.wsgi_path = Path(self._name)
        self._colloquy_driver = VirtualColloquyDriver(params=PARAMETERS)
        self._commands = {
        }
        self.run = RunCommand(owner=self)

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
        self._colloquy_driver.start()

    def close(self):
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

                with tag("div"):
                    text(f"Finished processing command '{string_command}'")
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



class RunCommand:

    def __init__(self, owner):
        self._name = "run"
        self._owner = owner
        self._wsgi = owner.wsgi
        owner.commands[self._name] = self

    def __call__(self, **kwargs):
        yield (f"| Running colloquy...")
        with self._owner.colloquy_driver:
            colloquy = self._owner.colloquy_driver
            elements = colloquy.elements
            females = colloquy.females
            males = colloquy.males
            for iteration in range(1):
                yield (f"| {iteration=}")
                for element in (*females, *males):
                    yield f"|| Turning on {element.name}' speaker..."
                    element.turn_on_speaker()
                    sleep(0.5)
                    element.turn_off_speaker()
                    yield (f"|| Turned off {element.name}' speaker...")
                    sleep(0.5)


    def write_html(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("form", action="", method="post"):
            doc.stag("input", type="submit", name="command", value=self._name)

    def test_speakers(self, **kwargs):
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            elements = colloquy.elements
            females = colloquy.females
            males = colloquy.males
            for iteration in range(iterations):
                yield (f"| {iteration=}")
                for element in (*females, *males):
                    yield f"|| Turning on {element.name}' speaker..."
                    element.turn_on_speaker()
                    sleep(1)
                    element.turn_off_speaker()
                    yield (f"|| Turned off {element.name}' speaker...")
                    sleep(0.5)


    # def _write_tests_run(self):
        # doc, tag, text = self._doc.tagtext()
        # with tag("form", action="", method="post"):
            # with tag("button", type="submit", name="command", value="tests/run"):
                # text("test colloquy")

    # def _write_test_neopixels(self):
        # doc, tag, text = self._doc.tagtext()
        # with tag("form", action="", method="post"):
            # with tag("input", type="number", name="iterations", value="1", step="1", min=1):
                # pass
            # with tag("button", type="submit", name="command", value="tests/neopixels"):
                # text("test neopixels")

    # def _write_test_speakers(self):
        # doc, tag, text = self._doc.tagtext()
        # with tag("form", action="", method="post"):
            # with tag("input", type="number", name="iterations", value="1", step="1", min=1):
                # pass
            # with tag("button", type="submit", name="command", value="tests/speakers"):
                # text("test speakers")

    # def _write_test_dxls(self):
        # doc, tag, text = self._doc.tagtext()
        # with tag("form", action="", method="post"):
            # with tag("input", type="number", name="iterations", value="1", step="1", min=1):
                # pass
            # with tag("button", type="submit", name="command", value="tests/dxls"):
                # text("test dxls")