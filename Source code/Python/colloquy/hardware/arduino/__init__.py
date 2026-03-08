import serial
import serial.tools.list_ports
from pathlib import Path
from utils import CustomDoc
import json
from time import sleep, time
from threading import Lock
from colloquy.base import Base
from .com_port import ComPort
from .html import HTML

START = time()

class Arduino(Base):

    _classes = {
        "serial": serial.Serial,
    }

    def __init__(self, owner, **kwargs):
        """
        Initialise la communication série avec l'Arduino.
        """
        super().__init__(owner=owner)
        self.lock = Lock()
        self._port_handler = None
        self._was_open = None
        self._html = HTML(owner=self)
        self._context_depth = 0

        self[self.html.name] = self.html.handle_request
        self._com_port = ComPort(owner=self)
        self[self.com_port.name] = self.com_port
        self["open"] = self.open
        self["close"] = self.close

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    def __enter__(self):
        if self._context_depth == 0:
            self._was_open = self.port_handler.is_open
            if not self._was_open:
                self.open()
        self._context_depth += 1

    def __exit__(self, *args, **kwargs):
        self._context_depth -= 1
        if self._context_depth == 0 and not self._was_open:
            self.close()

    @property
    def port_name(self):
        return self.port_handler.port

    @property
    def com_port(self):
        return self._com_port

    @property
    def is_open(self):
        return self.port_handler.is_open

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def html(self):
        return self._html

    @property
    def params(self):
        return self.owner.params

    @property
    def name(self):
        return "arduino"

    @property
    def baudrate(self):
        return self.params["arduino"]["baudrate"]

    @property
    def port_handler(self):
        if self._port_handler is None:
            if not self.is_simulated:
                self._port_handler = serial.Serial(baudrate=self.baudrate, timeout=1)
            else:
                self._port_handler = self.colloquy.virtual_hardware.arduino_serial_port 
                
            # Setting port name here avoid opening the port
            self.port_handler.port = self.params["arduino"]["communication port"]

        return self._port_handler

    def send(self, path, **data):
        with self:
            return self._send_unsafe(path, **data)

    def _send_unsafe(self, path, **data):
        command = {"path": path.as_posix(), **data}
        self.log(f"{command=}")
        serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        with self.lock:
            self.port_handler.write(serialized_command.encode('utf-8'))  # Envoie de la commande

            data = self.port_handler.readline()  # Lit une ligne du port série
        # if not data:
            # raise TimeoutError("No response from Arduino.")

        return data

    def _parse(self, data):
        """
        Analyse les données brutes reçues de l'Arduino.

        Arguments :
        - data : Données brutes (bytes) reçues.

        Retourne :
        - Un type natif Python (par exemple dictionnaire).
        """
        data = data.decode('utf-8')
        try:
            data = json.loads(data)  # Convertir JSON en dictionnaire
        except json.JSONDecodeError:
            raise ValueError(f"Invalid response format from Arduino. ({data=})")

        if data["status"] == "error":
            raise RuntimeError(data["message"])

        self.log(f"response={data}")
        return data

    def close(self, request=None):
        """
        Ferme le port série.
        """
        self.port_handler.close()

    def open(self, request=None):
        """
        Ouvre le port série.
        """
        self.port_handler.open()
        self.wait_for_reboot()


    def wait_for_reboot(self):
        start = time()
        while True:
            self.log("Waiting for Arduino to reboot.")
            data = self.port_handler.readline().strip()
            if data == b"Hello!":
                break
            if time()-start > 2:
                raise RuntimeError("Arduino was to long to reboot !")


    def _get_com_ports(self):
        return [
            port.device
            for port
            in serial.tools.list_ports.comports()]
