"""Unit tests for colloquy.hardware.male.drives.Drives.

`Drives` is a `BaseThread` that owns two `Drive` children (O and P). Its
__init__ constructs those `Drive` objects directly (no thread start, no
serial/filesystem I/O): `Drive.__init__` only reads `owner.owner.name`
(the male's name) and `owner.params["drive start values"][<male
name>]["O"/"P"]` off the owner chain, then builds an inert `Input` child.
None of that touches hardware, so constructing the real `Drives` object
against a `stub_factory`-built male stub (exposing `.name` and `.params`,
plus a `.neopixels` tree deep enough for `Drives.update()`) is safe and
simpler than the unbound-double pattern - mirrors
pytest_tests/female/test_drives.py's approach for the sibling class.

`which_is_frustated()` is the standout target: a real branching state
machine over `self.o_drive`/`self.p_drive` (each only needing
`.value`/`.is_satisfied`/`.is_frustated`/`.lock`). We use the `fake_drive`
(`FakeDrive`) fixture to build doubles with controlled values and call
`Drives.which_is_frustated()` **unbound** against a `stub_factory(o_drive=...,
p_drive=...)` double - simpler than fighting the real `Drive` class's
time-based `_satisfaction_lim`/`_frustrated_lim` derivation.
"""
from colloquy.hardware.male.drives import Drives


def make_drives(stub_factory, name="male1", o_start=12, p_start=34):
    owner = stub_factory(
        name=name,
        params={"drive start values": {name: {"O": o_start, "P": p_start}}},
        neopixels=stub_factory(
            up_ring=stub_factory(brightness=stub_factory(value=None)),
            o_drive_level=stub_factory(brightness=stub_factory(value=None)),
            p_drive_level=stub_factory(brightness=stub_factory(value=None)),
        ),
    )
    return Drives(owner=owner)


# --- construction / naming / registration -----------------------------


def test_drives_name(stub_factory):
    drives = make_drives(stub_factory, name="male1")

    assert drives.name == "male1's drives"


def test_o_drive_and_p_drive_names_and_start_values(stub_factory):
    drives = make_drives(stub_factory, name="male1", o_start=12, p_start=34)

    assert drives.o_drive.name == "male1's O drive"
    assert drives.p_drive.name == "male1's P drive"
    assert drives.o_drive.value == 12
    assert drives.p_drive.value == 34


def test_iter_yields_o_drive_then_p_drive(stub_factory):
    drives = make_drives(stub_factory)

    assert list(drives) == [drives.o_drive, drives.p_drive]


def test_drives_registers_children_by_name(stub_factory):
    # __init__ registers via `self[self.o_drive.name] = self.o_drive` (the
    # full display name, e.g. "male1's O drive") - NOT "O"/"P" literals.
    drives = make_drives(stub_factory)

    assert drives[drives.o_drive.name] is drives.o_drive
    assert drives[drives.p_drive.name] is drives.p_drive


def test_snapshot_children_keys_and_values(stub_factory):
    drives = make_drives(stub_factory)

    children = drives.snapshot_children

    assert set(children.keys()) == {
        "set O=0 and P=100",
        "set O=100 and P=0",
        "set O=30 and P=30",
        "set O=100 and P=100",
        drives.o_drive.name,
        drives.p_drive.name,
    }
    assert children[drives.o_drive.name] is drives.o_drive
    assert children[drives.p_drive.name] is drives.p_drive
    assert children["set O=0 and P=100"] == drives.set_o_to_0_p_to_100
    assert children["set O=100 and P=0"] == drives.set_p_to_0_o_to_100
    assert children["set O=30 and P=30"] == drives.set_o_and_p_to_30
    assert children["set O=100 and P=100"] == drives.set_o_and_p_to_100


# --- the set_* convenience commands + update() -------------------------


def test_set_o_to_0_p_to_100_writes_values_and_updates_neopixels(stub_factory):
    drives = make_drives(stub_factory)
    owner = drives.owner

    drives.set_o_to_0_p_to_100()

    assert drives.o_drive.value == 0
    assert drives.p_drive.value == 100
    assert owner.neopixels.o_drive_level.brightness.value == 0
    assert owner.neopixels.p_drive_level.brightness.value == 100
    assert owner.neopixels.up_ring.brightness.value == 100


def test_set_p_to_0_o_to_100_writes_values_and_updates_neopixels(stub_factory):
    drives = make_drives(stub_factory)
    owner = drives.owner

    drives.set_p_to_0_o_to_100()

    assert drives.o_drive.value == 100
    assert drives.p_drive.value == 0
    assert owner.neopixels.o_drive_level.brightness.value == 100
    assert owner.neopixels.p_drive_level.brightness.value == 0
    assert owner.neopixels.up_ring.brightness.value == 100


