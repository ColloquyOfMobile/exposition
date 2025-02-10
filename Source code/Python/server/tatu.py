from yattag import Doc, indent
from serial.tools import list_ports
from colloquy_tests import ColloquyTests
from .utils import CustomDoc
from colloquy_driver import ColloquyDriver
from parameters import Parameters
from threading import Thread, Event
from time import sleep, time

PARAMETERS = Parameters().as_dict()

class Tatu():
    def __init__(self, wsgi):
        self._wsgi = wsgi
        self._doc = None
        self._commands = {
            "start": self.start,
            "stop": self.stop,
        }
        self.colloquy_driver = None

    def open(self):
        self.colloquy_driver = ColloquyDriver(PARAMETERS)
        pass

    def close(self):
        self.colloquy_driver.stop()
        self.colloquy_driver = None

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
            with tag("div"):
                with tag("a", href="/shutdown"):
                    text("Shutdown server")
            with tag("h1",):
                text("Colloquy of Mobiles")
            with tag("div",):
                with tag("a", href=".."):
                    text("<- back")
            with tag("h2",):
                text("TATU:")
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
            yield doc.read().encode()



    def _write_tests_run(self):
        doc, tag, text = self._doc.tagtext()
        with tag("form", action="", method="post"):
            with tag("button", type="submit", name="command", value="start"):
                text("Start")
        with tag("form", action="", method="post"):
            with tag("button", type="submit", name="command", value="stop"):
                text("Stop")

    def start(self, **kwargs):
        self._stop_event = Event()
        self._thread = Thread(target=self._thread_target)
        self._thread.start()
        yield "Started"

    def stop(self, **kwargs):
        self._stop_event.set()
        self._thread.join()
        yield "Stopped"

    def _thread_target(self, **kwargs):
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            elements = self.colloquy_driver.elements
            bodies = self.colloquy_driver.bodies
            bar = self.colloquy_driver.bar

            neopixel_start = time()
            speaker_start = time()
            duration = 10
            buzzers = list(bodies)
            buzzer = None

            while True:
                if self._stop_event.is_set():
                    break

                for element in elements:
                    if not element.is_moving:
                        # print(f"{element=}, {element.is_moving}")
                        element.toggle_position()

                if time() - neopixel_start > 0.5:
                    for element in bodies:
                        element.toggle_neopixel()
                        neopixel_start = time()

                if time() - speaker_start > duration:
                    if buzzer is None:
                        buzzer = buzzers.pop(0)
                        buzzer.turn_on_speaker()
                        duration = 0.7
                    else:
                        buzzer.turn_off_speaker()
                        buzzers.append(buzzer)
                        buzzer = None
                        duration = 10

                    speaker_start = time()

                if not bar.is_moving:
                    bar.toggle_position()

            for element in bodies:
                element.turn_off_speaker()
                element.turn_off_neopixel()