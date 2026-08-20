"""Unit tests for colloquy.hardware.male.light_sensor.LightSensor.

LightSensor.__init__ only asserts `letter in "abcd"`, sets `self._letter`
and calls Base.__init__, which is inert (no serial/filesystem access -
see colloquy/base.py). That makes constructing the real LightSensor
object against a stub_factory-built owner safe, so it is used throughout
instead of the unbound-double pattern.
"""
import pytest
from pathlib import Path

from colloquy.hardware.male.light_sensor import LightSensor


def make_light_sensor(stub_factory, letter="a", **owner_attrs):
    owner_attrs.setdefault("id_number", 1)
    owner = stub_factory(**owner_attrs)
    return LightSensor(owner=owner, letter=letter)


def test_invalid_letter_raises(stub_factory):
    owner = stub_factory(id_number=1)

    with pytest.raises(AssertionError):
        LightSensor(owner=owner, letter="e")


def test_valid_letters_construct_fine(stub_factory):
    for letter in "abcd":
        owner = stub_factory(id_number=1)
        sensor = LightSensor(owner=owner, letter=letter)
        assert sensor.name == f"light sensor {letter}"


def test_male_property_reads_owner(stub_factory):
    owner = stub_factory(id_number=1)
    sensor = LightSensor(owner=owner, letter="b")

    assert sensor.male is owner


def test_name_is_light_sensor_plus_letter(stub_factory):
    sensor = make_light_sensor(stub_factory, letter="c")

    assert sensor.name == "light sensor c"


def test_threashold_reads_params_photosensor_threashold(stub_factory):
    owner = stub_factory(id_number=1, params={"photosensor_threashold": 42})
    sensor = LightSensor(owner=owner, letter="a")

    assert sensor.threashold == 42


def test_arduino_path_builds_expected_path(stub_factory):
    sensor = make_light_sensor(stub_factory, letter="c", id_number=2)

    assert sensor.arduino_path == Path("m2/light sensor/c")


def test_arduino_property_reads_owner_arduino(stub_factory, fake_arduino):
    arduino = fake_arduino()
    sensor = make_light_sensor(stub_factory, arduino=arduino)

    assert sensor.arduino is arduino


def test_is_simulated_true_when_super_is_simulated(stub_factory, monkeypatch):
    # Base.is_simulated (what `super().is_simulated` resolves to) is True
    # whenever socket.gethostname() != "Colloquy-Laptop" - force that
    # branch and confirm it short-circuits regardless of params.
    monkeypatch.setattr("colloquy.machines.socket.gethostname", lambda: "some-other-machine")
    owner = stub_factory(id_number=1, params={"emulate light sensor": False})
    sensor = LightSensor(owner=owner, letter="a")

    assert sensor.is_simulated is True


def test_is_simulated_falls_back_to_params_when_super_is_not_simulated(
    stub_factory, monkeypatch
):
    # Force super().is_simulated to False (hostname == "Colloquy-Laptop")
    # so the property must fall through to params["emulate light sensor"].
    monkeypatch.setattr("colloquy.machines.socket.gethostname", lambda: "Colloquy-Laptop")
    owner = stub_factory(id_number=1, params={"emulate light sensor": True})
    sensor = LightSensor(owner=owner, letter="a")

    assert sensor.is_simulated is True


def test_is_simulated_false_when_super_is_not_simulated_and_not_emulating(
    stub_factory, monkeypatch
):
    monkeypatch.setattr("colloquy.machines.socket.gethostname", lambda: "Colloquy-Laptop")
    owner = stub_factory(id_number=1, params={"emulate light sensor": False})
    sensor = LightSensor(owner=owner, letter="a")

    assert sensor.is_simulated is False


def test_read_sends_arduino_path_and_returns_int(stub_factory, fake_arduino):
    arduino = fake_arduino(response="17")
    sensor = make_light_sensor(stub_factory, letter="d", id_number=3, arduino=arduino)

    value = sensor.read()

    assert value == 17
    assert arduino.sent_paths == [Path("m3/light sensor/d")]


def test_read_as_bool_true_when_above_threashold(stub_factory, fake_arduino):
    arduino = fake_arduino(response="100")
    sensor = make_light_sensor(
        stub_factory,
        arduino=arduino,
        params={"photosensor_threashold": 50},
    )

    assert sensor.read_as_bool() is True


def test_read_as_bool_false_when_at_or_below_threashold(stub_factory, fake_arduino):
    arduino = fake_arduino(response="50")
    sensor = make_light_sensor(
        stub_factory,
        arduino=arduino,
        params={"photosensor_threashold": 50},
    )

    # read() > threashold, so equal values must read as False.
    assert sensor.read_as_bool() is False


def test_snapshot_children_is_empty(stub_factory):
    sensor = make_light_sensor(stub_factory)

    assert sensor.snapshot_children == {}
