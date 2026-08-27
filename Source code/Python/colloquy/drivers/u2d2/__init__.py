from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    COMM_SUCCESS,
)  # Uses Dynamixel SDK library
from functools import wraps
from threading import Lock
from colloquy.base import Base
from .com_port import ComPort
from colloquy.drivers.dxl import DXL

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
        # Latched by the first open() that succeeds and never cleared.
        # Not the same question as is_open, which flickers - see
        # ever_opened below.
        self._ever_opened = False
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
            # self._packet_handler = VirtualPacketHandler(owner=self.virtual_drivers)
            if not self.is_simulated:
                self._packet_handler = PacketHandler(2.0)
            else:
                self._packet_handler = (
                    self.colloquy.virtual_drivers.u2d2_packet_handler
                )

        return self._packet_handler

    @property
    def virtual_drivers(self):
        return self.colloquy.virtual_drivers

    @property
    def lock(self):
        return self._lock

    @property
    def dxl_list(self):
        return self._dxl_list

    @property
    def ever_opened(self):
        """Did an open() on this bus ever succeed this run?

        Asked instead of the port name by everything that wants to know
        whether there are servos to talk to. The name is set by `main.py`
        *before* the port is opened, so a bus whose open() raised has a
        name and no link - which used to be indistinguishable, back when
        a failed open ended the process and the question never came up.
        Now that startup survives one (see colloquy/startup/), a shutdown
        that trusted the name would set off to home five bodies over a bus
        that was never there.

        Not `is_open`, which flickers: `__enter__`/`__exit__` open and
        close the port around each transaction.
        """
        return self._ever_opened

    @property
    def dxls(self):
        return self._dxls

    # The five bodies and the bar: the six that are wired on every
    # installation, in the order somebody reads them on the page.
    BODY_NAMES = ("female1", "female2", "female3", "male1", "male2", "bar")

    @property
    def body_dxls(self):
        """The six always-wired servos, by name. Mirrors deliberately absent.

        Startup iterates this rather than `dxl_list`, which is all nine.
        Nothing drives a mirror yet and the three of them may not be wired
        at all, so nothing may enable torque on one until somebody asks for
        it by hand - "init hardware" on the dxl node is that asking
        (drivers/mirror/). Initialising all nine contradicted that, and an
        unwired mirror then took the whole process down on the first write
        it did not answer (docs/errors/2026-08-27-01.txt).

        Keyed by body name because "dxl_2" is not what somebody reading a
        startup failure needs to be told.
        """
        return {name: self._dxls[name] for name in self.BODY_NAMES}

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
        """Open the servo bus. Raises U2D2Error if there is no port to open.

        This used to be a bare `assert self.port_name`, which is the least
        useful exception in the file: no message, and the caller learns
        only that *something* was falsy. It also disappears under
        `python -O`, so a check meant to stop a nameless port being opened
        would have stopped nothing.

        Raising a U2D2Error instead is not cosmetic. Every caller that
        already copes with a servo that will not answer copes with this
        one - `Drivers.disable_torque` catches U2D2Error per servo so one
        dead servo cannot leave the other eight powered, and an
        AssertionError went straight past it.

        The port name is not persisted anywhere: `main.py` sets it, in
        `open_the_hardware()`, which is skipped entirely when the main PCB
        is noted as unmounted. So an empty name means the links were never
        opened, and the message says so rather than leaving somebody to
        work it out from a bare traceback.
        """
        if not self.port_name:
            raise U2D2Error(
                "the U2D2's port has not been set, so the servo bus was "
                "never opened. That is what a start with the main PCB "
                "noted as unmounted leaves behind - see hardware > main "
                "pcb - and nothing can move until the board is back and "
                "the process restarted."
            )

        if not self.is_simulated:
            self._port_handler = PortHandler(self.port_name)
        else:
            if self._port_handler is not None:
                assert not self._port_handler.is_open
            self._port_handler = self.colloquy.virtual_drivers.u2d2_port_handler(
                self.port_name
            )
        # PortHandler(self.port_name)
        self.port_handler.setBaudRate(self._baudrate)
        self._is_open = True
        self._ever_opened = True
