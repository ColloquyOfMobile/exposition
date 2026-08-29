# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_harness.py

"""The four boards between the box and the bodies, as the page reads them.

Like `test_next_pcb_mechanical.py`, these read real checked-in CAD files -
for the same reason, and it is the point of the module: the pinouts are
parsed rather than remembered, so what is worth pinning is that the parse
still finds them and that the findings the document states are still
true of the copper.

The findings matter beyond the document. `next pcb` spent two drafts
calling male2's supply the one open item that could block the build, on
the grounds that its 5 V came from somewhere off these files. It comes
off `A-J3` pin 9, split three ways by `center`. If that ever stops being
true, this is where it should fail.
"""
import pytest

from colloquy.hardware.electronics import harness


@pytest.fixture(params=[b.folder for b in harness.BOARDS])
def folder(request):
    return request.param


def connectors(folder):
    return {c.ref: c for c in harness.read(folder)}


# --- the files are there and parse ---------------------------------------


def test_every_board_file_is_where_this_thinks_it_is(folder):
    """The one failure that would make every test here vacuous."""
    assert harness.BOARDS_BY_FOLDER[folder].path.is_file()


def test_every_board_has_connectors_and_nets(folder):
    assert harness.read(folder)
    assert harness.nets(folder)


def test_every_board_has_an_outline(folder):
    width, height = harness.outline(folder)

    assert 20 < width < 400, width
    assert 20 < height < 400, height


def test_nothing_on_these_boards_is_an_active_component(folder):
    """They are connectors and copper. If a regulator ever appears on one,
    the document's opening sentence stops being true."""
    for connector in harness.read(folder):
        assert connector.kind.startswith(("DSUB-15", "JST EH")), connector.ref


# --- the topology --------------------------------------------------------


def test_center_takes_both_of_the_racks_shared_connectors():
    labels = {c.label for c in harness.read("center")}

    assert "to electronic box A" in labels
    assert "to electronic box B" in labels


def test_center_hands_out_one_cable_per_body():
    labels = {c.label for c in harness.read("center")}

    assert {"to female static", "to male 1", "to male 2"} <= labels


def test_a_female_reaches_her_body_through_two_boards():
    """static at the joint, base inside her - and the static one passes
    every conductor straight through."""
    static = connectors("female static")

    assert static["J1"].label == "to center/electronic box"
    assert static["J3"].label == "to female base"
    for pin, net in static["J1"].pins.items():
        assert static["J3"].pins[pin] == net, pin


# --- what the document claims, checked against the copper ----------------


def test_male2_is_fed_from_the_box_after_all():
    """The finding that closed `next pcb` section 5's open item."""
    center = connectors("center")

    assert center["J3"].pins["9"] == "/5V", "A-J3 pin 9 is the +5 V that arrives"
    assert center["J7"].label == "to male 2"
    assert center["J7"].pins["9"] == "/5V"
    assert center["J7"].pins["2"] == "/12V"


def test_one_conductor_feeds_three_bodies():
    """The number `next pcb` says to check before ordering anything."""
    fed = [
        c.label for c in harness.read("center")
        if c.pins.get("9") == "/5V" or c.pins.get("15") == "/5V"
    ]

    assert sorted(fed) == ["to electronic box A", "to female static",
                           "to male 1", "to male 2"]


def test_the_racks_second_connector_carries_no_power():
    """`as built` says so from the rack end; this is the other end."""
    box_b = connectors("center")["J6"]

    assert "/5V" not in box_b.pins.values()
    assert "/12V" not in box_b.pins.values()


def test_a_male_fills_a_dsub_15_with_one_pin_to_spare():
    """`next pcb` section 8 argues from this. Here it is on copper."""
    male = connectors("male static")["J7"]

    spares = [p for p, net in male.pins.items() if harness._is_spare(net)]
    assert spares == ["8"]


def test_a_female_has_six_spares_wired_end_to_end():
    """Which is what makes them usable for anything she ever needs, and
    it matches what the box's own netlist calls spare1..6."""
    static = connectors("female static")["J1"]

    spares = sorted(
        (p for p, net in static.pins.items() if harness._is_spare(net)),
        key=int,
    )
    assert spares == ["1", "2", "3", "9", "10", "11"]


def test_every_dynamixel_is_tapped_where_it_is_used():
    """One data line, four places it is picked off - the bar's, a
    female's, her mirror's and a male's."""
    taps = {
        "center": "dxl center",
        "female static": "dxl female",
        "female base": "dxl mirror",
        "male static": "dxl male",
    }
    for board, label in taps.items():
        labels = {c.label for c in harness.read(board)}
        assert label in labels, board
        tap = next(c for c in harness.read(board) if c.label == label)
        assert set(tap.pins.values()) == {"GND", "/12V", "/dynamixel data"}


def test_the_male_board_breaks_out_four_light_sensors():
    """Four per male, which is what fills his connector."""
    sensors = [c for c in harness.read("male static") if c.label == "photosensor"]

    assert len(sensors) == 4


# --- and the document -----------------------------------------------------


def test_the_document_says_it_is_generated():
    text = harness.markdown()

    assert text.startswith("# The harness")
    assert "Generated. Do not edit." in text


def test_the_document_carries_every_board_and_every_connector():
    text = harness.markdown()

    for board in harness.BOARDS:
        assert board.title in text
        for connector in harness.read(board.folder):
            assert connector.ref in text


def test_the_document_states_the_finding_it_was_written_for():
    text = harness.markdown()

    assert "male2's 5 V arrives through `center`" in text
