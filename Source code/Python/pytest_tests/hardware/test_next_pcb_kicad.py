# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_next_pcb_kicad.py

"""The netlist KiCad imports, and the audit that says whether it will.

`NETLIST.md` is for reading and `next_pcb.net` is for Pcbnew, and they
come out of one `Design` so they cannot disagree. What needs pinning is
the translation between them, because it is where the two vocabularies
meet: `next_pcb.py` names terminals (`IN`, `STROBE`, the DSUB shell as
pin 0) and a footprint numbers pads, and a netlist naming a pad that does
not exist imports *quietly* and leaves the net unconnected. That is a
fault found at the end of a build with a multimeter.

Like `test_next_pcb_mechanical.py`, one test here reads the checked-in
board file - for the same reason, and it is the point of the module: the
footprints are lifted from the board that exists rather than chosen, so
what is worth pinning is that they are still the ones it uses.
"""
import re

import pytest

from colloquy.hardware.electronics import next_pcb, next_pcb_kicad as kicad
from colloquy.hardware.electronics import next_pcb_mechanical as mechanical


@pytest.fixture(scope="module")
def design():
    return next_pcb.Design()


@pytest.fixture(scope="module")
def netlist(design):
    return kicad.netlist_text(design)


# --- every part can be placed --------------------------------------------


def test_every_part_has_a_footprint(design):
    """A part with none would reach the netlist as an empty string and
    import as a component KiCad cannot place."""
    for part in design.parts:
        assert part.footprint, part.ref
        assert ":" in part.footprint, f"{part.ref}: {part.footprint}"


def test_the_footprints_are_the_ones_the_board_that_exists_uses():
    """Lifted, not chosen - the same trick as the envelope, and the same
    reason: the connectors and the shield are fixed parts in a panel that
    is already cut."""
    text = mechanical.EXISTING_PCB.read_text(encoding="utf-8", errors="ignore")
    on_the_old_board = set(re.findall(r'\(footprint "([^"]+)"', text))

    for lifted in (
        next_pcb._V1["dsub"],
        next_pcb._V1["shield"],
        next_pcb._V1["u2d2"],
        next_pcb._V1["jack"],
        next_pcb._V1["bridge"],
        next_pcb._V1["jst"],
        next_pcb._V1["resistor"],
        next_pcb._V1["electrolytic"],
    ):
        assert lifted in on_the_old_board, lifted


def test_the_board_is_still_entirely_through_hole(design):
    """v1 is, this one is, and the five surface-mount things on it are
    the amplifier breakouts that leave."""
    for part in design.parts:
        assert "_SMD" not in part.footprint, part.ref
        assert "Handsoldering" not in part.footprint, part.ref


# --- the file itself -----------------------------------------------------


def test_it_is_balanced_and_complete(design, netlist):
    assert netlist.count("(") == netlist.count(")")
    assert len(re.findall(r"\(comp \(ref ", netlist)) == len(design.parts)
    assert len(re.findall(r"\(net \(code ", netlist)) == len(design.nets)


def test_it_says_where_it_came_from(netlist):
    """It lands in a CAD folder next to files a person edits."""
    assert "do not edit" in netlist
    assert "next_pcb.py" in netlist


def test_the_timestamps_are_stable_across_regenerations(design):
    """Pcbnew matches an imported netlist against the board by timestamp
    before it falls back to the reference. Fresh ones every run would
    arrive as 113 duplicates rather than as an update."""
    first = re.findall(r'\(tstamps "([^"]+)"\)', kicad.netlist_text(design))
    second = re.findall(r'\(tstamps "([^"]+)"\)', kicad.netlist_text(design))

    assert first == second
    assert len(set(first)) == len(first)


# --- the two vocabularies meeting ----------------------------------------


def test_the_dsub_shell_stays_pin_zero(netlist):
    """It happens to match: the design calls the shell pin 0 and the
    KiCad footprint calls its two mounting pads 0. Worth a test precisely
    because it is a coincidence somebody could tidy away."""
    assert '(node (ref "J5") (pin "0"))' in netlist


def test_the_megas_rails_are_translated_to_real_pads(netlist):
    """The shield brings 5 V out on four pads and GND on six, so the
    design's plain `5V` and `GND` name no pad at all."""
    assert '(node (ref "A1") (pin "5V1"))' in netlist
    assert '(node (ref "A1") (pin "GND1"))' in netlist
    assert '(node (ref "A1") (pin "5V"))' not in netlist
    assert '(node (ref "A1") (pin "GND"))' not in netlist


def test_a_mega_signal_pin_is_left_alone(netlist):
    """Only the rails need translating; D11 is a pad called D11."""
    assert '(node (ref "A1") (pin "D11"))' in netlist


def test_the_msgeq7_is_placed_but_not_wired(design, netlist):
    """Its terminals are named on purpose (`next_pcb.py`), because
    numbering them would be inventing the part. So the chip arrives on
    the board and its nets do not - and the audit says so rather than the
    reader finding out."""
    assert '(ref "U1")' in netlist
    for terminal in ("IN", "OUT", "STROBE", "RESET"):
        assert f'(node (ref "U1") (pin "{terminal}"))' not in netlist

    unnumbered = [f for f in kicad.audit(design, libraries={}) if f.kind == "not numbered"]
    assert len(unnumbered) == 30


# --- the audit -----------------------------------------------------------


def test_the_audit_finds_a_footprint_this_machine_has_not_got(design):
    """A nickname nobody has registered. Reported rather than raised: a
    library is a fact about a machine, and this has to run on the one
    with no KiCad at all."""
    findings = kicad.audit(design, libraries={})

    assert any(f.kind == "missing library" for f in findings)


def test_the_audit_finds_a_pad_that_does_not_exist(tmp_path, design):
    """The fault it exists for. A netlist naming a pad the footprint has
    not got imports quietly and leaves the net unconnected."""
    pretty = tmp_path / "Resistor_THT.pretty"
    pretty.mkdir()
    name = next_pcb._V1["resistor"].split(":", 1)[1]
    # A resistor with one pad: every R in the design asks for two.
    (pretty / f"{name}.kicad_mod").write_text(
        '(footprint "x" (pad "1" thru_hole circle))', encoding="utf-8"
    )

    findings = kicad.audit(design, libraries={"Resistor_THT": pretty})
    bad = [f for f in findings if f.kind == "no such pad"]

    assert bad
    assert all("'2'" in f.detail for f in bad)


def test_the_audit_passes_a_footprint_whose_pads_are_all_there(tmp_path, design):
    pretty = tmp_path / "Resistor_THT.pretty"
    pretty.mkdir()
    name = next_pcb._V1["resistor"].split(":", 1)[1]
    (pretty / f"{name}.kicad_mod").write_text(
        '(footprint "x" (pad "1" thru_hole circle) (pad "2" thru_hole circle))',
        encoding="utf-8",
    )

    findings = kicad.audit(design, libraries={"Resistor_THT": pretty})

    assert not [f for f in findings if f.kind == "no such pad"]


def test_the_u2d2s_flying_lead_is_not_reported_as_a_fault(design):
    """Its footprint is a mounting outline with no pads at all, and its
    data wire really is a lead to a screw terminal. A fact to state, not
    a fault to fix."""
    findings = kicad.audit(design, libraries={})

    assert not [f for f in findings if f.subject == "M1.data"]
