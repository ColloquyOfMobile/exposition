# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_microphone_board.py

"""`microphone board` against the copper it plugs into, the boards it
copies its fixing from, and the arithmetic it quotes.

Three promises, each quiet when broken:

- **it plugs in unchanged**: its JST is in the order of the harness
  boards' microphone sockets, read out of their copper, so a 1:1 lead
  can never swap the supply and the signal;
- **the extrusion facts are the existing boards'**: the 8 mm holes on
  one centreline, at the spacings the document gives, read out of the
  harness boards' outlines rather than restated;
- **every figure is computed**: by `microphone_board.py`.

Like `test_harness.py`, these read checked-in files rather than doubles.
"""
import math
import re

from colloquy.hardware.electronics import MicrophoneBoard, harness, microphone_board, shields

DOCUMENT = MicrophoneBoard.folder / MicrophoneBoard.file_name

# The harness boards whose microphone socket the board plugs into.
SOCKETS = ("female base", "male static")


def _text():
    return DOCUMENT.read_text(encoding="utf-8")


def _flat():
    """The document's prose with every run of whitespace made one space,
    so a phrase can be found across a line break."""
    return re.sub(r"\s+", " ", _text())


def _table(first_header_cell):
    lines = _text().splitlines()
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells and cells[0] == first_header_cell:
            rows = []
            for row in lines[index + 2:]:
                if not row.startswith("|"):
                    break
                rows.append(_cells(row))
            return cells, rows
    raise AssertionError(f"no table headed {first_header_cell!r}")


def _cells(line):
    if not line.startswith("|"):
        return []
    return [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]


def test_the_document_is_where_this_thinks_it_is():
    assert DOCUMENT.is_file()


# --- section 3: it plugs into the harness boards unchanged -----------------


def test_the_connector_is_in_the_harness_boards_order():
    _, rows = _table("J1 pin")
    written = {row[0]: row[1] for row in rows}
    assert written == {"1": "GND", "2": "+5V", "3": "OUT"}

    for folder in SOCKETS:
        sockets = [
            connector for connector in harness.read(folder)
            if connector.label == "microphone"
        ]
        assert len(sockets) == 1, folder
        pins = sockets[0].pins
        assert sockets[0].kind == "JST EH 3", folder
        assert pins["1"] == "GND", folder
        assert pins["2"] == "/5V", folder
        assert "microphone" in pins["3"], folder


# --- section 1: the existing boards screw on along one slot ----------------


def _edge_circles(folder):
    """Every circle on a harness board's Edge.Cuts: (x, y, diameter)."""
    tree = harness.parse(
        harness.BOARDS_BY_FOLDER[folder].path.read_text(encoding="utf-8", errors="ignore")
    )
    circles = []
    for item in harness.children(tree, "gr_circle"):
        layer = harness.children(item, "layer")
        if not layer or layer[0][1] != "Edge.Cuts":
            continue
        (centre,) = harness.children(item, "center")
        (end,) = harness.children(item, "end")
        x, y = float(centre[1]), float(centre[2])
        diameter = 2 * math.dist((x, y), (float(end[1]), float(end[2])))
        circles.append((x, y, round(diameter, 2)))
    return sorted(circles, key=lambda circle: circle[1])


def test_the_harness_boards_have_8_mm_holes_on_one_line_at_the_spacings_quoted():
    text = _flat()
    expected = {"female base": 43, "female static": 50, "center": 70}
    for folder, spacing in expected.items():
        circles = _edge_circles(folder)
        assert [circle[2] for circle in circles] == [8.0, 8.0], folder
        assert circles[0][0] == circles[1][0], folder
        assert round(circles[1][1] - circles[0][1]) == spacing, folder
        assert f"`{folder}` two, {spacing} mm" in text, folder

    # male static: one hole, and the slot open to its edge 50 mm on.
    circles = _edge_circles("male static")
    assert [circle[2] for circle in circles] == [8.0]
    assert "`male static` one and a slot, 50 mm" in text


# --- sections 1 to 3: the figures, recomputed -------------------------------


def test_the_circuit_figures_are_the_computed_ones():
    text = _flat()
    low, high = microphone_board.held_window()

    assert f"`TH` at {microphone_board.threshold_volts():.1f} V" in text
    assert (
        f"**held at {microphone_board.held_swing():.1f} Vpp ({low:.2f}–{high:.2f} V)**"
        in text
    )
    assert f"a {microphone_board.input_corner():.0f} Hz corner" in text
    assert (
        f"a {microphone_board.supply_corner():.0f} Hz corner for a "
        f"{microphone_board.supply_drop():.2f} V drop" in text
    )
    assert f"the corner is {microphone_board.build_out_corner() / 1000:.0f} kHz" in text
    assert f"attack {microphone_board.attack_seconds() * 1000:.1f} ms" in text


def test_the_output_stays_inside_the_teensys_reference():
    low, high = microphone_board.held_window()
    worst_low, worst_high = shields.microphone_window()

    assert worst_low <= low and high <= worst_high
    assert high < shields.TEENSY41_REFERENCE


def test_the_screw_leaves_a_full_bite_on_the_nut():
    left = microphone_board.thread_left_for_the_nut()

    assert left >= microphone_board.NUT_THREAD
    assert f"**{left:.1f} mm**" in _text()


def test_the_outline_adds_up():
    """Two holes 50 mm apart, 6 mm from each end, on a 62 mm board; the
    capsule clear of the first hole's keep-out."""
    text = _flat()
    width, length = (float(n) for n in re.search(r"\*\*(\d+) × (\d+) mm\*\*", text).groups())
    spacing = float(re.search(r"\*\*(\d+) mm apart\*\*, (\d+) mm from each end", text).group(1))
    end = float(re.search(r"\*\*\d+ mm apart\*\*, (\d+) mm from each end", text).group(1))
    keep_out = float(re.search(r"keep-out \| (\d+) mm round each hole", text).group(1))
    capsule_at = float(re.search(r"centred (\d+) mm from the end", text).group(1))

    assert (width, length) == (20, 62)
    assert 2 * end + spacing == length
    assert end + keep_out / 2 + 9.7 / 2 <= capsule_at
    assert keep_out <= width
