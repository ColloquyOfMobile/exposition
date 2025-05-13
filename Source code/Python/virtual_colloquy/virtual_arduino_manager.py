from time import sleep
from colloquy.arduino_manager import ArduinoManager
import json
from pathlib import Path
import re

class VirtualSerialPort:

    def __init__(self, baudrate, timeout, port=None):
        assert port is None, f"Port should be none to avoid opening! ({port=})"
        self._port = port
        self._is_open = False
        if port is not None:
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

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    @property
    def name(self):
        return self._port

    def close(self):
        self._is_open = False

    def open(self):
        assert not self.is_open
        assert self._port is not None
        self._readline_results = self._iter_readline_results()
        self._is_open = True

    def _load_possible_paths(self):
        """Read arduino code to extract the possible paths."""
        path = Path("Source code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino")
        text = path.read_text()

        # Expression régulière pour capturer les valeurs de path == "..."
        paths = re.findall(r'if\s*\(\s*path\s*==\s*"([^"]+)"\s*\)', text)

        # Stocker les chemins extraits
        self._possible_paths = sorted(paths)

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

    def _get_com_ports(self):
        return ["VirtualCOM1", "VirtualCOM2"]