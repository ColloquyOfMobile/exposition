"""Unit tests for colloquy.virtual_hardware.virtual_serial_port.
VirtualSerialPort - the simulated stand-in for the Arduino's pyserial
connection, used by Arduino.send() (colloquy/hardware/arduino/__init__.py)
when running simulated. It replays the .ino sketch's `path == "..."`
branches (read from Source code/Arduino/colloquy_of_mobiles/
colloquy_of_mobiles.ino - these tests must run with the repo root as cwd,
same requirement as the rest of the suite, e.g. local/params.json), and
fans a write() out to per-path handlers that mutate an in-memory state
dict or compute a simulated light-sensor reading.
"""
import json
from types import SimpleNamespace

import pytest

from colloquy.virtual_hardware.virtual_serial_port import VirtualSerialPort

PARAMS = {
    "photosensor_threashold": 300,
    "near_origin_threashold": 400,
    "female1": {"dxl origin": 1000},
    "male1": {"dxl origin": 2000},
    "male2": {"dxl origin": 3000},
    "bar": {
        "dxl origin": 0,
        "interaction_origins": {
            "male1": {"female1": 500},
            "male2": {"female1": 900},
        },
    },
}


def make_port(stub_factory, dxls=None, params=None):
    colloquy = stub_factory(params=PARAMS if params is None else params)
    owner = stub_factory(colloquy=colloquy, dxls=dxls or {})
    return VirtualSerialPort(owner=owner)


def test_load_possible_paths_reads_them_from_the_arduino_sketch(stub_factory):
    port = make_port(stub_factory)

    assert "f1/head" in port._possible_paths
    assert "m1/ring" in port._possible_paths
    assert "m1/light sensor/a" in port._possible_paths


def test_write_before_open_raises(stub_factory):
    port = make_port(stub_factory)

    with pytest.raises(AssertionError):
        port.write(json.dumps({"path": "f1/head", "r": 1, "g": 0, "b": 0, "w": 0}).encode())


def test_write_unknown_path_raises(stub_factory):
    port = make_port(stub_factory)
    port._is_open = True

    with pytest.raises(AssertionError):
        port.write(json.dumps({"path": "does/not-exist"}).encode())


def test_open_sets_is_open_and_queues_hello(stub_factory):
    port = make_port(stub_factory)
    port._port = "COM4"

    port.open()

    assert port.is_open is True
    assert port.readline() == b"Hello!"


def test_close_sets_is_open_false(stub_factory):
    port = make_port(stub_factory)
    port._port = "COM4"
    port.open()

    port.close()

    assert port.is_open is False


def test_readline_returns_success_status_when_nothing_queued(stub_factory):
    port = make_port(stub_factory)

    assert port.readline() == b'{"status": "success"}'


def test_write_set_female_neopixel_updates_state(stub_factory):
    port = make_port(stub_factory)
    port._is_open = True

    port.write(json.dumps({"path": "f2/head", "r": 1, "g": 2, "b": 3, "w": 4}).encode())

    assert port._states["female2"]["head"] == {"r": 1, "g": 2, "b": 3, "w": 4}
    # _set_female_neopixel returns None, so the queued reply falls back
    # to the generic ack rather than staying None.
    assert port.readline() == b'{"status": "success"}'


def test_write_set_male_neopixel_updates_state(stub_factory):
    port = make_port(stub_factory)
    port._is_open = True

    port.write(json.dumps({"path": "m1/ring", "r": 0, "g": 0, "b": 0, "w": 255}).encode())

    assert port._states["male1"]["ring"] == {"r": 0, "g": 0, "b": 0, "w": 255}


def test_write_generic_light_sensor_path_returns_constant(stub_factory):
    port = make_port(stub_factory)
    port._is_open = True

    port.write(json.dumps({"path": "m1/light sensor/a"}).encode())

    assert port.readline() == 10


def test_read_f1_sensor_below_threashold_when_female_not_near_origin(stub_factory):
    dxls = {1: SimpleNamespace(position=999999)}
    port = make_port(stub_factory, dxls=dxls)
    port._is_open = True

    port.write(json.dumps({"path": "f1/light sensor"}).encode())

    assert port.readline() < PARAMS["photosensor_threashold"]


def test_read_f1_sensor_below_threashold_when_no_male_nearby(stub_factory):
    dxls = {
        1: SimpleNamespace(position=PARAMS["female1"]["dxl origin"]),
        7: SimpleNamespace(position=999999),
        8: SimpleNamespace(position=999999),
    }
    port = make_port(stub_factory, dxls=dxls)
    port._is_open = True

    port.write(json.dumps({"path": "f1/light sensor"}).encode())

    assert port.readline() < PARAMS["photosensor_threashold"]


def test_read_f1_sensor_above_threashold_when_facing_lit_male(stub_factory):
    dxls = {
        1: SimpleNamespace(position=PARAMS["female1"]["dxl origin"]),
        7: SimpleNamespace(position=PARAMS["male1"]["dxl origin"]),
        8: SimpleNamespace(position=999999),
        9: SimpleNamespace(position=PARAMS["bar"]["interaction_origins"]["male1"]["female1"]),
    }
    port = make_port(stub_factory, dxls=dxls)
    port._is_open = True
    port._states["male1"]["ring"]["w"] = 255

    port.write(json.dumps({"path": "f1/light sensor"}).encode())

    assert port.readline() > PARAMS["photosensor_threashold"]


def test_read_f1_sensor_below_threashold_when_facing_unlit_male(stub_factory):
    dxls = {
        1: SimpleNamespace(position=PARAMS["female1"]["dxl origin"]),
        7: SimpleNamespace(position=PARAMS["male1"]["dxl origin"]),
        8: SimpleNamespace(position=999999),
        9: SimpleNamespace(position=PARAMS["bar"]["interaction_origins"]["male1"]["female1"]),
    }
    port = make_port(stub_factory, dxls=dxls)
    port._is_open = True

    port.write(json.dumps({"path": "f1/light sensor"}).encode())

    assert port.readline() < PARAMS["photosensor_threashold"]


def test_port_and_name_reflect_the_configured_port(stub_factory):
    port = make_port(stub_factory)

    assert port.port is None
    assert port.name is None

    port.port = "COM4"

    assert port.port == "COM4"
    assert port.name == "COM4"


def test_get_nearest_male_returns_none_when_bar_not_at_the_interaction_origin(stub_factory):
    dxls = {
        7: SimpleNamespace(position=PARAMS["male1"]["dxl origin"]),
        8: SimpleNamespace(position=999999),
        9: SimpleNamespace(position=999999),
    }
    port = make_port(stub_factory, dxls=dxls)

    assert port._get_nearest_male(female="female1") is None


def test_get_nearest_male_uses_male_dxl_ids_7_and_8(stub_factory):
    # Regression test for a mismatched-index bug: male1/male2 are
    # dxl_list[6]/dxl_list[7] in U2D2._dxls (colloquy/hardware/u2d2/
    # __init__.py), i.e. dynamixel ids 7/8 (dxl_list[i] has
    # dynamixel_id=i+1). _get_nearest_male used to look at ids 6/7
    # instead, so "male1" always inspected the wrong, unrelated servo.
    dxls = {
        7: SimpleNamespace(position=PARAMS["male1"]["dxl origin"]),
        8: SimpleNamespace(position=999999),
        9: SimpleNamespace(position=PARAMS["bar"]["interaction_origins"]["male1"]["female1"]),
    }
    port = make_port(stub_factory, dxls=dxls)

    assert port._get_nearest_male(female="female1") == "male1"
