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
from dynamixel_sdk import COMM_RX_TIMEOUT, COMM_SUCCESS, ERRNUM_RESULT_FAIL

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


def test_write_goal_position_without_torque_is_accepted_and_held(stub_factory):
    # It used to raise NotImplementedError out of the write, killing the
    # calling thread; a real servo holds the value until torque is on.
    handler = make_handler(stub_factory)

    comm, error = handler.write4ByteTxRx(
        None, dxl_id=4, register_address=GOAL_POSITION, value=500
    )

    assert (comm, error) == (COMM_SUCCESS, 0)
    assert handler.dxls[4].get("goal position") == 500
    assert handler.dxls[4].get("position") == 0


def test_write_goal_position_with_torque_enabled_and_no_move_needed(stub_factory):
    handler = make_handler(stub_factory)
    handler.write1ByteTxRx(None, dxl_id=5, register_address=TORQUE_ENABLED, value=1)

    handler.write4ByteTxRx(None, dxl_id=5, register_address=GOAL_POSITION, value=0)

    assert handler.read4ByteTxRx(None, dxl_id=5, register_address=GOAL_POSITION) == (
        0,
        COMM_SUCCESS,
        0,
    )


def test_error_reporting_uses_the_real_sdk_wording(stub_factory):
    # These two used to raise NotImplementedError. handle_error() calls
    # them only once a transaction has already failed, so a simulated bus
    # could never report a failure without crashing on the way to saying
    # so - the reporting path was the broken one.
    handler = make_handler(stub_factory)

    assert "no status packet" in handler.getTxRxResult(COMM_RX_TIMEOUT)
    assert "Failed to process" in handler.getRxPacketError(ERRNUM_RESULT_FAIL)


def test_no_faults_by_default(stub_factory):
    handler = make_handler(stub_factory)

    results = [handler.read4ByteTxRx(None, 1, POSITION) for _ in range(200)]

    assert all(comm == COMM_SUCCESS and error == 0 for _, comm, error in results)
    assert handler.fault_count == 0


def test_comm_errors_are_injected_at_the_configured_rate(stub_factory):
    handler = make_handler(stub_factory)
    handler.set_error_rates(comm=0.5)

    results = [handler.read4ByteTxRx(None, 1, POSITION) for _ in range(400)]
    failed = [r for r in results if r[1] != COMM_SUCCESS]

    # Seeded, so this is exact rather than flaky - roughly half.
    assert 150 < len(failed) < 250
    assert handler.fault_count == len(failed)
    assert all(value == 0 for value, _, _ in failed), "a failed read has no value"


def test_servo_errors_are_reported_as_an_error_bit_not_a_comm_failure(stub_factory):
    handler = make_handler(stub_factory)
    handler.set_error_rates(servo=1.0)

    value, comm, error = handler.read4ByteTxRx(None, 1, POSITION)

    assert comm == COMM_SUCCESS
    assert error == ERRNUM_RESULT_FAIL


def test_a_failed_write_does_not_reach_the_servo(stub_factory):
    # A write that failed must not take effect, or a retry bug would be
    # hidden rather than exposed.
    handler = make_handler(stub_factory)
    handler.write1ByteTxRx(None, 1, TORQUE_ENABLED, 1)
    handler.write4ByteTxRx(None, 1, GOAL_POSITION, 0)
    handler.set_error_rates(comm=1.0)

    comm, error = handler.write4ByteTxRx(None, 1, GOAL_POSITION, 4000)

    assert comm != COMM_SUCCESS
    assert handler.dxls[1].get("goal position") == 0


def test_set_error_rates_resets_the_count(stub_factory):
    handler = make_handler(stub_factory)
    handler.set_error_rates(comm=1.0)
    handler.read4ByteTxRx(None, 1, POSITION)
    assert handler.fault_count == 1

    handler.set_error_rates()

    assert handler.fault_count == 0
    assert (handler.comm_error_rate, handler.servo_error_rate) == (0.0, 0.0)
