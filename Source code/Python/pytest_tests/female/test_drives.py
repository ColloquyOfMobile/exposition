"""Unit tests for colloquy.drivers.female.drives.

`Drives` is a `BaseThread` that owns two `Drive` children (O and P). Its
__init__ constructs those `Drive` objects directly (no thread start, no
serial/filesystem I/O): `Drive.__init__` only reads `owner.owner.name` (the
female's name, for its own display name) and
`owner.params["drive start values"][<female name>]["O"/"P"]` (the starting
drive values) off the owner chain, then builds an inert `Input` child.
None of that touches hardware, so constructing the real `Drives` object
against a `stub_factory`-built female stub (exposing `.name` and
`.params`) is safe and simpler than the unbound-double pattern.

`build_map_to_compensate_brightness_to_human_eye()` is a pure module-level
function (no I/O at all) and is tested directly.
"""
from types import SimpleNamespace

from colloquy.drivers.female.drives import (
    Drives,
    build_map_to_compensate_brightness_to_human_eye,
)


def make_drives(stub_factory, name="female1"):
    owner = stub_factory(
        name=name,
        params={"drive start values": {name: {"O": 12, "P": 34}}},
    )
    return Drives(owner=owner)


def test_build_map_has_101_entries():
    the_map = build_map_to_compensate_brightness_to_human_eye()

    assert len(the_map) == 101


def test_build_map_is_monotonically_non_decreasing():
    the_map = build_map_to_compensate_brightness_to_human_eye()

    assert all(the_map[i] <= the_map[i + 1] for i in range(len(the_map) - 1))


def test_build_map_first_and_last_values():
    the_map = build_map_to_compensate_brightness_to_human_eye()

    # First raw sample is 4/255; round(4 * 100 / 255) == 2.
    assert the_map[0] == 2
    # Last raw sample is 255/255 == full scale -> 100.
    assert the_map[-1] == 100


def test_compensate_brightness_for_human_eye_uses_the_map(stub_factory):
    drives = make_drives(stub_factory)

    expected_map = build_map_to_compensate_brightness_to_human_eye()

    assert drives.compensate_brightness_for_human_eye(0) == expected_map[0]
    assert drives.compensate_brightness_for_human_eye(50) == expected_map[50]
    assert drives.compensate_brightness_for_human_eye(100) == expected_map[100]


def test_puce_color(stub_factory):
    # logic35_systems.ino color_puce[4] = {180, 160, 0, 40}; //GRBW//greenish
    drives = make_drives(stub_factory)

    assert drives.puce == dict(red=160, green=180, blue=0, white=40)


def test_orange_color(stub_factory):
    # logic35_systems.ino color_orange[4] = {80, 255, 25, 16}; //GRBW/orangish
    drives = make_drives(stub_factory)

    assert drives.orange == dict(red=255, green=80, blue=25, white=16)


def test_white_color(stub_factory):
    drives = make_drives(stub_factory)

    assert drives.white == dict(red=0, green=0, blue=0, white=255)


def test_iter_yields_o_drive_then_p_drive(stub_factory):
    drives = make_drives(stub_factory)

    assert list(drives) == [drives.o_drive, drives.p_drive]


def test_o_drive_and_p_drive_names_and_start_values(stub_factory):
    drives = make_drives(stub_factory, name="female1")

    assert drives.o_drive.name == "female1's O drive"
    assert drives.p_drive.name == "female1's P drive"
    assert drives.o_drive.value == 12
    assert drives.p_drive.value == 34


def test_drives_registers_children_by_name(stub_factory):
    drives = make_drives(stub_factory)

    # Drives.__init__ registers children under o_drive.name/p_drive.name
    # (e.g. "female1's O drive"), not the bare "O"/"P" drive names.
    assert drives[drives.o_drive.name] is drives.o_drive
    assert drives[drives.p_drive.name] is drives.p_drive


def test_drives_name_is_drives(stub_factory):
    drives = make_drives(stub_factory)

    assert drives.name == "drives"


def test_snapshot_children_keys_and_values(stub_factory):
    drives = make_drives(stub_factory)

    children = drives.snapshot_children

    # Her two appetites, and what they look like from the room: every
    # thread that declares scenarios carries them here, which is the dict
    # the page walks.
    assert set(children.keys()) == {
        drives.o_drive.name,
        drives.p_drive.name,
        "scenarios",
    }
    assert children[drives.o_drive.name] is drives.o_drive
    assert children[drives.p_drive.name] is drives.p_drive
    assert children["scenarios"].names == ("female-appetite-lights",)


# --- an appetite stays a whole number ------------------------------------


def lit_female(stub_factory, name="female1"):
    """Her drives, with just enough of a body behind them that
    `Drives.update()` - which every change to an appetite calls - can
    write the brightnesses it wants to write."""

    def group():
        return SimpleNamespace(
            brightness=SimpleNamespace(value=None), color=None, on=lambda: None
        )

    owner = stub_factory(
        name=name,
        params={"drive start values": {name: {"O": 44, "P": 44}}},
        neopixels=SimpleNamespace(
            head=group(), body_o=group(), body_p=group(), feet=group()
        ),
    )
    return Drives(owner=owner)


def test_a_fractional_decrement_leaves_the_drive_an_integer(stub_factory):
    """params' "reinforcement decrement" is female2's 12.5, and it is the
    one number in a drive that does not come out of drive/__init__.py.

    `commit()` has always run its value through int(); `decrease()` did
    not, so one round of female2's reinforcement made her appetite a float
    and the `update()` at the end of that very call indexed the gamma
    table with it. It raised `tuple indices must be integers`, which
    killed her reinforcement thread, stopped `drivers` and ended the whole
    exposition about a minute into a run.
    """
    drives = lit_female(stub_factory)

    drives.o_drive.decrease(12.5)

    assert drives.o_drive.value == 31
    assert isinstance(drives.o_drive.value, int)


def test_a_fractional_decrement_does_not_break_the_body_lights(stub_factory):
    drives = lit_female(stub_factory)
    the_map = build_map_to_compensate_brightness_to_human_eye()

    drives.p_drive.decrease(12.5)

    # The brightness the update() inside decrease() actually wrote.
    assert drives.owner.neopixels.body_p.brightness.value == the_map[31]


def test_a_decrement_never_takes_an_appetite_below_zero(stub_factory):
    drives = lit_female(stub_factory)

    drives.o_drive.decrease(99.5)

    assert drives.o_drive.value == 0
