from colloquy.base import Base
from pathlib import Path
from colloquy.ui import leaves


class LightSensor(Base):
    """One of a male's 4 light sensors (a/b/c/d). Mirrors Female's
    LightSensor (same threshold param, same read/read_as_bool shape) - the
    firmware already implements maleN.lightSensorX.read() for all 4, but
    there was previously no working Python-side reader: the only prior
    attempt (colloquy/hardware/arduino/light_sensor_command) never set
    _read_func/_register/dxl_id, so calling it would raise AttributeError.
    """

    def __init__(self, owner, letter):
        assert letter in "abcd"
        self._letter = letter
        super().__init__(owner=owner)

    @property
    def male(self):
        return self.owner

    @property
    def arduino(self):
        return self.owner.arduino

    @property
    def is_simulated(self):
        if super().is_simulated:
            return True
        return self.params["emulate light sensor"]

    @property
    def threashold(self):
        return self.params["photosensor_threashold"]

    @property
    def params(self):
        return self.owner.params

    @property
    def name(self):
        return f"light sensor {self._letter}"

    @property
    def arduino_path(self):
        return Path(f"m{self.owner.id_number}/light sensor/{self._letter}")

    def read_as_bool(self):
        return self.read() > self.threashold

    def read(self):
        with self.arduino:
            response = self.arduino.send(self.arduino_path)
        return int(response)

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["read"] = self.read
        states["value"] = leaves.value(path, "value", self.read())
        return states
