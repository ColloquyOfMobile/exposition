from time import sleep
from colloquy_driver.arduino_manager import ArduinoManager

class VirtualSerialPort:

    def __init__(self, port, baudrate, timeout):
        self._is_open = True
        self._readline_results = self._iter_readline_results()

    def _iter_readline_results(self):
        sleep(0.1)
        yield b"Hello!"
        while self.is_open:
            sleep(0.1)
            yield b"{}"

    def readline(self):
        return next(self._readline_results)

    def write(self, data):
        pass

    @property
    def is_open(self):
        return self._is_open

    def close(self):
        self._is_open = False

class VirtualArduinoManager(ArduinoManager):

    _classes = {
        "serial": VirtualSerialPort,
    }