def test_set_o_and_p_to_30_writes_values_and_updates_neopixels(stub_factory):
    drives = make_drives(stub_factory)
    owner = drives.owner

    drives.set_o_and_p_to_30()

    assert drives.o_drive.value == 30
    assert drives.p_drive.value == 30
    assert owner.neopixels.o_drive_level.brightness.value == 30
    assert owner.neopixels.p_drive_level.brightness.value == 30
    assert owner.neopixels.up_ring.brightness.value == 30


def test_set_o_and_p_to_100_writes_values_and_updates_neopixels(stub_factory):
    drives = make_drives(stub_factory)
    owner = drives.owner

    drives.set_o_and_p_to_100()

    assert drives.o_drive.value == 100
    assert drives.p_drive.value == 100
    assert owner.neopixels.o_drive_level.brightness.value == 100
    assert owner.neopixels.p_drive_level.brightness.value == 100
    assert owner.neopixels.up_ring.brightness.value == 100


# --- setdown() (does not start/stop any thread; just turns lights off) -


def test_setdown_turns_off_the_three_neopixel_segments(stub_factory):
    calls = []
    owner = stub_factory(
        name="male1",
        params={"drive start values": {"male1": {"O": 0, "P": 0}}},
        neopixels=stub_factory(
            o_drive_level=stub_factory(off=lambda: calls.append("o_drive_level")),
            p_drive_level=stub_factory(off=lambda: calls.append("p_drive_level")),
            up_ring=stub_factory(off=lambda: calls.append("up_ring")),
        ),
    )
    drives = Drives(owner=owner)

    drives.setdown()

    assert set(calls) == {"o_drive_level", "p_drive_level", "up_ring"}


# --- which_is_frustated() state machine ---------------------------------


def test_which_is_frustated_both_satisfied_returns_empty_tuple(stub_factory, fake_drive):
    fake = stub_factory(o_drive=fake_drive(10), p_drive=fake_drive(20))

    assert Drives.which_is_frustated(fake) == tuple()


def test_which_is_frustated_both_frustrated_returns_both(stub_factory, fake_drive):
    fake = stub_factory(o_drive=fake_drive(200), p_drive=fake_drive(250))

    assert Drives.which_is_frustated(fake) == ("O", "P")


def test_which_is_frustated_o_greater_returns_o_only(stub_factory, fake_drive):
    # Neither both-satisfied (values >= 30) nor both-frustrated (values <= 180).
    fake = stub_factory(o_drive=fake_drive(100), p_drive=fake_drive(50))

    assert Drives.which_is_frustated(fake) == ("O",)


def test_which_is_frustated_p_greater_returns_p_only(stub_factory, fake_drive):
    fake = stub_factory(o_drive=fake_drive(50), p_drive=fake_drive(100))

    assert Drives.which_is_frustated(fake) == ("P",)


def test_which_is_frustated_equal_values_returns_both(stub_factory, fake_drive):
    # Equal, but not caught by the both-satisfied/both-frustrated branches.
    fake = stub_factory(o_drive=fake_drive(100), p_drive=fake_drive(100))

    assert Drives.which_is_frustated(fake) == ("O", "P")


def test_which_is_frustated_one_satisfied_one_not_falls_to_comparison(stub_factory, fake_drive):
    # o is satisfied (value < 30) but p is not, so the "both satisfied"
    # branch doesn't fire; falls through to the value comparison.
    fake = stub_factory(o_drive=fake_drive(10), p_drive=fake_drive(50))

    assert Drives.which_is_frustated(fake) == ("P",)


def test_which_is_frustated_one_frustrated_one_not_falls_to_comparison(stub_factory, fake_drive):
    # o is frustrated (value > 180) but p is not, so the "both frustrated"
    # branch doesn't fire; falls through to the value comparison.
    fake = stub_factory(o_drive=fake_drive(200), p_drive=fake_drive(50))

    assert Drives.which_is_frustated(fake) == ("O",)


# NOTE on the trailing `raise ValueError(...)` in which_is_frustated(): for
# any two real numbers exactly one of (o > p), (p > o), (p == o) is true,
# and those three branches are checked exhaustively above the raise. So the
# ValueError branch is unreachable dead code given the preceding branches -
# we did not write a test attempting to trigger it.


# --- static color dicts (cross-checked against the .ino firmware's GRBW
# arrays referenced in the module-level comment) ------------------------


def test_puce_color():
    # logic35_systems.ino color_puce[4] = {180, 160, 0, 40}; //GRBW//greenish
    assert Drives.puce.fget(None) == dict(red=160, green=180, blue=0, white=40)


def test_orange_color():
    # logic35_systems.ino color_orange[4] = {80, 255, 25, 16}; //GRBW/orangish
    assert Drives.orange.fget(None) == dict(red=255, green=80, blue=25, white=16)


def test_white_color():
    assert Drives.white.fget(None) == dict(red=0, green=0, blue=0, white=255)
