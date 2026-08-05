"""Unit tests for colloquy.virtual_hardware.virtual_packet_handler.
VirtualPacketHandler - the simulated stand-in for dynamixel_sdk's
PacketHandler, used by U2D2.read_1_byte/write_1_byte/etc. (see
handle_error in colloquy/hardware/u2d2/__init__.py) when running
simulated. It owns 10 VirtualDXL registers (ids 0-9) and dispatches
register reads/writes to them by register address.

Constructing it is safe: __init__ only builds VirtualDXL children (no
serial/thread side effects - a VirtualDXL only spawns a thread from
set("goal position", ...) with torque enabled, which write4ByteTxRx can
trigger, so those cases keep goal == current position to keep the spawned
thread's run() a no-op).
"""
import pytest
from dynamixel_sdk import COMM_SUCCESS

from colloquy.virtual_hardware.virtual_packet_handler import VirtualPacketHandler

TORQUE_ENABLED = 64
DRIVE_MODE = 10
OPERATING_MODE = 11
PROFILE_VELOCITY = 112
PROFILE_ACCELERATION = 108
POSITION = 132
GOAL_POSITION = 116
TEMPERATURE = 146


def make_handler(stub_factory):
    return VirtualPacketHandler(owner=stub_factory())


def test_name(stub_factory):
    handler = make_handler(stub_factory)

    assert handler.name == "virtual dxl packet handler"


def test_builds_ten_virtual_dxls_indexed_by_id(stub_factory):
    handler = make_handler(stub_factory)

    assert len(handler.dxls) == 10
    assert [dxl._dxl_id for dxl in handler.dxls] == list(range(10))


def test_write_and_read_1_byte_round_trip(stub_factory):
    handler = make_handler(stub_factory)

    result = handler.write1ByteTxRx(None, dxl_id=2, register_address=TORQUE_ENABLED, value=1)

    assert result == (COMM_SUCCESS, 0)
    assert handler.read1ByteTxRx(None, dxl_id=2, register_address=TORQUE_ENABLED) == (
        1,
        COMM_SUCCESS,
        0,
    )


def test_write_1_byte_rejects_a_4_byte_register(stub_factory):
    handler = make_handler(stub_factory)

    with pytest.raises(AssertionError):
        handler.write1ByteTxRx(None, dxl_id=2, register_address=POSITION, value=1)


def test_write_and_read_4_bytes_round_trip(stub_factory):
    handler = make_handler(stub_factory)

    result = handler.write4ByteTxRx(
        None, dxl_id=3, register_address=PROFILE_VELOCITY, value=200
    )

    assert result == (COMM_SUCCESS, 0)
    assert handler.read4ByteTxRx(None, dxl_id=3, register_address=PROFILE_VELOCITY) == (
        200,
        COMM_SUCCESS,
        0,
    )


def test_read_4_bytes_rejects_a_1_byte_register(stub_factory):
    handler = make_handler(stub_factory)

    with pytest.raises(AssertionError):
        handler.read4ByteTxRx(None, dxl_id=3, register_address=TEMPERATURE)


def test_write_goal_position_without_torque_raises_not_implemented(stub_factory):
    handler = make_handler(stub_factory)

    with pytest.raises(NotImplementedError):
        handler.write4ByteTxRx(None, dxl_id=4, register_address=GOAL_POSITION, value=500)


def test_write_goal_position_with_torque_enabled_and_no_move_needed(stub_factory):
    handler = make_handler(stub_factory)
    handler.write1ByteTxRx(None, dxl_id=5, register_address=TORQUE_ENABLED, value=1)

    handler.write4ByteTxRx(None, dxl_id=5, register_address=GOAL_POSITION, value=0)
    handler.dxls[5]._thread.join(timeout=1)

    assert handler.read4ByteTxRx(None, dxl_id=5, register_address=GOAL_POSITION) == (
        0,
        COMM_SUCCESS,
        0,
    )


def test_get_tx_rx_result_and_get_rx_packet_error_are_not_implemented(stub_factory):
    handler = make_handler(stub_factory)

    with pytest.raises(NotImplementedError):
        handler.getTxRxResult(0)

    with pytest.raises(NotImplementedError):
        handler.getRxPacketError(0)
