"""Unit tests for colloquy.hardware.male.search.blink.Blink.

Blink.__init__ only builds `self._name` from `owner.male.name` and calls
BaseThread.__init__, which is inert (no serial/filesystem/thread access -
see colloquy/base_thread/__init__.py). That makes constructing the real
Blink object against a stub_factory-built owner (exposing `.male`) safe,
so it is used throughout instead of the unbound-double pattern.

We never call .start()/.start_command()/.stop_command() - setup()/loop()/
setdown() are invoked directly as plain methods, per the suite's rules.

What Blink does (colloquy/light_pattern_timing.py has the provenance):
he sends his ten bits once, 0.2s each, and then holds the ring dark for
the rest of a 4.35s cycle. Time is not slept through here and not read
from the wall either: the `clock` fixture replaces the module's own
`time` with one the test advances by hand. Reading the real clock made
these tests fail whenever the machine stalled for longer than the
distance to the next bit boundary - rare, but a suite that is run after
every change cannot afford a test that fails for no reason.
"""
import pytest

from colloquy.hardware.male.search.blink import Blink
from colloquy.light_pattern_timing import (
    BIT_DURATION,
    BITS,
    BURST_DURATION,
    CYCLE_DURATION,
)


class FakeClock:
    """A stand-in for time(): reads the same until a test moves it."""

    def __init__(self, now=1_000_000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr("colloquy.hardware.male.search.blink.time", fake)
    return fake


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
        pattern = (1, 0, 0, 1, 1, 0, 1, 0, 0, 1)
    ring = FakeRing()
    reads = []

    def get_blink_pattern():
        reads.append(pattern)
        return pattern

    male = stub_factory(
        name=male_name, get_blink_pattern=get_blink_pattern, ring=ring
    )
    owner = stub_factory(male=male)
    blink = Blink(owner=owner)
    return blink, ring, reads


def at(blink, clock, seconds_into_cycle):
    """Move the clock to `seconds_into_cycle` after this burst started."""
    clock.now = blink._cycle_start + seconds_into_cycle


def test_name_is_derived_from_owner_male_name(stub_factory):
    blink, _ring, _reads = make_blink(stub_factory, male_name="male2")

    assert blink.name == "blink male2"


def test_male_property_reads_owner_male(stub_factory):
    blink, _ring, _reads = make_blink(stub_factory)

    assert blink.male is blink.owner.male


def test_white_is_a_pure_white_dict(stub_factory):
    blink, _ring, _reads = make_blink(stub_factory)

    assert blink.white == dict(red=0, green=0, blue=0, white=255)


def test_snapshot_children_is_empty(stub_factory):
    blink, _ring, _reads = make_blink(stub_factory)

    assert blink.snapshot_children == {}


def test_setup_sets_ring_to_white_and_arms_an_immediate_burst(stub_factory):
    blink, ring, _reads = make_blink(stub_factory)
    blink._cycle_start = 123.0

    blink.setup()

    assert ring.color == dict(red=0, green=0, blue=0, white=255)
    assert ring.on_calls == 1
    assert ring.off_calls == 0
    # Zero, not now: the first loop() must find a whole cycle elapsed and
    # open with a burst rather than with 2.35s of silence.
    assert blink._cycle_start == 0


def test_setdown_turns_ring_off(stub_factory):
    blink, ring, _reads = make_blink(stub_factory)

    blink.setdown()

    assert ring.off_calls == 1
    assert ring.on_calls == 0


def test_first_loop_after_setup_starts_a_burst_on_the_first_bit(stub_factory, clock):
    pattern = (1, 0, 0, 1, 1, 0, 1, 0, 0, 1)
    blink, ring, reads = make_blink(stub_factory, pattern=pattern)
    blink.setup()

    blink.loop()

    assert ring.set_calls == [pattern[0]]
    assert len(reads) == 1
    assert blink._cycle_start == clock.now


def test_each_bit_is_shown_in_order_at_its_own_moment(stub_factory, clock):
    pattern = (1, 0, 0, 1, 1, 0, 1, 0, 0, 1)
    blink, ring, _reads = make_blink(stub_factory, pattern=pattern)
    blink.setup()
    blink.loop()

    # Sample the middle of every bit's window rather than its edge, so the
    # test says which bit is meant to be lit, not how float division
    # rounds on the boundary.
    for index in range(1, BITS):
        at(blink, clock, (index + 0.5) * BIT_DURATION)
        blink.loop()

    # set() is only called on a change, so what the ring receives is the
    # pattern with its runs collapsed - the sequence, not one call per bit.
    expected = [bit for i, bit in enumerate(pattern) if i == 0 or bit != pattern[i - 1]]
    assert ring.set_calls == expected


def test_nothing_is_sent_while_a_bit_is_still_the_same(stub_factory, clock):
    blink, ring, _reads = make_blink(stub_factory, pattern=(1,) * BITS)
    blink.setup()
    blink.loop()

    for _ in range(20):
        blink.loop()

    # An all-ones pattern is one lit bit repeated: one write, not 21. Every
    # ring write is a serial round trip, and the thread ticks ~20x a bit.
    assert ring.set_calls == [1]


def test_the_ring_goes_dark_for_the_gap_after_the_last_bit(stub_factory, clock):
    blink, ring, _reads = make_blink(stub_factory, pattern=(1,) * BITS)
    blink.setup()
    blink.loop()

    at(blink, clock, BURST_DURATION + 0.01)
    blink.loop()
    at(blink, clock, CYCLE_DURATION - 0.01)
    blink.loop()

    # Dark once, and still dark just before the next burst is due: the
    # silence is what frames the pattern for whoever is reading it.
    assert ring.set_calls == [1, 0]


def test_a_new_burst_starts_after_a_whole_cycle_and_re_reads_the_pattern(
    stub_factory, clock
):
    blink, ring, reads = make_blink(stub_factory, pattern=(1,) * BITS)
    blink.setup()
    blink.loop()
    at(blink, clock, BURST_DURATION + 0.01)
    blink.loop()

    # Just past the boundary rather than exactly on it: "a whole cycle has
    # elapsed" is the condition under test, and floating point makes
    # landing precisely on the line a coin toss.
    at(blink, clock, CYCLE_DURATION + 0.01)
    blink.loop()

    assert ring.set_calls == [1, 0, 1]
    # Re-read at the boundary and only there, so a drive state that changes
    # mid-burst can't splice two patterns into one unreadable message.
    assert len(reads) == 2
    assert blink._cycle_start == clock.now


def test_a_drive_state_changing_mid_burst_is_not_picked_up_until_the_next_one(
    stub_factory, clock
):
    ring = FakeRing()
    wanted = [(1, 1, 1, 1, 1, 1, 1, 1, 1, 1)]
    male = stub_factory(
        name="male1", get_blink_pattern=lambda: wanted[0], ring=ring
    )
    blink = Blink(owner=stub_factory(male=male))
    blink.setup()
    blink.loop()

    wanted[0] = (0,) * BITS  # he changes his mind halfway through
    at(blink, clock, BURST_DURATION / 2)
    blink.loop()

    assert ring.set_calls == [1]
    assert blink.pattern == (1,) * BITS

    at(blink, clock, CYCLE_DURATION + 0.01)
    blink.loop()

    assert blink.pattern == (0,) * BITS


def test_the_pattern_is_never_mutated(stub_factory, clock):
    pattern = (1, 0, 0, 1, 1, 0, 1, 0, 0, 1)
    blink, _ring, _reads = make_blink(stub_factory, pattern=pattern)
    blink.setup()
    blink.loop()

    for index in range(1, BITS):
        at(blink, clock, (index + 0.5) * BIT_DURATION)
        blink.loop()

    # It used to be a deque rotated one step per bit, which is why the
    # phase of what a female saw was anybody's guess.
    assert pattern == (1, 0, 0, 1, 1, 0, 1, 0, 0, 1)
    assert blink.pattern == pattern


def test_is_transmitting_is_true_during_the_burst_and_false_in_the_gap(
    stub_factory, clock
):
    blink, _ring, _reads = make_blink(stub_factory)
    blink.setup()
    blink.loop()

    assert blink.is_transmitting is True

    at(blink, clock, BURST_DURATION + 0.01)

    assert blink.is_transmitting is False
