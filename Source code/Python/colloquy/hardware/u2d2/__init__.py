from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from functools import wraps
from threading import Lock
from time import sleep
from pathlib import Path
import serial.tools.list_ports
from colloquy.base import Base
from .html import HTML
from .com_port import ComPort
from colloquy.hardware.dxl import DXL


def handle_error(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        with self:        
            dxl_id = args[1]
            for i in range(5):
                
                with self.lock:
                    try:
                        value, dxl_comm_result, dxl_error = func(*args, **kwargs)
                    except IndexError:
                        continue # Look like com error produce index error in the DXL SDK.

                #self._busy.clear()
                if dxl_comm_result != COMM_SUCCESS:
                    self.log(f"COM ERR: ({dxl_id=}) {self.packet_handler.getTxRxResult(dxl_comm_result)}")
                    continue
                if dxl_error != 0:
                    self.log(f"DXL ERR: ({dxl_id=}) {self.packet_handler.getRxPacketError(dxl_error)}")
                    continue
                return value

    return wrapper


class U2D2(Base):

    def __init__(self, owner, **kwargs):
        super().__init__(owner=owner)
        
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        # self._path = Path("dxl manager")
        self._was_open = None
        self._context_depth = 0
        self._is_open = False
        
        # port_name = kwargs["communication port"]
        self._lock = Lock()
        self._baudrate = 57600
        self._port_handler = None # port_handler(port_name)
        self._packet_handler = None #PacketHandler(2.0)
        self._com_port = ComPort(owner=self)
        self[self.com_port.name] = self.com_port
        self._dxl_list = [
            DXL(owner=self, dynamixel_id=i+1)
            for i
            in range(9)
            ]
        for dxl in self.dxl_list:
            self[dxl.name] = dxl
        self._dxls = {}
        self._dxls[f"female1"] = self._dxl_list[0]
        self._dxls[f"female2"] = self._dxl_list[2]
        self._dxls[f"female3"] = self._dxl_list[4]
        self._dxls[f"male1"] = self._dxl_list[6]
        self._dxls[f"male2"] = self._dxl_list[7]
        self._dxls[f"bar"] = self._dxl_list[8]

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
            self._was_open = self.is_open
            if not self._was_open:
                self.open()
        self._context_depth += 1

    def __exit__(self, *args, **kwargs):
        self._context_depth -= 1
        if self._context_depth == 0 and not self._was_open:
            self.close()

    @property
    def packet_handler(self):
        if self._packet_handler is None:
            # self._packet_handler = VirtualPacketHandler(owner=self.virtual_hardware)
            if not self.is_simulated:
                self._packet_handler = PacketHandler(2.0)
            else:
                self._packet_handler = self.colloquy.virtual_hardware.u2d2_packet_handler 

        return self._packet_handler

    @property
    def virtual_hardware(self):
        return self.colloquy.virtual_hardware

    @property
    def lock(self):
        return self._lock

    @property
    def dxl_list(self):
        return self._dxl_list

    @property
    def dxls(self):
        return self._dxls

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def html(self):
        return self._html

    @property
    def port_name(self):
        return self.com_port.value

    @property
    def com_port(self):
        return self._com_port

    @property
    def is_open(self):
        return self._is_open

    @property
    def port_handler(self):
        return self._port_handler

    @property
    def name(self):
        return "u2d2"

    @handle_error
    def read_1_byte(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        return value, dxl_comm_result, dxl_error

    @handle_error
    def write_1_byte(self, dxl_id, register_address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

    @handle_error
    def read_4_bytes(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        return value, dxl_comm_result, dxl_error

    @handle_error
    def write_4_bytes(self, dxl_id, register_address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

    @handle_error
    def _read_2_bytes_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read2ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        return value, dxl_comm_result, dxl_error

    @handle_error
    def _write_2_bytes_at(self, dxl_id, register_address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

    def close(self):
        self.port_handler.closePort()
        self._is_open = False

    def open(self):
        assert self.port_name
            
        if not self.is_simulated:
            self._port_handler = PortHandler(self.port_name)
        else:
            if self._port_handler is not None:
                assert not self._port_handler.is_open
            self._port_handler = self.colloquy.virtual_hardware.u2d2_port_handler(self.port_name)
        # PortHandler(self.port_name)
        self.port_handler.setBaudRate(self._baudrate)
        self._is_open = True

    # def _get_com_ports(self):
        # return [
            # port.device
            # for port
            # in serial.tools.list_ports.comports()]

    # def _set_com_port(self, com_port, **kwargs):
        # com_port = com_port[0]
        # self.port_handler.closePort()
        # self.port_handler = self._classes["port_handler"](com_port)

        # self.hardware.params["dynamixel network"]["communication port"] = com_port
        # self.hardware.save()

    # def _add_html_com(self, ):
        # doc, tag, text = self.html_doc.tagtext()
        # # with tag("h3"):
            # # text("DXL manager:")

        # port_list = self._get_com_ports()

        # with tag("form", method="post"):
            # with tag("label", **{"id": "dxl_manager/com_port"}):
                # text(f"DXL com port:")

            # with tag("select", id="dxl_manager/com_port", name="com_port"):
                # for port in port_list:
                    # kwargs = {}
                    # if port == self.port_handler.getPortName():
                        # kwargs["selected"] = True
                    # with tag('option', value=port, **kwargs):
                        # text(port)

            # with tag("button", name="action", value="dxl_manager/com_port/set"):
                # text(f"set.")

            # self.hardware.actions["dxl_manager/com_port/set"] = self._set_com_port

        # # yield doc.read().encode()