from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    COMM_SUCCESS,
)  # Uses Dynamixel SDK library
from functools import wraps
from threading import Lock
from colloquy.base import Base
from .com_port import ComPort
from colloquy.hardware.dxl import DXL

ATTEMPTS = 5


class U2D2Error(RuntimeError):
    """A servo transaction that never got through, after every retry."""


def handle_error(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        with self:
            dxl_id = args[1]
            last_error = "no attempt completed"
            for i in range(ATTEMPTS):
                with self.lock:
                    try:
                        value, dxl_comm_result, dxl_error = func(*args, **kwargs)
                    except IndexError:
                        # Look like com error produce index error in the DXL SDK.
                        last_error = "IndexError from the DXL SDK"
                        continue

                # self._busy.clear()
                if dxl_comm_result != COMM_SUCCESS:
                    last_error = self.packet_handler.getTxRxResult(dxl_comm_result)
                    self.log(f"COM ERR: ({dxl_id=}) {last_error}")
                    continue
                if dxl_error != 0:
                    last_error = self.packet_handler.getRxPacketError(dxl_error)
                    self.log(f"DXL ERR: ({dxl_id=}) {last_error}")
                    continue

                return value

            # Every attempt failed. This used to fall off the end and
            # return None, which is the worst of both worlds: a read then
            # hands None to arithmetic somewhere else entirely (is_moving
            # does abs(None - goal)), and a write is simply dropped, so a
            # body that never moves looks mechanical rather than
            # electrical. Say so here, where the id and the register are
            # still known - the thread framework catches it, records it
            # against the thread that asked, and shows it in the web UI.
            message = (
                f"{func.__name__} gave up on dxl {dxl_id} after {ATTEMPTS} "
                f"attempts: {last_error}"
            )
            self.log(message)
            raise U2D2Error(message)

    return wrapper


class U2D2(Base):
    def __init__(self, owner, **kwargs):
        super().__init__(owner=owner)

        # self._path = Path("dxl manager")
        self._was_open = None
        self._context_depth = 0
        self._is_open = False

        # port_name = kwargs["communication port"]
        self._lock = Lock()
        self._baudrate = 57600
        self._port_handler = None  # port_handler(port_name)
        self._packet_handler = None  # PacketHandler(2.0)
        self._com_port = ComPort(owner=self)
        self[self.com_port.name] = self.com_port
        self._dxl_list = [DXL(owner=self, dynamixel_id=i + 1) for i in range(9)]
        for dxl in self.dxl_list:
            self[dxl.name] = dxl
        self._dxls = {}
        self._dxls["female1"] = self._dxl_list[0]
        self._dxls["female2"] = self._dxl_list[2]
        self._dxls["female3"] = self._dxl_list[4]
        self._dxls["male1"] = self._dxl_list[6]
        self._dxls["male2"] = self._dxl_list[7]
        self._dxls["bar"] = self._dxl_list[8]
        # The gaps between the females: ids 2, 4 and 6 have always been
        # built here and mapped to nothing. They are the mirrors, one per
        # female.
        self._dxls["mirror1"] = self._dxl_list[1]
        self._dxls["mirror2"] = self._dxl_list[3]
        self._dxls["mirror3"] = self._dxl_list[5]

    def __enter__(self):
        with self.lock:
            if self._context_depth == 0:
                self._was_open = self.is_open
                if not self._was_open:
                    self.open()
            self._context_depth += 1

    def __exit__(self, *args, **kwargs):
        with self.lock:
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
                self._packet_handler = (
                    self.colloquy.virtual_hardware.u2d2_packet_handler
                )

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
            self.port_handler, dxl_id, register_address, value
        )

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
            self.port_handler, dxl_id, register_address, value
        )

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
            self.port_handler, dxl_id, register_address, value
        )

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
            self._port_handler = self.colloquy.virtual_hardware.u2d2_port_handler(
                self.port_name
            )
        # PortHandler(self.port_name)
        self.port_handler.setBaudRate(self._baudrate)
        self._is_open = True
