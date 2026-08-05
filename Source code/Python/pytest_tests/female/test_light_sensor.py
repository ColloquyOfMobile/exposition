"""Unit tests for colloquy.hardware.female.light_sensor.LightSensor.

LightSensor.__init__ only sets `self._name` and calls
`BaseThread.__init__`, which is inert (no serial/filesystem access) - see
`colloquy/base_thread/__init__.py`. That makes constructing the real
`LightSensor` object against a `stub_factory`-built owner safe, so it is
used throughout instead of the unbound-double pattern.
"""
from pathlib import Path

from colloquy.hardware.female.light_sensor import LightSensor


def make_light_sensor(stub_factory, **owner_attrs):
    owner_attrs.setdefault("id_number", 1)
    owner = stub_factory(**owner_attrs)
    return LightSensor(name="light sensor", owner=owner)


def test_threashold_reads_params_photosensor_threashold(stub_factory):
    owner = stub_factory(id_number=1, params={"photosensor_threashold": 42})
    light_sensor = LightSensor(name="light sensor", owner=owner)

    assert light_sensor.threashold == 42


def test_is_simulated_true_when_super_is_simulated(stub_factory, monkeypatch):
    # Base.is_simulated (what `super().is_simulated` resolves to, since
    # BaseThread doesn't override it) is True whenever
    # socket.gethostname() != "Colloquy-Laptop" - force that branch and
    # confirm it short-circuits regardless of params.
    monkeypatch.setattr("colloquy.base.socket.gethostname", lambda: "some-other-machine")
    owner = stub_factory(id_number=1, params={"emulate light sensor": False})
    light_sensor = LightSensor(name="light sensor", owner=owner)

    assert light_sensor.is_simulated is True


def test_is_simulated_falls_back_to_params_when_super_is_not_simulated(
    stub_factory, monkeypatch
):
    # Force super().is_simulated to False (hostname == "Colloquy-Laptop")
    # so the property must fall through to params["emulate light sensor"].
    monkeypatch.setattr("colloquy.base.socket.gethostname", lambda: "Colloquy-Laptop")
    owner = stub_factory(id_number=1, params={"emulate light sensor": True})
    light_sensor = LightSensor(name="light sensor", owner=owner)

    assert light_sensor.is_simulated is True


def test_is_simulated_false_when_super_is_not_simulated_and_not_emulating(
    stub_factory, monkeypatch
):
    monkeypatch.setattr("colloquy.base.socket.gethostname", lambda: "Colloquy-Laptop")
    owner = stub_factory(id_number=1, params={"emulate light sensor": False})
    light_sensor = LightSensor(name="light sensor", owner=owner)

    assert light_sensor.is_simulated is False


def test_arduino_path_builds_expected_path(stub_factory):
    light_sensor = make_light_sensor(stub_factory, id_number=2)

    assert light_sensor.arduino_path == Path("f2/light sensor")


def test_arduino_property_reads_owner_arduino(stub_factory, fake_arduino):
    arduino = fake_arduino()
    light_sensor = make_light_sensor(stub_factory, arduino=arduino)

    assert light_sensor.arduino is arduino


def test_read_sends_arduino_path_and_returns_int(stub_factory, fake_arduino):
    arduino = fake_arduino(response="17")
    light_sensor = make_light_sensor(stub_factory, id_number=3, arduino=arduino)

    value = light_sensor.read()

    assert value == 17
    assert arduino.sent_paths == [Path("f3/light sensor")]


def test_read_as_bool_true_when_above_threashold(stub_factory, fake_arduino):
    arduino = fake_arduino(response="100")
    light_sensor = make_light_sensor(
        stub_factory,
        arduino=arduino,
        params={"photosensor_threashold": 50},
    )

    assert light_sensor.read_as_bool() is True


def test_read_as_bool_false_when_at_or_below_threashold(stub_factory, fake_arduino):
    arduino = fake_arduino(response="50")
    light_sensor = make_light_sensor(
        stub_factory,
        arduino=arduino,
        params={"photosensor_threashold": 50},
    )

    # read() > threashold, so equal values must read as False.
    assert light_sensor.read_as_bool() is False
