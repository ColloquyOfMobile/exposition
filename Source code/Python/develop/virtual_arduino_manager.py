from colloquy_driver.arduino_manager import ArduinoManager

class VirtualSerialPort:

    def __init__(self, port, baudrate, timeout):
        self._is_open = True
        self._readline_results = self._iter_readline_results()

    def _iter_readline_results(self):
        yield b"Hello!"
        while self.is_open:
            yield b"{}"

    def readline(self):
        return next(self._readline_results)

    def write(self, data):
        print(f"{data=}")
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

    def __init__(self, **kwargs):
        """
        Initialise la communication série avec l'Arduino.
        """
        port_name = kwargs["communication port"]
        baudrate = kwargs["baudrate"]
        self.port_handler = self._classes["serial"](port=port_name, baudrate=baudrate, timeout=1)
        self.wait_for_reboot()


