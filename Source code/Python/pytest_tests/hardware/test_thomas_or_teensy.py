# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_thomas_or_teensy.py

"""`thomas or teensy` against the copper it claims to keep.

The document's central promise is that the board keeps every connection
the v2 board makes - same nets on the same DSUB pins, same Mega pins for
firmware 4 - and adds Teensy mode beside it. It restates those pinouts
because a board is drawn from a specification, and a restated pinout is
one that can drift. So the tables are parsed here and held to the v2
project's `circuit.json`, its connectivity contract: if either moves,
this is where it should fail, not at a rack with a body that does not
answer.

Like `test_harness.py`, these read checked-in files rather than doubles,
for the same reason: the parse finding them is the thing worth pinning.
"""
import json
import re

import pytest

from colloquy.hardware.electronics import ThomasOrTeensy
from colloquy.hardware.electronics.harness import KICAD

DOCUMENT = ThomasOrTeensy.folder / ThomasOrTeensy.file_name
CIRCUIT = KICAD / "electronic box v2" / "colloquy-control-v2" / "circuit.json"
SKETCH = (
    KICAD.parents[1]
    / "Source code"
    / "Arduino"
    / "colloquy_of_mobiles"
    / "colloquy_of_mobiles.ino"
)

# The three Mega pins the document adds: the reserved link and the MODE sense.
NEW_MEGA_PINS = {"D18", "D19", "D30"}


def _pins(ref):
    for component in json.loads(CIRCUIT.read_text(encoding="utf-8"))["components"]:
        if component["ref"] == ref:
            return {pin: net for pin, net in component["pins"].items() if net}
    raise AssertionError(f"{ref} is not in circuit.json")


def _table(first_header_cell):
    """The markdown table whose header starts with this cell, as rows of
    cells with the backticks taken off."""
    lines = DOCUMENT.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells and cells[0] == first_header_cell:
            header = cells
            rows = []
            for row in lines[index + 2:]:
                if not row.startswith("|"):
                    break
                rows.append(_cells(row))
            return header, rows
    raise AssertionError(f"no table headed {first_header_cell!r}")


def _cells(line):
    if not line.startswith("|"):
        return []
    return [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]


def test_the_files_are_where_this_thinks_they_are():
    """The one failure that would make every test here vacuous."""
    assert DOCUMENT.is_file()
    assert CIRCUIT.is_file()
    assert SKETCH.is_file()


# --- section 2: every connection to the harness is kept ------------------


def test_the_four_body_connectors_are_the_v2_boards_pin_for_pin():
    header, rows = _table("Pin")
    refs = [cell.split()[0] for cell in header[1:]]
    assert refs == ["J5", "J1", "A-J3", "B-J4"]

    for column, ref in enumerate(refs, start=1):
        written = {
            ("0" if row[0] == "shell" else row[0]): row[column] for row in rows
        }
        assert written == _pins(ref), ref


def test_the_other_connectors_are_the_v2_boards_pin_for_pin():
    header, rows = _table("Connector")
    assert header[1:] == ["1", "2", "3", "4", "5", "6"]

    for row in rows:
        ref = row[0].split()[0]
        written = {pin: net for pin, net in zip(header[1:], row[1:]) if net}
        assert written == _pins(ref), ref


def test_only_the_five_line_outs_change_with_the_mode():
    """The document names five conductors whose source changes; they have
    to be every line out on the four connectors, and nothing else."""
    line_outs = {
        (ref, pin)
        for ref in ("J5", "J1", "A-J3", "B-J4")
        for pin, net in _pins(ref).items()
        if net.endswith("/line out")
    }
    named = re.search(
        r"the five `line out`s \(([^)]*)\)", DOCUMENT.read_text(encoding="utf-8")
    )
    assert named is not None
    written = set()
    ref = None
    for part in named.group(1).replace("`", "").split(","):
        tokens = part.split()
        if len(tokens) == 2:
            ref, pin = tokens
        else:
            (pin,) = tokens
        written.add((ref, pin))

    assert written == line_outs
    assert len(line_outs) == 5


# --- section 3: firmware 4 runs unmodified --------------------------------


def test_the_mega_pins_are_the_v2_boards():
    _, rows = _table("Mega pin")
    written = {row[0]: row[1] for row in rows}
    v2 = {
        pin: net for pin, net in _pins("A1").items()
        if not pin.startswith(("5V", "GND"))
    }

    assert written == v2


def test_the_new_mega_pins_are_free_on_v2_and_in_firmware_4():
    """D18, D19 and D30 are added. If the v2 board or firmware 4 used any
    of them, Thomas mode would no longer be the v2 board."""
    assert not NEW_MEGA_PINS & set(_pins("A1"))

    sketch = SKETCH.read_text(encoding="utf-8")
    defined = {
        f"D{number}"
        for number in re.findall(r"^#define \w+ (\d+)\b", sketch, re.MULTILINE)
    }
    assert not NEW_MEGA_PINS & defined
    assert "Serial1" not in sketch

    text = DOCUMENT.read_text(encoding="utf-8")
    for pin in NEW_MEGA_PINS:
        assert f"`{pin}`" in text, pin


# --- section 4a: the Teensy's pins ----------------------------------------


def _teensy_rows():
    _, rows = _table("Teensy pin")
    return [row for row in rows if row[0].isdigit()]


def test_no_teensy_pin_is_used_twice():
    pins = [int(row[0]) for row in _teensy_rows()]

    assert len(pins) == len(set(pins))


def test_the_microphones_are_on_pins_both_adcs_reach_in_body_order():
    """14 to 23 reach either of the Teensy's converters, 24 to 27 only
    one; and 20, 21 and 23 are the I2S clocks."""
    microphones = [
        row for row in _teensy_rows()
        if "microphone" in row[1] and "bench" not in row[1]
    ]
    pins = [int(row[0]) for row in microphones]

    assert pins == [14, 15, 16, 17, 18]
    assert [row[1].split(",")[1].split()[0] for row in microphones] == [
        "female1", "female2", "female3", "male1", "male2",
    ]
    clocks = {
        int(row[0]) for row in _teensy_rows()
        if any(word in row[1] for word in ("LRCLK", "BCLK", "MCLK"))
    }
    assert clocks == {20, 21, 23}
    assert not clocks & set(pins)


def test_the_i2s_data_pins_are_the_six_channel_outputs():
    """`AudioOutputI2SHex` drives pins 7, 32 and 9, in that order."""
    data = [int(row[0]) for row in _teensy_rows() if row[1].startswith("OUT1")]

    assert data[:3] == [7, 32, 9]


@pytest.mark.parametrize("phrase", [
    "one mode for the whole board",
    "**Released is Thomas mode**",
])
def test_the_decisions_are_still_written_down(phrase):
    assert phrase in DOCUMENT.read_text(encoding="utf-8")
