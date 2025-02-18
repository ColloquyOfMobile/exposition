from yattag import Doc, indent
from serial.tools import list_ports
from tests import ColloquyTests
from utils import CustomDoc
from pathlib import Path

class Tests():
    def __init__(self, wsgi):
        self._wsgi = wsgi
        self._doc = None
        self.wsgi_path = Path("tests")
        self._tests = ColloquyTests()
        self._commands = {
            "tests/run": self._tests.run,
            "tests/neopixels": self._tests.test_neopixels,
            "tests/speakers": self._tests.test_speakers,
            "tests/speakers/female1": self._tests.test_fem1_speaker,
            "tests/speakers/female2": self._tests.test_fem2_speaker,
            "tests/speakers/female3": self._tests.test_fem3_speaker,
            "tests/speakers/male1": self._tests.test_male1_speaker,
            "tests/speakers/male2": self._tests.test_male2_speaker,
            "tests/dxls": self._tests.test_dxls,
            "tests/play pacman": self._tests.play_pacman,
            "tests/play pink panther": self._tests.play_pinkpanther,
        }

    def open(self):
        self._tests.open()

    def close(self):
        self._tests.close()

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
                text("Tests:")
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
            self._write_tests_run()
            self._write_test_neopixels()
            self._write_test_speakers()
            self._write_test_dxls()
            self._write_specific_tests()
            yield doc.read().encode()



    def _write_tests_run(self):
        doc, tag, text = self._doc.tagtext()
        with tag("form", action="", method="post"):
            with tag("button", type="submit", name="command", value="tests/run"):
                text("test colloquy")

    def _write_test_neopixels(self):
        doc, tag, text = self._doc.tagtext()
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="iterations", value="1", step="1", min=1):
                pass
            with tag("button", type="submit", name="command", value="tests/neopixels"):
                text("test neopixels")

    def _write_test_speakers(self):
        doc, tag, text = self._doc.tagtext()
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="iterations", value="1", step="1", min=1):
                pass
            with tag("button", type="submit", name="command", value="tests/speakers"):
                text("test speakers")

    def _write_test_dxls(self):
        doc, tag, text = self._doc.tagtext()
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="iterations", value="1", step="1", min=1):
                pass
            with tag("button", type="submit", name="command", value="tests/dxls"):
                text("test dxls")


    def _write_specific_tests(self):
        doc, tag, text = self._doc.tagtext()
        commands = [
            "tests/speakers/female1",
            "tests/speakers/female2",
            "tests/speakers/female3",
            "tests/speakers/male1",
            "tests/speakers/male2",
            "tests/open door test",
            "tests/play pacman",
            "tests/play pink panther",
            ]
        for command in commands:
            assert command in self._commands
            with tag("form", action="", method="post"):
                with tag("input", type="number", name="iterations", value="1", step="1", min=1):
                    pass
                with tag("input", type="submit", name="command", value=command):
                    pass

    def _write_arduino_connect(self):
        doc, tag, text = self._doc.tagtext()

        # Get the list of available serial ports
        ports = list_ports.comports()
        port_list = [(port.device, port.description) for port in ports]

        with tag("form", action="", method="post"):
            with tag("select", name="selected", value=""):
                for port, description in port_list:
                    with tag("option", value=port):
                        text(f"{port} - {description}")
            with tag("button", type="submit", name="command", value="arduino/connect"):
                text("connect arduino")

    def add_html_link(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("h2",):
            with tag("a", href=self.wsgi_path.as_posix()):
                text("Tests.")