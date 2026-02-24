from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from functools import wraps
from threading import Lock
from time import sleep
from pathlib import Path
import serial.tools.list_ports
from colloquy.base import Base
from functools import partial
from .html import HTML


class ComPort(Base):


    def __init__(self, owner):
        super().__init__(owner=owner)
        
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        self._value = None
        self._ports = []

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def html(self):
        return self._html

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
            self._ports = [
                port.device
                for port
                in serial.tools.list_ports.comports()]  
        
        for name in self._ports:
            self[name] = partial(self.set, com_port=name)
        
        return self._ports

    def set(self, com_port, *args, **kwargs):
        self._value = com_port