"""Unit tests for colloquy.virtual_drivers.virtual_port_handler.VirtualPortHandler.

Not a Base subclass and has no serial/filesystem side effects - safe to
construct directly. It stands in for dynamixel_sdk.PortHandler in
U2D2.open()/close() when running simulated.
"""
from colloquy.virtual_drivers.virtual_port_handler import VirtualPortHandler


def test_starts_open_with_given_port():
    handler = VirtualPortHandler("COM4")

    assert handler.is_open is True
    assert handler._port == "COM4"


def test_close_port_sets_is_open_false():
    handler = VirtualPortHandler("COM4")

    handler.closePort()

    assert handler.is_open is False


def test_set_baud_rate_write_and_clear_port_are_no_ops():
    handler = VirtualPortHandler("COM4")

    assert handler.setBaudRate(57600) is None
    assert handler.writePort(b"data") is None
    assert handler.clearPort() is None
    assert handler.is_open is True
