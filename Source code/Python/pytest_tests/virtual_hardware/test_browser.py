"""Unit tests for the web-UI view of the simulated hardware
(colloquy.virtual_hardware.browser) - the read-only window onto what the
simulated arduino and servos currently hold.
"""
from types import SimpleNamespace

from colloquy.virtual_hardware.browser import BodyStateNode, ServosNode


def make_owner(stub_factory, states=None, dxls=None):
    return stub_factory(states=states or {}, dxls=dxls or {})


def leaves(node, path=()):
    """The value leaves a page render would show for an opened node."""
    return {
        key: value["value"]
        for key, value in node._snapshot_if_opened(path).items()
        if isinstance(value, dict) and "value" in value
    }


def test_pixels_are_shown_channel_by_channel(stub_factory):
    states = {"female1": {"head": {"r": 0, "g": 0, "b": 255, "w": 0}}}
    node = BodyStateNode(owner=make_owner(stub_factory, states), body_name="female1")

    assert leaves(node) == {"head": "r0 g0 b255 w0"}


def test_an_all_zero_pixel_is_called_dark(stub_factory):
    # The whole point of this view: a segment commanded to black looks
    # exactly like a lit one from outside the simulator. The read-pattern
    # test shipped for days sending its readout LEDs plain black.
    states = {"female1": {"head": {"r": 0, "g": 0, "b": 0, "w": 0}}}
    node = BodyStateNode(owner=make_owner(stub_factory, states), body_name="female1")

    assert leaves(node) == {"head": "r0 g0 b0 w0 - dark"}


def test_a_scalar_sensor_reading_is_shown_as_is(stub_factory):
    states = {"female1": {"light sensor": 412}}
    node = BodyStateNode(owner=make_owner(stub_factory, states), body_name="female1")

    assert leaves(node) == {"light sensor": 412}


def test_a_males_four_sensors_are_shown_together(stub_factory):
    states = {"male1": {"light sensor": {"a": 1, "b": 2, "c": 3, "d": 4}}}
    node = BodyStateNode(owner=make_owner(stub_factory, states), body_name="male1")

    assert leaves(node) == {"light sensor": "a: 1, b: 2, c: 3, d: 4"}


def _dxl(position, goal, torque=1):
    values = {"position": position, "goal position": goal, "torque enabled": torque}
    return SimpleNamespace(get=values.__getitem__)


def test_servos_are_listed_by_body_name(stub_factory):
    dxls = {i: _dxl(0, 0) for i in range(10)}
    node = ServosNode(owner=make_owner(stub_factory, dxls=dxls))

    assert list(leaves(node)) == [
        "female1",
        "female2",
        "female3",
        "male1",
        "male2",
        "bar",
    ]


def test_a_servo_shows_position_goal_and_torque(stub_factory):
    dxls = {i: _dxl(0, 0) for i in range(10)}
    dxls[9] = _dxl(position=100, goal=100, torque=0)
    node = ServosNode(owner=make_owner(stub_factory, dxls=dxls))

    assert leaves(node)["bar"] == "position 100, goal 100, torque off"


def test_a_servo_on_its_way_says_so_and_by_how_far(stub_factory):
    dxls = {i: _dxl(0, 0) for i in range(10)}
    dxls[9] = _dxl(position=100, goal=2100)
    node = ServosNode(owner=make_owner(stub_factory, dxls=dxls))

    assert leaves(node)["bar"] == "position 100, goal 2100, torque on, moving (+2000)"
