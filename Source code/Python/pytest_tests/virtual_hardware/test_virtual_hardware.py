"""Unit tests for colloquy.virtual_hardware.VirtualHardware - the BaseThread
node owning the simulated Arduino serial connection and Dynamixel packet/
port handlers used throughout colloquy/hardware/ when running simulated
(see U2D2.packet_handler/open() and Arduino's serial connection).

VirtualHardware.__init__ (via BaseThread.__init__) only sets attributes -
no serial/thread side effects - so constructing it against a stub_factory
owner is safe, as long as .start() is never called (see conftest rules).
"""
from colloquy.virtual_hardware import VirtualHardware
from colloquy.virtual_hardware.virtual_packet_handler import VirtualPacketHandler
from colloquy.virtual_hardware.virtual_port_handler import VirtualPortHandler
from colloquy.virtual_hardware.virtual_serial_port import VirtualSerialPort


def make_hardware(stub_factory, **owner_attrs):
    return VirtualHardware(owner=stub_factory(**owner_attrs))


def test_name_is_virtual_hardware(stub_factory):
    hardware = make_hardware(stub_factory)

    assert hardware.name == "virtual hardware"


def test_params_delegates_to_owner(stub_factory):
    hardware = make_hardware(stub_factory, params={"foo": 1})

    assert hardware.params == {"foo": 1}


def test_colloquy_delegates_to_owner(stub_factory):
    marker = object()
    hardware = make_hardware(stub_factory, colloquy=marker)

    assert hardware.colloquy is marker


def test_arduino_serial_port_is_lazily_created_and_cached(stub_factory):
    hardware = make_hardware(stub_factory)

    port = hardware.arduino_serial_port

    assert isinstance(port, VirtualSerialPort)
    assert hardware.arduino_serial_port is port


def test_u2d2_packet_handler_is_lazily_created_and_cached(stub_factory):
    hardware = make_hardware(stub_factory)

    handler = hardware.u2d2_packet_handler

    assert isinstance(handler, VirtualPacketHandler)
    assert hardware.u2d2_packet_handler is handler


def test_dxls_delegates_to_packet_handler(stub_factory):
    hardware = make_hardware(stub_factory)

    assert hardware.dxls is hardware.u2d2_packet_handler.dxls


def test_u2d2_port_handler_returns_a_fresh_virtual_port_handler_each_call(stub_factory):
    hardware = make_hardware(stub_factory)

    handler = hardware.u2d2_port_handler("COM4")

    assert isinstance(handler, VirtualPortHandler)
    assert handler._port == "COM4"
    assert hardware.u2d2_port_handler("COM4") is not handler
