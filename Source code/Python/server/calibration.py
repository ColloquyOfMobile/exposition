from utils import CustomDoc
from colloquy_driver import ColloquyDriver
from parameters import Parameters
from pathlib import Path

PARAMETERS = Parameters().as_dict()

class Calibration():
    def __init__(self, wsgi):
        self._wsgi = wsgi
        self._doc = None
        self.wsgi_path = Path("calibration")
        self.colloquy_driver = None
        self._commands = {
            "bar/move and wait": self.bar_move_and_wait,
        }

    def open(self):
        self.colloquy_driver = ColloquyDriver(PARAMETERS)

    def close(self):
        self.colloquy_driver.stop()
        self.colloquy_driver = None

    def bar_move_and_wait(self, **kwargs):
        position = int(kwargs["position"][0])
        self.colloquy_driver.bar.move_and_wait(position)
        yield "Finish moving the bar."

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
            self._write_move_bar()
            yield doc.read().encode()

    def _write_move_bar(self):
        doc, tag, text = self._doc.tagtext()
        position = self.colloquy_driver.bar.position
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="position", value=position, step="1"):
                pass
            with tag("button", type="submit", name="command", value="bar/move and wait"):
                text("bar/move and wait")

    def add_html_link(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("h2",):
            with tag("a", href=self.wsgi_path.as_posix()):
                text("Calibration.")