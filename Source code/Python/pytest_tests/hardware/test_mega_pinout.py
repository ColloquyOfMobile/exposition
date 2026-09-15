# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_mega_pinout.py

"""The Mega pinout drawing in `as built`, against the board it draws.

Reads the real checked-in `electronic box.kicad_pcb`, for
`test_harness.py`'s reason: the drawing is parsed rather than remembered,
so what is worth pinning is that the parse still finds the pins, that the
file on disk is what the generator makes of the board today, and that
the microphone table written beside it in `AS_BUILT.md` - the one somebody
reads with a probe in their hand - is still true of the copper.
"""
import re

import pytest

from colloquy.hardware.electronics import mega_pinout


@pytest.fixture(scope="module")
def board():
    return mega_pinout.Board()


def test_the_pads_land_where_as_built_says_they_do(board):
    """The rotation is the one thing the parse could get quietly wrong,
    and `as built` already states two coordinates to check it against."""
    assert board.pad(mega_pinout.MEGA, "D0").x == pytest.approx(191.96)
    assert board.pad("J4", "1").x == pytest.approx(200.85)
    # J11's even pins sit level with the Mega's analog pins, row for row.
    for row, analog in enumerate(("A0", "A1", "A2", "A3", "A4")):
        even = board.pad("J11", str(2 * row + 2))
        assert even.y == pytest.approx(board.pad(mega_pinout.MEGA, analog).y)


def test_only_j11_and_j12_have_their_names_printed(board):
    printed = {ref for ref in mega_pinout.HEADERS if board.printed[ref]}
    assert printed == {"J11", "J12"}


BODIES = ("female1", "female2", "female3", "male1", "male2")


@pytest.mark.parametrize("index, body", list(enumerate(BODIES)))
def test_the_microphone_table_in_as_built_is_the_copper(board, index, body):
    wire = board.pad("J11", str(2 * index + 1))
    mega_input = board.pad("J11", str(2 * index + 2))
    assert wire.net == f"{body}/microphone/1"
    assert board.mega_pad_on(mega_input.net).number == f"A{index}"
    (cable,) = board.elsewhere(wire.net)

    document = (
        mega_pinout.Path(mega_pinout.__file__).with_name("AS_BUILT.md")
    ).read_text(encoding="utf-8")
    row = next(
        line for line in document.splitlines()
        if re.match(rf"\|\s*\**{body}\**\s*\|", line)
    )
    cells = [re.sub(r"[*`]", "", cell).strip() for cell in row.strip("|").split("|")]
    assert cells[1] == f"J11 {wire.number}"
    assert cells[2] == f"J11 {mega_input.number} = A{index}"
    assert cells[3] == f"{cable.ref} pin {cable.number}"


def test_the_cuts_are_dirty_reworks_table():
    document = mega_pinout.Path(mega_pinout.__file__).with_name("DIRTY_REWORK.md")
    text = document.read_text(encoding="utf-8")
    cut = re.findall(r"^\| \d \| shield pad \*\*(D\d+)\*\*", text, re.MULTILINE)
    assert sorted(cut) == sorted(mega_pinout.CUT_IN_THE_REWORK)


def test_the_file_on_disk_is_the_board_today(board):
    """Regenerate with `py export_mega_pinout.py` when this fails."""
    on_disk = (mega_pinout.STATIC / mega_pinout.FILE_NAME).read_text(encoding="utf-8")
    assert on_disk == mega_pinout.svg(board)


def test_as_built_shows_it():
    document = mega_pinout.Path(mega_pinout.__file__).with_name("AS_BUILT.md")
    assert f"/static/hardware/{mega_pinout.FILE_NAME}" in document.read_text(
        encoding="utf-8"
    )
