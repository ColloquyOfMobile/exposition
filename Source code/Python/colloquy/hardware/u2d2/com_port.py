from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    COMM_SUCCESS,
)  # Uses Dynamixel SDK library
from functools import wraps
from threading import Lock
from time import sleep
from pathlib import Path
import serial.tools.list_ports
from colloquy.base import Base
from functools import partial
from .html import HTML
from colloquy.hardware.com_port import ComPort


class ComPort(ComPort):
    def __init__(self, owner, value=None):
        super().__init__(owner=owner, value=None)

    def set(self, com_port, *args, **kwargs):
        self._value = com_port
