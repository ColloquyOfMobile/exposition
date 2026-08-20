"""Unit tests for colloquy.virtual_hardware.virtual_serial_port.
VirtualSerialPort - the simulated stand-in for the Arduino's pyserial
connection, used by Arduino.send() (colloquy/hardware/arduino/__init__.py)
when running simulated. It replays the .ino sketch's `path == "..."`
branches (read from Source code/Arduino/colloquy_of_mobiles/
colloquy_of_mobiles.ino, located relative to the module rather than to the
working directory), and fans a write() out to per-path handlers that mutate
an in-memory state dict or compute a simulated light-sensor reading.

Replies are bytes shaped like the firmware's own `Serial.println(response)`:
a decimal number for a light sensor, an empty line for everything else.
"""
import json
from types import SimpleNamespace

import pytest

CRLF = bytes([13, 10])  # what Serial.println() terminates a reply with

from colloquy.hardware.angle.conversion import REDUCTIONS, degrees_to_ticks
from colloquy.virtual_hardware.virtual_serial_port import VirtualSerialPort

PARAMS = {
    "photosensor_threashold": 300,
    # Degrees of the body, per kind, since the reductions differ (see
    # colloquy/params.py). Deliberately not the real values: what matters
    # here is that each kind uses its own.
    "near origin threshold": {"female": 10, "male": 30, "bar": 10},
    "female1": {"dxl origin": 1000},
    "female2": {"dxl origin": 1100},
    "female3": {"dxl origin": 1200},
    "male1": {"dxl origin": 2000},
    "male2": {"dxl origin": 3000},
    "bar": {
        # Deliberately non-zero: the bar's own origin is where its angles
        # are measured from, and was once left out of the simulated
        # comparison while being included in the real goal position. Far
        # enough out to be detectable if it is dropped again.
        "dxl origin": 1500,
        # Degrees of the bar, as in the real params file.
        "interaction_origins": {
            "male1": {"female1": 15, "female2": 20, "female3": 25},
            "male2": {"female1": 30, "female2": 35, "female3": 40},
        },
    },
}


def meeting_point(male, female):
    """Where the bar's servo sits to put `male` in front of `female` - what
    Bar.set_male_in_front_of_female() ends up writing, its own origin plus
    the meeting angle through the bar's 1:3 reduction."""
    return PARAMS["bar"]["dxl origin"] + degrees_to_ticks(
        PARAMS["bar"]["interaction_origins"][male][female], REDUCTIONS["bar"]
    )


def reading(port):
    """A sensor reply, back as the number the firmware sent."""
    return int(port.readline())


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
    assert port.readline().strip() == b"Hello!"


def test_close_sets_is_open_false(stub_factory):
    port = make_port(stub_factory)
    port._port = "COM4"
    port.open()

    port.close()

    assert port.is_open is False


def test_readline_returns_an_empty_line_when_nothing_queued(stub_factory):
    # What the firmware answers to a write: PixelGroup.fill() returns "",
    # and Serial.println() adds the CRLF.
    port = make_port(stub_factory)

    assert port.readline() == CRLF


def test_write_set_female_neopixel_updates_state(stub_factory):
    port = make_port(stub_factory)
    port._is_open = True

    port.write(json.dumps({"path": "f2/head", "r": 1, "g": 2, "b": 3, "w": 4}).encode())

    assert port._states["female2"]["head"] == {"r": 1, "g": 2, "b": 3, "w": 4}
    # _set_female_neopixel returns None, so the queued reply falls back
    # to the firmware's own empty acknowledgement rather than staying None.
    assert port.readline() == CRLF


def test_write_set_male_neopixel_updates_state(stub_factory):
    port = make_port(stub_factory)
    port._is_open = True

    port.write(json.dumps({"path": "m1/ring", "r": 0, "g": 0, "b": 0, "w": 255}).encode())

    assert port._states["male1"]["ring"] == {"r": 0, "g": 0, "b": 0, "w": 255}


def test_unmodelled_sensor_reads_dark_relative_to_the_threshold(stub_factory):
    # A male's sensors have no model behind them. The reading must still be
    # below the threshold *whatever the threshold is* - it used to be the
    # bare constant 10, which silently becomes "lit" if the threshold is
    # ever tuned below it.
    port = make_port(stub_factory)
    port._is_open = True

    port.write(json.dumps({"path": "m1/light sensor/a"}).encode())

    assert reading(port) < PARAMS["photosensor_threashold"]


def test_replies_are_always_bytes(stub_factory):
    # LightSensor.read() does int(response), which happens to accept a
    # bare int too - but pyserial hands back bytes, and anything that
    # decodes or strips a reply must behave the same simulated or not.
    port = make_port(stub_factory)
    port._is_open = True

    port.write(json.dumps({"path": "m1/light sensor/a"}).encode())
    sensor_reply = port.readline()

    port.write(json.dumps({"path": "m1/ring", "r": 0, "g": 0, "b": 0, "w": 1}).encode())
    write_reply = port.readline()

    assert isinstance(sensor_reply, bytes) and sensor_reply.endswith(CRLF)
    assert isinstance(write_reply, bytes)


def test_read_f1_sensor_below_threashold_when_female_not_near_origin(stub_factory):
    dxls = {1: SimpleNamespace(position=999999)}
    port = make_port(stub_factory, dxls=dxls)
    port._is_open = True

    port.write(json.dumps({"path": "f1/light sensor"}).encode())

    assert reading(port) < PARAMS["photosensor_threashold"]


