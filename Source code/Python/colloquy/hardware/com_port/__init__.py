import serial.tools.list_ports
from colloquy.base import Base
from functools import partial


class ComPort(Base):
    def __init__(self, owner, value=None):
        super().__init__(owner=owner)

        self._value = value
        self._ports = []

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def value(self):
        return self._value

    @property
    def name(self):
        return "com port"

    @property
    def ports(self):

        for name in self._ports:
            self._dict.pop(name)

        if self.is_simulated:
            self._ports = ["simulated u2d2 port", "simulated arduino port"]
        else:
            self._ports = [port.device for port in serial.tools.list_ports.comports()]

        for name in self._ports:
            self[name] = partial(self.set, com_port=name)

        return self._ports

    def set(self, com_port, *args, **kwargs):
        raise NotImplementedError(self)
