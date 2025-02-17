from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from functools import wraps


def handle_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        for i in range(3):
            value, dxl_comm_result, dxl_error = func(*args, **kwargs)
            if dxl_comm_result != COMM_SUCCESS:
                print(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
                continue
            if dxl_error != 0:
                print(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")
                continue
            return value
        if dxl_comm_result != COMM_SUCCESS:
            raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        if dxl_error != 0:
            raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    return wrapper


class VirtualPortHandler:
    def __init__(self, port_name):
        pass

    def openPort(self):
        return True

    def setBaudRate(self, baudrate):
        return True

    def closePort(self):
        return

class VirtualPacketHandler:
    def __init__(self, protocol):
        pass

    def write1ByteTxRx(self, port_handler, dxl_id, register_address, value):
        return COMM_SUCCESS, 0

    def write4ByteTxRx(self, port_handler, dxl_id, register_address, value):
        return COMM_SUCCESS, 0

    def getTxRxResult(self, result):
        raise NotImplementedError
        return None

    def getRxPacketError(self, result):
        raise NotImplementedError
        return None

class VirtualDynamixelManager:

    _classes = {
        "port_handler": VirtualPortHandler,
        "packet_handler": VirtualPacketHandler,
    }

    def __init__(self, **kwargs):
        port_name = kwargs["communication port"]
        baudrate = kwargs["baudrate"]
        self.port_handler = self._classes["port_handler"](port_name)
        self.packet_handler = self._classes["packet_handler"](2.0)  # Using protocol 2.0

        if not self.port_handler.openPort():
            raise IOError(f"Failed to open the port: {port_name}")

        if not self.port_handler.setBaudRate(baudrate):
            raise IOError(f"Failed to set baud rate to: {baudrate}")

    @handle_error
    def _read_1_byte_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        return value, dxl_comm_result, dxl_error

    @handle_error
    def _read_2_bytes_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read2ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        return value, dxl_comm_result, dxl_error

    @handle_error
    def _read_4_bytes_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        return value, dxl_comm_result, dxl_error

    @handle_error
    def _write_1_byte_at(self, dxl_id, register_address, value):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    @handle_error
    def _write_2_bytes_at(self, dxl_id, register_address, value):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        return None, dxl_comm_result, dxl_error

    @handle_error
    def _write_4_bytes_at(self, dxl_id, register_address, value):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    def stop(self):
        self.port_handler.closePort()


    def start(self):
        self.port_handler.openPort()

