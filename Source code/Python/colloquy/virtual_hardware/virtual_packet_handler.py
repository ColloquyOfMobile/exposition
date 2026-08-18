from random import Random

from dynamixel_sdk import (  # Uses Dynamixel SDK library
    COMM_RX_TIMEOUT,
    COMM_SUCCESS,
    ERRNUM_RESULT_FAIL,
    PacketHandler,
)
from pathlib import Path
from colloquy.base import Base
from colloquy.hardware.angle.conversion import as_unsigned
from .virtual_dxl import VirtualDXL

_1_BYTE_REGISTERS = {"drive mode", "temperature", "torque enabled", "operating mode"}
_2_BYTE_REGISTERS = set()
_4_BYTE_REGISTERS = {
    "position",
    "goal position",
    "profile velocity",
    "profile acceleration",
}


class VirtualPacketHandler(Base):
    """Stands in for the SDK's PacketHandler when simulated.

    Can be told to fail: U2D2.handle_error() wraps every servo read and
    write in a five-attempt retry loop, and with a handler that always
    succeeds that loop had never once run its error branch - nor had the
    code that reports what went wrong. See comm_error_rate /
    servo_error_rate, both 0 by default, and the "faults" node in the web
    UI that sets them.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._path = Path("dxl_network")
        self._name = "virtual dxl packet handler"
        self._register_map = {
            64: "torque enabled",
            10: "drive mode",
            11: "operating mode",
            112: "profile velocity",
            108: "profile acceleration",
            132: "position",
            116: "goal position",
            146: "temperature",
        }
        self._dxls = [VirtualDXL(owner=self, dxl_id=i) for i in range(10)]

        # Only for its error-message text, so a simulated failure reads
        # exactly like a real one in the logs.
        self._sdk = PacketHandler(2.0)
        # Seeded: a fault run that can't be repeated is hard to debug.
        self._random = Random(0)
        self.comm_error_rate = 0.0
        self.servo_error_rate = 0.0
        self._fault_count = 0

    @property
    def dxls(self):
        return self._dxls

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def fault_count(self):
        return self._fault_count

    def set_error_rates(self, comm=0.0, servo=0.0):
        self.comm_error_rate = comm
        self.servo_error_rate = servo
        self._fault_count = 0

    def _next_result(self):
        """Whether this transaction fails, and how.

        A comm error is the bus not answering at all (the SDK's
        "There is no status packet!"); a servo error is an answer carrying
        an error bit. handle_error() treats them differently, so both are
        worth being able to provoke.
        """
        if self._random.random() < self.comm_error_rate:
            self._fault_count += 1
            return COMM_RX_TIMEOUT, 0
        if self._random.random() < self.servo_error_rate:
            self._fault_count += 1
            return COMM_SUCCESS, ERRNUM_RESULT_FAIL
        return COMM_SUCCESS, 0

    def _read(self, dxl_id, register_address, expected):
        label = self._register_map[register_address]
        assert label in expected, f"{label=}"
        comm_result, error = self._next_result()
        if comm_result != COMM_SUCCESS or error:
            # What the real SDK hands back when a read fails: no value.
            return 0, comm_result, error
        return self._dxls[dxl_id].get(label), COMM_SUCCESS, 0

    def _write(self, dxl_id, register_address, value, expected):
        label = self._register_map[register_address]
        assert label in expected, f"{label=}, {value=}"
        comm_result, error = self._next_result()
        if comm_result != COMM_SUCCESS or error:
            # A failed transaction doesn't reach the servo, so the value
            # must not be applied either - otherwise a "failed" write that
            # silently took effect would hide retry bugs rather than expose
            # them.
            return comm_result, error
        self._dxls[dxl_id].set(label, value)
        return COMM_SUCCESS, 0

    def write1ByteTxRx(self, port_handler, dxl_id, register_address, value):
        return self._write(dxl_id, register_address, value, _1_BYTE_REGISTERS)

    def read1ByteTxRx(self, port_handler, dxl_id, register_address):
        return self._read(dxl_id, register_address, _1_BYTE_REGISTERS)

    def write2ByteTxRx(self, port_handler, dxl_id, register_address, value):
        return self._write(dxl_id, register_address, value, _2_BYTE_REGISTERS)

    def read2ByteTxRx(self, port_handler, dxl_id, register_address):
        return self._read(dxl_id, register_address, _2_BYTE_REGISTERS)

    def write4ByteTxRx(self, port_handler, dxl_id, register_address, value):
        return self._write(dxl_id, register_address, value, _4_BYTE_REGISTERS)

    def read4ByteTxRx(self, port_handler, dxl_id, register_address):
        value, comm_result, error = self._read(
            dxl_id, register_address, _4_BYTE_REGISTERS
        )
        # The real SDK builds this out of four bytes and hands it over
        # unsigned (DXL_MAKEDWORD, protocol2_packet_handler), so a
        # position below zero comes back as a huge number and something
        # upstream has to convert it. Answering with a tidy Python int
        # here would mean the conversion is only ever exercised on the
        # rig - which is where it was missing.
        return as_unsigned(value), comm_result, error

    def getTxRxResult(self, result):
        # These two used to raise NotImplementedError. handle_error() calls
        # them only when a transaction has failed, so the simulated bus
        # could never report a failure without crashing on the way - the
        # reporting path was the broken one, same as the web UI's error
        # display was.
        return self._sdk.getTxRxResult(result)

    def getRxPacketError(self, error):
        return self._sdk.getRxPacketError(error)
