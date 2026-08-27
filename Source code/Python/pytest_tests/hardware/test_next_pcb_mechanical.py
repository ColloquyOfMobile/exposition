# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_next_pcb_mechanical.py

"""The envelope the next board has to fit, read out of the one that exists.

These read a real file, which the rest of this suite does not do - but it
is a checked-in CAD file that nothing here writes to, and the whole point
of the module under test is that it parses rather than remembers. A test
that restated the numbers would be the second copy the module exists to
avoid; what is worth pinning is that the parse still finds them, and that
the answers are the shape a board has.
"""
from colloquy.hardware.electronics import next_pcb_mechanical as mechanical
from colloquy.hardware.electronics.next_pcb_report import mechanical_markdown


def test_the_board_file_is_where_this_thinks_it_is():
    """The one failure that would make every other test here vacuous."""
    assert mechanical.EXISTING_PCB.exists(), mechanical.EXISTING_PCB


def test_the_board_is_a4():
    board = mechanical.outline()

    assert (board["width"], board["height"]) == (210.0, 297.0)
    assert board["corner_radius"] == 5.0


def test_the_outline_is_not_at_the_origin():
    """It is drawn at x 44, y 52.16, and the next board should keep that
    frame: every fixed position below is in it, and redrawing at 0,0 turns
    all of them into arithmetic somebody has to do by hand."""
    board = mechanical.outline()

    assert board["left"] != 0
    assert board["top"] != 0


def test_every_fixed_part_was_found():
    """`FIXED` names them; if a reference is ever renamed on the old board
    this silently drops it, and the new board loses a panel cutout."""
    found = mechanical.fixed_placements()

    assert set(found) == set(mechanical.FIXED)


def test_the_fixed_parts_are_all_actually_near_an_edge():
    """They are what the panel has a hole for. Something 100 mm into the
    middle of the board is not that, and would mean `FIXED` had drifted
    into listing things for other reasons."""
    for reference in mechanical.FIXED:
        edge, distance = mechanical.edges_of(reference)
        assert distance < 20, (reference, edge, distance)


def test_the_connectors_are_spread_over_three_edges():
    """Two DSUBs on the bottom, one left, one right. It matters because a
    layout that quietly moved one to a tidier edge would need the
    enclosure re-cut."""
    edges = {
        reference: mechanical.edges_of(reference)[0]
        for reference in ("J5", "J1", "A-J3", "B-J4")
    }

    assert edges == {
        "J5": "right",
        "J1": "left",
        "A-J3": "bottom",
        "B-J4": "bottom",
    }


def test_both_usb_sockets_are_along_the_top():
    """The Mega's and the U2D2's. Both leads have to reach out of the
    rack, which is why neither is free to move inward."""
    for reference in ("A1", "U1"):
        assert mechanical.edges_of(reference)[0] == "top"


def test_the_old_board_has_no_mounting_holes():
    """Not a quirk of the export - the NPTH file has a header, an M30 and
    nothing between them, and there is no MountingHole footprint either.
    An A4 board with a Mega shield on it is held by DSUB jackscrews."""
    assert mechanical.mounting_holes() == []
    assert mechanical.has_mounting_holes() is False


def test_the_amplifiers_free_a_real_band_of_board():
    """Ten parts leave because the amplifier moved to the body, and the
    filters and analysers have to go somewhere."""
    freed = mechanical.freed_region()
    board = mechanical.outline()

    assert freed["parts"] == len(mechanical.REMOVED)
    assert freed["width"] > 100
    # Inside the board, or the parse has found something in another frame.
    assert board["left"] <= freed["left"] <= freed["right"] <= board["right"]
    assert board["top"] <= freed["top"] <= freed["bottom"] <= board["bottom"]


def test_nothing_removed_is_also_fixed():
    """A part cannot both leave the board and be what the panel has a hole
    for."""
    assert not set(mechanical.REMOVED) & set(mechanical.FIXED)


def test_the_document_announces_itself_and_carries_the_numbers():
    text = mechanical_markdown()

    assert "Generated. Do not edit." in text
    assert "210 × 297 mm" in text
    # The finding, not just the measurements.
    assert "Mounting holes: there are none" in text
