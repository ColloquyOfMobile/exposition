"""Unit tests for colloquy.drivers.female.neopixels.Neopixels.

Neopixels is a thin Base wrapper that owns four Neopixel segments (head,
body_o, body_p, feet). Its __init__ only reads `owner.arduino` and the
segment constructors (Head/BodyO/BodyP/Feet -> Neopixel.__init__) are
inert - they set some initial parameter values but Neopixel.update()
is a no-op until the segment has been turned on/off at least once
(`_on_off_state` starts as None), so no arduino.send() happens during
construction. That makes constructing the real Neopixels object (with a
stub owner) safe and simpler than the unbound-double pattern here.
"""
from colloquy.drivers.female.neopixels import Neopixels
from colloquy.drivers.female.neopixels.head import Head
from colloquy.drivers.female.neopixels.body_o import BodyO
from colloquy.drivers.female.neopixels.body_p import BodyP
from colloquy.drivers.female.neopixels.feet import Feet


def make_neopixels(stub_factory, fake_arduino):
    owner = stub_factory(arduino=fake_arduino())
    return Neopixels(owner=owner)


def test_construction_reads_arduino_from_owner(stub_factory, fake_arduino):
    arduino = fake_arduino()
    owner = stub_factory(arduino=arduino, owners=[])

    neopixels = Neopixels(owner=owner)

    assert neopixels.arduino is arduino
    # arduino.send() must never be called just from constructing segments.
    assert arduino.sent_paths == []


def test_construction_builds_expected_segments(stub_factory, fake_arduino):
    neopixels = make_neopixels(stub_factory, fake_arduino)

    assert isinstance(neopixels.head, Head)
    assert isinstance(neopixels.body_o, BodyO)
    assert isinstance(neopixels.body_p, BodyP)
    assert isinstance(neopixels.feet, Feet)

    assert neopixels.head.name == "head"
    assert neopixels.body_o.name == "bodyO"
    assert neopixels.body_p.name == "bodyP"
    assert neopixels.feet.name == "feet"

    # Segments are also registered as dict-like children for dispatch.
    assert neopixels["head"] is neopixels.head
    assert neopixels["bodyO"] is neopixels.body_o
    assert neopixels["bodyP"] is neopixels.body_p
    assert neopixels["feet"] is neopixels.feet


def test_name_is_neopixels(stub_factory, fake_arduino):
    neopixels = make_neopixels(stub_factory, fake_arduino)

    assert neopixels.name == "neopixels"


def test_iter_yields_segments_in_order(stub_factory, fake_arduino):
    neopixels = make_neopixels(stub_factory, fake_arduino)

    assert list(neopixels) == [
        neopixels.head,
        neopixels.body_o,
        neopixels.body_p,
        neopixels.feet,
    ]


def test_snapshot_children_keys_and_values(stub_factory, fake_arduino):
    neopixels = make_neopixels(stub_factory, fake_arduino)

    children = neopixels.snapshot_children

    assert set(children.keys()) == {"head", "bodyO", "bodyP", "feet"}
    assert children["head"] is neopixels.head
    assert children["bodyO"] is neopixels.body_o
    assert children["bodyP"] is neopixels.body_p
    assert children["feet"] is neopixels.feet
