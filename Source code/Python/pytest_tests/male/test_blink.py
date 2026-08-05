"""Unit tests for colloquy.hardware.male.search.blink.Blink.

Blink.__init__ only builds `self._name` from `owner.male.name` and calls
BaseThread.__init__, which is inert (no serial/filesystem/thread access -
see colloquy/base_thread/__init__.py). That makes constructing the real
Blink object against a stub_factory-built owner (exposing `.male`) safe,
so it is used throughout instead of the unbound-double pattern.

We never call .start()/.start_command()/.stop_command() - setup()/loop()/
setdown() are invoked directly as plain methods, per the suite's rules.
"""
from collections import deque

from colloquy.hardware.male.search.blink import Blink


class FakeRing:
    """Duck-typed stand-in for the male's ring Neopixel segment - records
    .on()/.off()/.set(value) calls and lets .color be read back."""

    def __init__(self):
        self.color = None
        self.on_calls = 0
        self.off_calls = 0
        self.set_calls = []

    def on(self):
        self.on_calls += 1

    def off(self):
        self.off_calls += 1

    def set(self, value):
        self.set_calls.append(value)


def make_blink(stub_factory, pattern=None, male_name="male1"):
    if pattern is None:
        pattern = deque([1, 0, 0, 1, 1, 0, 1, 0, 0, 1])
    ring = FakeRing()
    male = stub_factory(name=male_name, get_blink_pattern=lambda: pattern, ring=ring)
    owner = stub_factory(male=male)
    blink = Blink(owner=owner)
    return blink, ring, pattern


def test_name_is_derived_from_owner_male_name(stub_factory):
    blink, _ring, _pattern = make_blink(stub_factory, male_name="male2")

    assert blink.name == "blink male2"


def test_male_property_reads_owner_male(stub_factory):
    blink, _ring, _pattern = make_blink(stub_factory)

    assert blink.male is blink.owner.male


def test_white_is_a_pure_white_dict(stub_factory):
    blink, _ring, _pattern = make_blink(stub_factory)

    assert blink.white == dict(red=0, green=0, blue=0, white=255)


def test_snapshot_children_is_empty(stub_factory):
    blink, _ring, _pattern = make_blink(stub_factory)

    assert blink.snapshot_children == {}


def test_setup_sets_ring_to_white_and_turns_it_on(stub_factory):
    blink, ring, _pattern = make_blink(stub_factory)
    blink._timestamp = 123.0

    blink.setup()

    assert ring.color == dict(red=0, green=0, blue=0, white=255)
    assert ring.on_calls == 1
    assert ring.off_calls == 0
    # setup() also resets the timestamp so the next loop() advances.
    assert blink._timestamp == 0


def test_setdown_turns_ring_off(stub_factory):
    blink, ring, _pattern = make_blink(stub_factory)

    blink.setdown()

    assert ring.off_calls == 1
    assert ring.on_calls == 0


def test_loop_before_blink_step_elapsed_is_a_no_op(stub_factory):
    from time import time

    blink, ring, pattern = make_blink(stub_factory)
    before = list(pattern)
    # Just set, so (time() - _timestamp) is ~0, well under _blink_step (0.5s).
    blink._timestamp = time()

    blink.loop()

    assert ring.set_calls == []
    assert list(pattern) == before


def test_loop_after_blink_step_elapsed_pops_rotates_and_sets(stub_factory):
    blink, ring, pattern = make_blink(stub_factory)

    # Force the elapsed-time gate open every call by resetting _timestamp
    # to 0 right before each loop() (time() - 0 is always > _blink_step).
    for _ in range(5):
        before = list(pattern)
        expected_popped = before[0]
        expected_rotated = before[1:] + [before[0]]

        blink._timestamp = 0
        blink.loop()

        # popleft() -> append() -> ring.set(value), in that exact order,
        # and only the popped bit (the old front) is what gets set().
        assert ring.set_calls[-1] == expected_popped
        assert list(pattern) == expected_rotated


def test_loop_updates_timestamp_after_advancing(stub_factory):
    from time import time

    blink, _ring, _pattern = make_blink(stub_factory)
    blink._timestamp = 0

    before = time()
    blink.loop()
    after = time()

    assert before <= blink._timestamp <= after
