
import serial
from pathlib import Path
import json
from time import sleep, time

class ArduinoManager:
    def __init__(self, **kwargs):
        """
        Initialise la communication série avec l'Arduino.
        """
        port_name = kwargs["communication port"]
        baudrate = kwargs["baudrate"]
        self.port_handler = serial.Serial(port=port_name, baudrate=baudrate, timeout=1)
        self.wait_for_reboot()

        # IMPORTANT let the arduino reload
        # sleep(0.5)

    def send(self, path, data):
        """
        Envoie une commande à l'Arduino et récupère la réponse.

        Arguments :
        - path : Path vers le composant (par exemple "female1/neopixel").
        - data : Commande à envoyer (par exemple "on", "off").

        Retourne :
        - La réponse analysée de l'Arduino sous forme de dictionnaire.

        Examples:
        >>> kwargs = {"communication port": "COM11", "baudrate": 57600}
        >>> arduino_manager = ArduinoManager(**kwargs)
        >>> path = Path("female1/neopixel") # Target the Female1's Neopixels.
        >>> data = "on" # Turns the Neopixels on.
        >>> arduino_manager.send(path, data) # Returns empty dict if no errors
        {}
        >>> path = Path("female1/neopixel")
        >>> data = "off" # Turns the Neopixels off.
        >>> arduino_manager.send(path, data)
        {}
        >>> path = Path("female1/speaker") # Target the Female1's speaker.
        >>> data = "on" # Turns the speaker at 300 Hz.
        >>> arduino_manager.send(path, data)
        {}
        >>> path = Path("female1/speaker")
        >>> data = "off" # Turns off the speaker.
        >>> arduino_manager.send(path, data)
        {}
        """
        command = {"path": str(path), "data": data}
        serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        # print(f"{serialized_command.encode('utf-8')=}")
        self.port_handler.write(serialized_command.encode('utf-8'))  # Envoie de la commande
        # self.port_handler.write(b'{}\n')

        data = self.port_handler.readline()  # Lit une ligne du port série
        # print(f"{data=}")
        if not data:
            raise TimeoutError("No response from Arduino.")

        return self._parse(data)

    def send_yield(self, path, data):
        """
        Envoie une commande à l'Arduino et récupère la réponse sans timeout.

        Arguments :
        - path : Path vers le composant (par exemple "female1/neopixel").
        - data : Commande à envoyer (par exemple "on", "off").

        Retourne :
        - La réponse analysée de l'Arduino sous forme de dictionnaire.
        """
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

    def wait_for_reboot(self):
        start = time()
        while True:
            print("|| Waiting for Arduino to reboot.")
            data = self.port_handler.readline().strip()
            if data == b"Hello!":
                break
            if time()-start > 2:
                raise RuntimeError("Arduino was to long to reboot !")