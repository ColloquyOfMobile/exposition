from colloquy.base_thread import BaseThread
from .virtual_serial_port import VirtualSerialPort
from .virtual_port_handler import VirtualPortHandler
from .virtual_packet_handler import VirtualPacketHandler

class VirtualHardware(BaseThread):
    def __init__(self, owner):
        super().__init__(owner)
        self._arduino_serial_port = None
        self._u2d2_packet_handler = None

    @property
    def params(self):
        return self.owner.params

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def name(self):
        return "virtual hardware"

    @property
    def dxls(self):
        return self.u2d2_packet_handler.dxls

    @property
    def arduino_serial_port(self):
        if self._arduino_serial_port is None:
            self._arduino_serial_port = VirtualSerialPort(owner=self)
        return self._arduino_serial_port

    @property
    def u2d2_packet_handler(self):
        if self._u2d2_packet_handler is None:
            self._u2d2_packet_handler = VirtualPacketHandler(owner=self)
        return self._u2d2_packet_handler

    def u2d2_port_handler(self, port_name):
        return VirtualPortHandler(port_name)
