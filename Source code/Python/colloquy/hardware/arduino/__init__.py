import serial
import serial.tools.list_ports
from pathlib import Path
from utils import CustomDoc
import json
from time import sleep, time
from threading import Lock
from colloquy.base import Base
from .virtual_serial_port import VirtualSerialPort
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
    def port_name(self):
        return self.params["arduino"]["communication port"]

    @property
    def baudrate(self):
        return self.params["arduino"]["baudrate"]

    @property
    def port_handler(self):
        if self._port_handler is None:
            klass = VirtualSerialPort
            if not self.is_simulated:
                klass = serial.Serial
            self._port_handler = klass(baudrate=self.baudrate, timeout=1)
            # Setting port name here avoid opening the port
            self.port_handler.port = self.port_name

        return self._port_handler

    def send(self, path, **data):
        with self:
            return self._send_unsafe(path, **data)

    # def send_yield(self, path, **data):
        # command = {"path": str(path), **data}
        # serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        # self.port_handler.write(serialized_command.encode('utf-8'))  # Envoie de la commande
        # while True:
            # with self.lock:
                # data = self.port_handler.readline()  # Lit une ligne du port série
            # if data:
                # break
            # yield f"Arduino still processing {command}..."

        # return self._parse(data)

    def _send_unsafe(self, path, **data):
        command = {"path": path.as_posix(), **data}
        self.log(f"{command=}")
        serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        with self.lock:
            self.port_handler.write(serialized_command.encode('utf-8'))  # Envoie de la commande

            # data = self.port_handler.readline()  # Lit une ligne du port série
        # if not data:
            # raise TimeoutError("No response from Arduino.")

        return {} # self._parse("{}".encode())

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

    def _set_com_port(self, com_port):
        com_port = com_port[0]
        self.port_handler.port = com_port
        self.hardware.params["arduino"]["communication port"] = com_port
        self.hardware.save()

    def _add_html_com(self):
        doc, tag, text = self.html_doc.tagtext()

        port_list = self._get_com_ports()

        with tag("form", method="post"):
            with tag("label", **{"id": "arduino/com_port"}):
                text(f"Arduino com port:")

            with tag("select", id="arduino/com_port", name="com_port"):
                for port in port_list:
                    kwargs = {}
                    if port == self.port_handler.name:
                        kwargs["selected"] = True
                    with tag('option', value=port, **kwargs):
                        text(port)

            with tag("button", name="action", value="arduino/com_port/set"):
                text(f"set.")

            self.hardware.actions["arduino/com_port/set"] = self._set_com_port