def test_read_f1_sensor_below_threashold_when_no_male_nearby(stub_factory):
    dxls = {
        1: SimpleNamespace(position=PARAMS["female1"]["dxl origin"]),
        7: SimpleNamespace(position=999999),
        8: SimpleNamespace(position=999999),
        9: SimpleNamespace(position=meeting_point("male1", "female1")),
    }
    port = make_port(stub_factory, dxls=dxls)
    port._is_open = True

    port.write(json.dumps({"path": "f1/light sensor"}).encode())

    assert reading(port) < PARAMS["photosensor_threashold"]


def test_read_f1_sensor_above_threashold_when_facing_lit_male(stub_factory):
    dxls = {
        1: SimpleNamespace(position=PARAMS["female1"]["dxl origin"]),
        7: SimpleNamespace(position=PARAMS["male1"]["dxl origin"]),
        8: SimpleNamespace(position=999999),
        9: SimpleNamespace(position=meeting_point("male1", "female1")),
    }
    port = make_port(stub_factory, dxls=dxls)
    port._is_open = True
    port._states["male1"]["ring"]["w"] = 255

    port.write(json.dumps({"path": "f1/light sensor"}).encode())

    assert reading(port) > PARAMS["photosensor_threashold"]


def test_read_f1_sensor_below_threashold_when_facing_unlit_male(stub_factory):
    dxls = {
        1: SimpleNamespace(position=PARAMS["female1"]["dxl origin"]),
        7: SimpleNamespace(position=PARAMS["male1"]["dxl origin"]),
        8: SimpleNamespace(position=999999),
        9: SimpleNamespace(position=meeting_point("male1", "female1")),
    }
    port = make_port(stub_factory, dxls=dxls)
    port._is_open = True

    port.write(json.dumps({"path": "f1/light sensor"}).encode())

    assert reading(port) < PARAMS["photosensor_threashold"]


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
        9: SimpleNamespace(position=meeting_point("male1", "female1")),
    }
    port = make_port(stub_factory, dxls=dxls)

    assert port._get_nearest_male(female="female1") == "male1"


def _facing(female, male, bar_at=None):
    """Both bodies facing forward, bar wherever asked (their meeting point
    by default)."""
    from colloquy.virtual_hardware.virtual_serial_port import (
        FEMALE_DXL_IDS,
        MALE_DXL_IDS,
    )

    dxls = {
        FEMALE_DXL_IDS[female]: SimpleNamespace(position=PARAMS[female]["dxl origin"]),
        MALE_DXL_IDS["male1"]: SimpleNamespace(position=PARAMS["male1"]["dxl origin"]),
        MALE_DXL_IDS["male2"]: SimpleNamespace(position=PARAMS["male2"]["dxl origin"]),
        9: SimpleNamespace(
            position=meeting_point(male, female) if bar_at is None else bar_at
        ),
    }
    return dxls


def test_get_nearest_male_finds_male2_even_when_male1_also_faces_forward(stub_factory):
    # Regression: the loop used to stop at the first male facing his own
    # origin. With male1 forward too, a bar parked exactly at male2's
    # meeting point still reported nobody, so male2 could never be seen.
    port = make_port(stub_factory, dxls=_facing("female1", "male2"))

    assert port._get_nearest_male(female="female1") == "male2"


def test_meeting_points_are_measured_from_the_bars_own_origin(stub_factory):
    # The bar's angle is measured from its origin; a servo position equal
    # to the meeting angle's units alone only agreed while that origin
    # was 0.
    offset_only = degrees_to_ticks(
        PARAMS["bar"]["interaction_origins"]["male1"]["female1"], REDUCTIONS["bar"]
    )
    port = make_port(stub_factory, dxls=_facing("female1", "male1", bar_at=offset_only))

    assert port._get_nearest_male(female="female1") is None

    port = make_port(stub_factory, dxls=_facing("female1", "male1"))

    assert port._get_nearest_male(female="female1") == "male1"


def test_every_female_has_a_sensor_model_not_just_female1(stub_factory):
    # female2/female3 used to fall through to the unmodelled-sensor
    # constant, so nothing involving them could produce a reading.
    for female in ("female1", "female2", "female3"):
        port = make_port(stub_factory, dxls=_facing(female, "male2"))
        port._is_open = True
        port._states["male2"]["ring"]["w"] = 255

        port.write(json.dumps({"path": f"f{female[-1]}/light sensor"}).encode())

        assert reading(port) > PARAMS["photosensor_threashold"], female


def test_readings_are_repeatable_across_runs(stub_factory):
    # Sensor noise is seeded, so the same simulated situation gives the
    # same numbers twice - a decode experiment can be replayed.
    def read_once():
        port = make_port(stub_factory, dxls=_facing("female1", "male1"))
        port._is_open = True
        port._states["male1"]["ring"]["w"] = 255
        port.write(json.dumps({"path": "f1/light sensor"}).encode())
        return reading(port)

    assert read_once() == read_once()


def test_a_round_trip_costs_time_by_default(stub_factory, monkeypatch):
    # Replying instantly is not neutral: ReadPattern bins its samples by
    # wall clock, so a latency-free simulator hands it 2-3x more samples
    # per pattern step than the rig ever will.
    import colloquy.virtual_hardware.virtual_serial_port as module

    slept = []
    monkeypatch.setattr(module, "sleep", slept.append)
    port = make_port(stub_factory)
    port._is_open = True

    assert port.latency == module.REALISTIC_LATENCY

    port.write(json.dumps({"path": "m1/light sensor/a"}).encode())

    assert slept == [module.REALISTIC_LATENCY]


def test_latency_can_be_turned_off(stub_factory, monkeypatch):
    import colloquy.virtual_hardware.virtual_serial_port as module

    slept = []
    monkeypatch.setattr(module, "sleep", slept.append)
    port = make_port(stub_factory)
    port._is_open = True
    port.latency = 0

    port.write(json.dumps({"path": "m1/light sensor/a"}).encode())

    assert slept == []
