from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from functools import wraps


def handle_error(func):    
    @wrap(func)
    def wrapper(*args, **kwargs):        
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
            
            
class DynamixelManager:
    def __init__(self, **kwargs):
        port_name = kwargs["communication port"]
        baudrate = kwargs["baudrate"]
        self.port_handler = PortHandler(port_name)
        self.packet_handler = PacketHandler(2.0)  # Using protocol 2.0

        if not self.port_handler.openPort():
            raise IOError(f"Failed to open the port: {port_name}")

        if not self.port_handler.setBaudRate(baudrate):
            raise IOError(f"Failed to set baud rate to: {baudrate}")
    
    @property
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

        return value
    
    @property
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

        return value
    
    @property
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

        return value
    
    @property
    def _write_1_byte_at(self, dxl_id, register_address, value):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")
    
    @property
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
    
    @property
    def _write_4_bytes_at(self, dxl_id, register_address, value):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    def stop(self):
        self.port_handler.closePort()


    def start(self):
        self.port_handler.openPort()