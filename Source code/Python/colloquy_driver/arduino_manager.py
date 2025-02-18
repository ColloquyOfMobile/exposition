
import serial
from pathlib import Path
import json
from time import sleep, time
from threading import Event

class ArduinoManager:

    _classes = {
        "serial": serial.Serial,
    }

    def __init__(self, **kwargs):
        """
        Initialise la communication série avec l'Arduino.
        """
        port_name = kwargs["communication port"]
        baudrate = kwargs["baudrate"]
        self.port_handler = self._classes["serial"](port=port_name, baudrate=baudrate, timeout=1)
        self.wait_for_reboot()
        self._busy = Event()

        # IMPORTANT let the arduino reload
        # sleep(0.5)


    def send(self, path, data):
        command = {"path": str(path), "data": data}
        serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        while self._busy.is_set():
            sleep(0.01)
        self._busy.set()
        self.port_handler.write(serialized_command.encode('utf-8'))  # Envoie de la commande

        data = self.port_handler.readline()  # Lit une ligne du port série
        self._busy.clear()
        if not data:
            raise TimeoutError("No response from Arduino.")


        return self._parse(data)

    def send_yield(self, path, data):
        command = {"path": str(path), "data": data}
        serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        # print(f"{serialized_command.encode('utf-8')=}")
        self.port_handler.write(serialized_command.encode('utf-8'))  # Envoie de la commande
        # self.port_handler.write(b'{}\n')
        while True:
            data = self.port_handler.readline()  # Lit une ligne du port série
            # print(f"{data=}")
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
            return json.loads(data)  # Convertir JSON en dictionnaire
        except json.JSONDecodeError:
            raise ValueError(f"Invalid response format from Arduino. ({data=})")

        if data["status"] == "error":
            raise RuntimeError(data["message"])


    def stop(self):
        """
        Ferme le port série.
        """
        self.port_handler.close()

    def start(self):
        """
        Ferme le port série.
        """
        if not self.port_handler.is_open:
            self.port_handler.open()
            self.wait_for_reboot()

    def _turn_off_all_neopixel(self):
        raise NotImplementedError("Should give access to colloquy driver here to implement this.")
        self.send(path="male1/neopixel", data="on")

    def wait_for_reboot(self):
        start = time()
        while True:
            print("|| Waiting for Arduino to reboot.")
            data = self.port_handler.readline().strip()
            if data == b"Hello!":
                break
            if time()-start > 2:
                raise RuntimeError("Arduino was to long to reboot !")