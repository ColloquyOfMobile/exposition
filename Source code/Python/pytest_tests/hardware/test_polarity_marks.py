"""Every polarized part on a board to make shows + and - beside its pads.

`mark_polarity.py` prints them so that a fitted board can be checked by
eye. This holds the boards to it: a board regenerated without them, a new
LED dropped in unmarked, or a sign beside the wrong pad fails here.

Read out of the `.kicad_pcb` files, like `test_harness.py`. Inside a
footprint both pads and texts sit in the footprint's own coordinates, so
which pad a sign is beside needs no rotation.
"""
import json

import pytest

from colloquy.hardware.electronics import harness
from colloquy.hardware.pcb_files import gerbers

# Footprint name prefix -> the signs of pads 1 and 2; the same table as
# `mark_polarity.py`, which needs KiCad's Python and cannot be imported here.
POLARITY = {"LED_": ("-", "+"), "D_": ("-", "+"), "CP_": ("+", "-")}
SIGNS = {"+", "-"}
# What `assembly-parts.json` says of a part whose pad 1 is each sign.
STATED = {"-": "pad 1 cathode", "+": "pad 1 positive"}
FURTHEST_MM = 4.0

PARTS = json.loads((gerbers.KICAD_FOLDER / "assembly-parts.json").read_text(encoding="utf-8"))["parts"]


def signs_of(name):
    for prefix, signs in POLARITY.items():
        if name.startswith(prefix):
            return signs
    return None


def _value(node, name):
    found = harness.children(node, name)
    return found[0][1:] if found else []


def polarized(board):
    """Each polarized footprint on the board, parsed.

    Only these are parsed: the pure-Python reader takes seconds over the
    whole backplane. KiCad writes every top-level item from a tab-indented
    line to a lone closing one.
    """
    text = board.source_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    start = text.find("\n\t(footprint ")
    while start != -1:
        end = text.index("\n\t)", start) + 3
        name = text[start:start + 200].split('"')[1].split(":")[-1]
        if signs_of(name):
            yield name, harness.parse(text[start:end])
        start = text.find("\n\t(footprint ", end)


def reference(footprint):
    return next(item[2] for item in harness.children(footprint, "property") if item[1] == "Reference")


def marks(footprint):
    found = []
    for item in harness.children(footprint, "fp_text"):
        if item[1] == "user" and item[2] in SIGNS:
            hidden = ["hide", "yes"] in item or any("hide" in effect for effect in harness.children(item, "effects"))
            found.append({"sign": item[2], "at": [float(v) for v in _value(item, "at")],
                          "layer": _value(item, "layer")[0], "hidden": hidden})
    return found


def pads(footprint):
    return {item[1]: [float(v) for v in _value(item, "at")[:2]] for item in harness.children(footprint, "pad")}


def distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


BOARDS = gerbers.load()


@pytest.mark.parametrize("board", BOARDS, ids=lambda b: b.id)
def test_every_polarized_part_shows_each_sign_beside_its_own_pad(board):
    for name, footprint in polarized(board):
        ref = reference(footprint)
        side = _value(footprint, "layer")[0]
        silk = "F.SilkS" if side == "F.Cu" else "B.SilkS"
        found = marks(footprint)
        assert sorted(m["sign"] for m in found) == ["+", "-"], (board.id, ref)
        where = pads(footprint)
        for number, sign in zip(("1", "2"), signs_of(name)):
            (mark,) = [m for m in found if m["sign"] == sign]
            other = "2" if number == "1" else "1"
            assert mark["layer"] == silk and not mark["hidden"], (board.id, ref, sign)
            # Upright or upside down; turned a quarter, "-" would read "|".
            assert (mark["at"][2:] or [0])[0] % 180 == 0, (board.id, ref, sign)
            assert distance(mark["at"], where[number]) < distance(mark["at"], where[other]), (board.id, ref, sign)
            assert distance(mark["at"], where[number]) <= FURTHEST_MM, (board.id, ref, sign)


def test_the_boards_have_the_parts_that_needed_marks():
    """The one failure that would make the test above vacuous."""
    found = {(board.id, reference(footprint)) for board in BOARDS for _, footprint in polarized(board)}
    assert {("backplane", "C1"), ("backplane", "DT1"), ("teensy-adapter", "D1"),
            ("microphone-flex", "D1"), ("female-base-v2", "C1"), ("male-static-v2", "C1")} <= found


def test_the_convention_is_the_one_the_part_table_states():
    """Pad 1's sign agrees with what the ordered part's specification says."""
    for board in BOARDS:
        for name, footprint in polarized(board):
            value = next(item[2] for item in harness.children(footprint, "property") if item[1] == "Value")
            for part in PARTS:
                if (part["footprint"], part["value"]) == (name, value):
                    assert STATED[signs_of(name)[0]] in part["specification"], (board.id, reference(footprint))


def test_every_part_the_table_calls_polarized_gets_marks():
    """A polarized part on a footprint outside POLARITY would go unmarked."""
    for part in PARTS:
        if any(stated in part["specification"] for stated in STATED.values()):
            assert signs_of(part["footprint"]), part["footprint"]
