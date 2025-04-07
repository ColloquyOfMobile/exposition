import serial
from pathlib import Path
import json
from time import sleep, time
from threading import Lock
from .thread_driver import ThreadDriver
START = time()

class ArduinoManager(ThreadDriver):

    _classes = {
        "serial": serial.Serial,
    }

    def __init__(self, **kwargs):
        """
        Initialise la communication série avec l'Arduino.
        """
        ThreadDriver.__init__(self, kwargs["name"])
        self.lock = Lock()
        port_name = kwargs["communication port"]
        baudrate = kwargs["baudrate"]
        self.port_handler = self._classes["serial"](baudrate=baudrate, timeout=1)
        # Set port name avoid opening the port
        self.port_handler.port = port_name

    def send(self, path, **data):
        command = {"path": str(path), **data}
        self.log(f"{round(time()-START, 2)}: {command=}")
        serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        with self.lock:
            self.port_handler.write(serialized_command.encode('utf-8'))  # Envoie de la commande

            data = self.port_handler.readline()  # Lit une ligne du port série
        if not data:
            raise TimeoutError("No response from Arduino.")

        return self._parse(data)

    def send_yield(self, path, **data):
        command = {"path": str(path), **data}
        serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        self.port_handler.write(serialized_command.encode('utf-8'))  # Envoie de la commande
        while True:
            with self.lock:
                data = self.port_handler.readline()  # Lit une ligne du port série
            if data:
                break
            yield f"Arduino still processing {command}..."

        return self._parse(data)

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

        self.log(f"{data=}")
        return data


    def close(self):
        """
        Ferme le port série.
        """
        self.port_handler.close()

    def open(self):
        """
        Ouvre le port série.
        """
        self.port_handler.open()
        self.wait_for_reboot()


    def wait_for_reboot(self):
        start = time()
        while True:
            print("|| Waiting for Arduino to reboot.")
            data = self.port_handler.readline().strip()
            if data == b"Hello!":
                break
            if time()-start > 2:
                raise RuntimeError("Arduino was to long to reboot !")