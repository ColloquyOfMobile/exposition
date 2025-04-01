from time import sleep
from colloquy_driver.arduino_manager import ArduinoManager
import json
from pathlib import Path
import re

class VirtualSerialPort:

    def __init__(self, port, baudrate, timeout):
        self._is_open = True
        self._possible_paths = set()
        self._load_possible_paths()
        self._readline_results = self._iter_readline_results()

    def readline(self):
        return next(self._readline_results)

    def write(self, data):
        data = data.decode()
        data = json.loads(data)
        path = data["path"]
        assert path in self._possible_paths, f"{path=}, {self._possible_paths=}"
        if path.endswith("neopixel"):
            assert "r" in data
            assert "g" in data
            assert "b" in data
            assert "w" in data
            assert "brightness" in data

    @property
    def is_open(self):
        return self._is_open

    def close(self):
        self._is_open = False

    def open(self):
        self._readline_results = self._iter_readline_results()
        self._is_open = True

    def _load_possible_paths(self):
        """Read arduino code to extract the possible paths."""
        path = Path("Source code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino")
        text = path.read_text()

        # Expression régulière pour capturer les valeurs de path == "..."
        paths = re.findall(r'path\s*==\s*"([^"]+)"', text)

        # Stocker les chemins extraits
        self._possible_paths = set(paths)
        # raise NotImplementedError(f"{self._possible_paths=}")

    def _iter_readline_results(self):
        sleep(0.1)
        yield b"Hello!"
        while self.is_open:
            sleep(0.1)
            yield b'{"status": "success"}'

class VirtualArduinoManager(ArduinoManager):

    _classes = {
        "serial": VirtualSerialPort,
    }