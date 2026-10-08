# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_shields_diagram.py

"""The drawing of the shields backplane: its slots and its two steps.

Every position in it is read out of `CAD/KiCad/shields/`, and the one
thing that is *worked out* rather than read - where each shield sits,
from its connector meeting the slot's header - is checked here against
the holes that would have to line up if it were right: a card's retention
hole on the backplane's, the carrier's two on the backplane's two, the
Teensy adapter's four on the computing slot's four.
"""
import math
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from colloquy.drivers.audio import BODIES
from colloquy.hardware.electronics import shields_diagram
from colloquy.hardware.main_pcb.configuration import Configuration, table

CLOSE = 0.05  # mm


@pytest.fixture(scope="module")
def geo():
    return shields_diagram.Geometry()


def _near(a, b):
    return math.dist(a, b) < CLOSE


# --- the shields land where their holes say ------------------------------


def test_each_card_sits_on_its_slots_retention_hole(geo):
    for number, slot in enumerate(table.VOICE_SLOTS, start=1):
        assert _near(geo.card_holes[slot.name], geo.holes[f"HV{number}"]), slot.name


def test_the_carrier_sits_on_its_two_retention_holes(geo):
    backplane = [geo.holes[ref] for ref in sorted(geo.holes) if ref.startswith("HA")]

    assert len(geo.carrier_holes) == len(backplane) == 2
    for hole in geo.carrier_holes:
        assert any(_near(hole, other) for other in backplane), hole


def test_the_adapter_sits_on_the_computing_slots_four_holes(geo):
    for ref, hole in geo.adapter_holes.items():
        assert _near(hole, geo.holes[ref]), ref
    assert geo.adapter == pytest.approx(geo.computing, abs=CLOSE)


def test_the_teensy_is_a_teensy_41(geo):
    """17.78 by 60.96 mm, PJRC's own outline: two rows of 24 pins 0.6 in
    apart, read off the adapter's sockets."""
    width = geo.teensy[2] - geo.teensy[0]
    length = geo.teensy[3] - geo.teensy[1]

    assert (width, length) == pytest.approx((17.78, 60.96), abs=CLOSE)


def test_the_mega_has_its_usb_end_over_the_top_edge(geo):
    """`shields` 2b: the slot keeps its USB end at the top edge."""
    usb = [box for box, name in geo.mega_overhangs if name == "USB"]

    assert len(usb) == 1
    assert usb[0][1] < geo.outline[1] < usb[0][3]


# --- what is read off the nets -------------------------------------------


def test_each_analyser_module_is_its_bodys(geo):
    """Module N is body N, as on every board so far."""
    ordered = sorted(geo.modules, key=lambda module: module[0][0])

    assert [body for _box, body in ordered] == list(BODIES)


def test_the_dsubs_carry_the_bodies_cad_boards_says(geo):
    assert geo.dsubs["J5"][1] == ["female1"]
    assert geo.dsubs["J1"][1] == ["female2"]
    # The two shared through `center`.
    shared = set(geo.dsubs["A-J3"][1]) | set(geo.dsubs["B-J4"][1])
    assert shared == {"female3", "male1", "male2"}


# --- what is drawn --------------------------------------------------------


def test_the_file_on_disk_is_the_boards_today(geo):
    """Regenerate with `py export_shields_diagram.py` when this fails."""
    path = shields_diagram.STATIC / shields_diagram.FILE_NAME

    assert path.read_text(encoding="utf-8") == shields_diagram.svg(geo)


def test_every_choice_and_both_steps_are_named(geo):
    drawn = shields_diagram.svg(geo)

    for slot in (table.COMPUTING_SLOT, table.ANALYSER_SLOT, table.VOICE_SLOTS[0]):
        for choice in slot.choices:
            assert f">{choice.name}<" in drawn, choice.name
    for step in table.SHIELD_STEPS:
        assert step.name.upper() in drawn


def test_it_carries_no_script(geo):
    drawn = shields_diagram.svg(geo).lower()

    assert "<script" not in drawn
    assert not re.search(r"\son[a-z]+\s*=", drawn), "an event handler"


def test_shields_shows_it():
    document = Path(shields_diagram.__file__).with_name("SHIELDS.md")

    assert f"/static/hardware/{shields_diagram.FILE_NAME}" in document.read_text(
        encoding="utf-8"
    )


# --- the two steps, and the page -----------------------------------------


def test_step_one_is_what_an_unrecorded_backplane_holds():
    assert table.SHIELD_STEPS[0].fitted == table.fitted_on({}, "shields backplane")


def test_step_two_is_the_teensy_with_the_analyser_slot_empty():
    """`shields` sections 0 and 10: the adapter in the Mega's place, the
    analyser slot emptied, Thomas's cards still in."""
    fitted = table.SHIELD_STEPS[1].fitted

    assert fitted["computing slot"] == table.TEENSY_ADAPTER
    assert fitted["analyser slot"] == table.EMPTY
    assert {fitted[s.name] for s in table.VOICE_SLOTS} == {table.THOMAS_CARD}


def _configuration(stored):
    params = {"main pcb": {"configuration": stored}, "audio": {"wired bodies": list(BODIES)}}
    pcb = SimpleNamespace(
        owners=[], colloquy=SimpleNamespace(params=params), name="main pcb",
        params=params["main pcb"],
    )
    return Configuration(owner=pcb)._snapshot_if_opened(("hardware", "main pcb", "configuration"))


def test_the_page_draws_it_for_the_shields_backplane_only():
    shields = _configuration({"board": "shields backplane"})
    box = _configuration({"board": "electronic box"})

    assert shields_diagram.FILE_NAME in shields["drawing"]["html"]
    assert "drawing" not in box


def test_the_page_names_the_step_a_record_is():
    teensy = {
        "board": "shields backplane",
        "fitted": {"shields backplane": dict(table.SHIELD_STEPS[1].fitted)},
    }

    assert _configuration({"board": "shields backplane"})["step"]["value"].startswith("step 1")
    assert _configuration(teensy)["step"]["value"].startswith("step 2")
    odd = {"board": "shields backplane", "fitted": {"shields backplane": {"JV1 female1": "empty"}}}
    assert "step" not in _configuration(odd)
