from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from functools import wraps
from threading import Lock
from time import sleep
from pathlib import Path
import serial.tools.list_ports
from colloquy.base import Base

# from .logger import Logger
# from .thread_element import ThreadElement


def handle_error(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
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

    _classes = {
        "port_handler": PortHandler,
        "packet_handler": PacketHandler,
    }

    def __init__(self, owner, **kwargs):
        super().__init__(owner=owner)
        # self._path = Path("dxl manager")
        # port_name = kwargs["communication port"]
        # self._baudrate = kwargs["baudrate"]
        # self.port_handler = self._classes["port_handler"](port_name)
        # self.packet_handler = self._classes["packet_handler"](2.0)
        # self.lock = Lock()

    @property
    def name(self):
        return "u2d2"

    @handle_error
    def _read_1_byte_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )

        return value, dxl_comm_result, dxl_error

    @handle_error
    def _read_2_bytes_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read2ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        return value, dxl_comm_result, dxl_error

    @handle_error
    def _read_4_bytes_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        return value, dxl_comm_result, dxl_error

    @handle_error
    def _write_1_byte_at(self, dxl_id, register_address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

    @handle_error
    def _write_2_bytes_at(self, dxl_id, register_address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

    @handle_error
    def _write_4_bytes_at(self, dxl_id, register_address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

    def close(self):
        self.port_handler.closePort()


    def open(self):
        self.port_handler.openPort()
        self.port_handler.setBaudRate(self._baudrate)

    def _get_com_ports(self):
        return [
            port.device
            for port
            in serial.tools.list_ports.comports()]

    def _set_com_port(self, com_port, **kwargs):
        com_port = com_port[0]
        self.port_handler.closePort()
        self.port_handler = self._classes["port_handler"](com_port)

        self.hardware.params["dynamixel network"]["communication port"] = com_port
        self.hardware.save()

    def add_html(self):
        if not self.hardware.is_connected:
            self._add_html_com()

    def _add_html_com(self, ):
        doc, tag, text = self.html_doc.tagtext()
        # with tag("h3"):
            # text("DXL manager:")

        port_list = self._get_com_ports()

        with tag("form", method="post"):
            with tag("label", **{"id": "dxl_manager/com_port"}):
                text(f"DXL com port:")

            with tag("select", id="dxl_manager/com_port", name="com_port"):
                for port in port_list:
                    kwargs = {}
                    if port == self.port_handler.getPortName():
                        kwargs["selected"] = True
                    with tag('option', value=port, **kwargs):
                        text(port)

            with tag("button", name="action", value="dxl_manager/com_port/set"):
                text(f"set.")

            self.hardware.actions["dxl_manager/com_port/set"] = self._set_com_port

        # yield doc.read().encode()