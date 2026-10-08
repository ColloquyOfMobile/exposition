# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_main_pcb_configuration.py

"""Which board is in the rack, and what is plugged into its slots.

A record rather than a reading - nothing in the hardware can say which
shield is in a slot, `shields` says so outright - so what is tested is
the record: that a press writes it, that a hand-edited params.json can
never take the page down, that each board's slots are its document's,
and that what the page says follows from a configuration is what the
documents say follows.

`Configuration` is a plain `Base` over one params entry, so it builds
against a stub owner, as `MainPCB` does in test_main_pcb.py.
"""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from colloquy.drivers.audio import BODIES
from colloquy.hardware.electronics import Electronics
from colloquy.hardware.main_pcb import MainPCB
from colloquy.hardware.main_pcb.configuration import Configuration, table
from colloquy.params import DEFAULTS

_ELECTRONICS = Path(table.__file__).resolve().parents[2] / "electronics"
PATH = ("hardware", "main pcb", "configuration")


def make_configuration(configuration=None, wired_bodies=("female1", "male1")):
    """A Configuration over a throwaway params dict."""
    params = {
        "main pcb": {"mounted": True, "unmounted at": ""},
        "audio": {"wired bodies": list(wired_bodies)},
    }
    if configuration is not None:
        params["main pcb"]["configuration"] = configuration
    colloquy = SimpleNamespace(params=params)
    pcb = SimpleNamespace(
        owners=[], colloquy=colloquy, name="main pcb", params=params["main pcb"]
    )
    node = Configuration(owner=pcb)
    node._log = lambda *a, **k: None
    node.stored = params["main pcb"]
    return node


def snapshot(node, path=PATH):
    return node._snapshot_if_opened(path)


def press(node, *names):
    """Follow child names down from `node` and call the last one, the way
    the tree does with a `call` tail."""
    for name in names[:-1]:
        node = node.snapshot_children[name]
    node.snapshot_children[names[-1]]()


# --- the record ----------------------------------------------------------


def test_the_default_is_the_board_in_service():
    assert DEFAULTS["main pcb"]["configuration"]["board"] == table.DEFAULT_BOARD
    assert table.DEFAULT_BOARD == "electronic box"

    reading = table.read(DEFAULTS["main pcb"]["configuration"])
    assert reading.board is table.ELECTRONIC_BOX
    assert reading.recorded_at == ""


def test_a_default_is_never_passed_off_as_something_somebody_said():
    states = snapshot(make_configuration())

    assert "never" in states["recorded"]["value"]
    assert "default" in states["recorded"]["value"]


@pytest.mark.parametrize(
    "stored",
    [
        None,
        {},
        "shields backplane",
        ["a", "list"],
        {"board": None},
        {"board": "a board that does not exist"},
        {"board": "shields backplane", "fitted": "not a dict"},
        {"board": "shields backplane", "fitted": {"shields backplane": "nor this"}},
        {"board": "shields backplane", "fitted": {"shields backplane": {"computing slot": 7}}},
    ],
)
def test_a_hand_edited_record_never_takes_the_page_down(stored):
    """params.json is hand-editable, and a render that raises is outside a
    command - which emergency-stops the installation."""
    node = make_configuration(stored)

    states = snapshot(node)
    for name, child in node.snapshot_children.items():
        child._snapshot_if_opened(PATH + (name,))
    assert states["in the rack"]["value"]


def test_an_unknown_board_is_said_and_every_board_offered():
    node = make_configuration({"board": "electronic box v3"})

    assert "not a board" in snapshot(node)["in the rack"]["value"]
    assert set(node.snapshot_children["board"].snapshot_children) == {
        board.name for board in table.BOARDS
    }


def test_an_unknown_slot_value_is_said_and_every_choice_offered():
    node = make_configuration(
        {"board": "shields backplane", "fitted": {"shields backplane": {"computing slot": "Uno"}}}
    )

    slot = node.snapshot_children["computing slot"]
    assert "none of the choices" in slot._snapshot_if_opened(PATH + ("computing slot",))["fitted"]["value"]
    assert set(slot.snapshot_children) == {c.name for c in table.COMPUTING_SLOT.choices}
    assert "not understood" in snapshot(node)


# --- pressing ------------------------------------------------------------


def test_choosing_a_board_writes_it_down():
    node = make_configuration()

    press(node, "board", "shields backplane")

    stored = node.stored["configuration"]
    assert stored["board"] == "shields backplane"
    assert stored["recorded at"], "when it was recorded is worth having"
    assert node.reading.board is table.SHIELDS_BACKPLANE


def test_choosing_a_shield_writes_it_down_for_that_board():
    node = make_configuration({"board": "shields backplane", "fitted": {}, "recorded at": ""})

    press(node, "computing slot", table.TEENSY_ADAPTER)

    stored = node.stored["configuration"]
    assert stored["fitted"] == {"shields backplane": {"computing slot": table.TEENSY_ADAPTER}}
    assert node.reading.fitted["computing slot"] == table.TEENSY_ADAPTER
    assert stored["recorded at"]


def test_the_record_is_written_whole():
    """Only assignment saves params.json - a nested setdefault or update
    changes memory and never reaches the file."""
    node = make_configuration({"board": "shields backplane", "fitted": {}, "recorded at": ""})
    written = []
    real = node.stored

    class Watched(dict):
        def __setitem__(self, key, value):
            written.append(key)
            super().__setitem__(key, value)

    node.owner.params = Watched(real)
    node.stored = node.owner.params

    press(node, "JV3 female3", table.EMPTY)

    assert written == ["configuration"]


def test_a_board_taken_out_keeps_its_shields():
    """Its shields are still in it: putting it back should not mean
    recording them all over again."""
    node = make_configuration({"board": "shields backplane", "fitted": {}, "recorded at": ""})
    press(node, "computing slot", table.TEENSY_ADAPTER)

    press(node, "board", "electronic box")
    press(node, "board", "shields backplane")

    assert node.reading.fitted["computing slot"] == table.TEENSY_ADAPTER


def test_only_the_presses_that_change_something_are_offered():
    node = make_configuration({"board": "shields backplane"})

    assert "shields backplane" not in node.snapshot_children["board"].snapshot_children
    computing = node.snapshot_children["computing slot"].snapshot_children
    assert table.MEGA not in computing
    assert set(computing) == {table.TEENSY_ADAPTER, table.EMPTY}


def test_a_board_shows_its_own_slots_and_no_others():
    expected = {
        "electronic box": [],
        "colloquy control v2": [],
        "thomas or teensy": ["mode shunt", "teensy socket"],
        "shields backplane": [
            "computing slot",
            "analyser slot",
            "JV1 female1",
            "JV2 female2",
            "JV3 female3",
            "JV4 male1",
            "JV5 male2",
        ],
    }
    for board, slots in expected.items():
        node = make_configuration({"board": board})
        assert list(node.snapshot_children) == ["board", *slots], board


def test_the_writers_refuse_what_is_not_on_the_board():
    with pytest.raises(ValueError):
        table.with_board({}, "electronic box v3", "now")
    with pytest.raises(ValueError):
        table.with_fitted({}, "electronic box", "computing slot", table.MEGA, "now")
    with pytest.raises(ValueError):
        table.with_fitted({}, "shields backplane", "computing slot", "Uno", "now")


# --- the page ------------------------------------------------------------


def _every_configuration_node():
    for board in table.BOARDS:
        node = make_configuration({"board": board.name})
        yield PATH, node
        for name, child in node.snapshot_children.items():
            yield PATH + (name,), child


def test_no_reading_is_named_after_a_child():
    """Both are written into one dict, so a leaf with a child's name
    replaces the child's link - silently (see `scope` in CLAUDE.md)."""
    for path, node in _every_configuration_node():
        states = node._snapshot_if_opened(path)
        for name in node.snapshot_children:
            # A command stays a callable and a node stays a node; a leaf
            # is neither.
            assert callable(states[name]) or "opened" in states[name], (path, name)


def test_every_document_linked_is_one_the_page_has():
    names = {document.name for document in Electronics(owner=None).documents}

    for board in table.BOARDS:
        assert board.documents, board.name
        assert set(board.documents) <= names, board.name


def test_the_links_go_to_the_documents():
    states = snapshot(make_configuration({"board": "shields backplane"}))

    assert 'href="/app/hardware/electronics/shields"' in states["described in"]["html"]


def test_a_board_with_slots_says_how_to_change_them():
    for board in table.BOARDS:
        states = snapshot(make_configuration({"board": board.name}))
        assert ("changing what is fitted" in states) == bool(board.slots), board.name


def test_main_pcb_carries_the_configuration_mounted_or_not():
    for mounted in (True, False):
        params = {
            "main pcb": {
                "mounted": mounted,
                "unmounted at": "",
                "configuration": {"board": "shields backplane"},
            }
        }
        owner = SimpleNamespace(
            owners=[], colloquy=SimpleNamespace(params=params), name="hardware"
        )
        pcb = MainPCB(owner=owner)

        assert "configuration" in pcb.snapshot_children
        board = pcb._snapshot_if_opened(("hardware", "main pcb"))["board"]["value"]
        assert board.startswith("shields backplane")


# --- held to the documents -----------------------------------------------


def test_voice_slot_n_is_body_n():
    """`shields` section 2d's table, read rather than restated."""
    text = (_ELECTRONICS / "SHIELDS.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `(JV\d)` \| (\w+) \| `\w+/tone`", text, re.MULTILINE)

    assert [f"{slot} {body}" for slot, body in rows] == [s.name for s in table.VOICE_SLOTS]
    assert [body for _slot, body in rows] == list(BODIES)


def test_the_shunt_positions_are_the_silkscreens():
    text = (_ELECTRONICS / "THOMAS_OR_TEENSY.md").read_text(encoding="utf-8")

    for position in (table.THOMAS, table.TEENSY):
        assert f"shunt to `{position}`" in text or f"shunt back to `{position}`" in text


def test_every_slot_default_is_one_of_its_choices():
    for slot in (table.RACK,) + tuple(s for b in table.BOARDS for s in b.slots):
        assert slot.choice(slot.default) is not None, slot.name


def test_the_shields_defaults_are_its_first_step():
    """Step 1 - the Mega, the carrier, five Thomas cards - is the one the
    exhibition depends on, so it is what an unrecorded slot is taken to
    hold."""
    fitted = table.fitted_on({}, "shields backplane")

    assert fitted["computing slot"] == table.MEGA
    assert fitted["analyser slot"] == table.MSGEQ7_CARRIER
    assert {fitted[s.name] for s in table.VOICE_SLOTS} == {table.THOMAS_CARD}


# --- what follows --------------------------------------------------------


def _notes(fitted, board="shields backplane", wired=("female1", "male1")):
    stored = {"board": board, "fitted": {board: fitted}}
    return table.notes(table.read(stored), list(wired))


def test_step_one_with_its_wired_bodies_has_little_to_say():
    said = _notes({}, wired=BODIES)

    assert said == {}


def test_the_mega_without_its_carrier_cannot_hear():
    said = _notes({"analyser slot": table.EMPTY})

    assert "no body can be heard" in said["hearing"]
    # And the audio tests' list is called out, since it still names two.
    assert "female1 and male1" in said["wired bodies"]


def test_the_teensy_does_not_read_the_carrier():
    said = _notes({"computing slot": table.TEENSY_ADAPTER})

    assert "never the carrier" in said["hearing"]
    assert "firmware 5" in said["computing"]


def test_the_teensy_step_says_nothing_about_hearing():
    said = _notes({"computing slot": table.TEENSY_ADAPTER, "analyser slot": table.EMPTY})

    assert "hearing" not in said


def test_an_empty_voice_slot_is_a_silent_body():
    said = _notes({"JV3 female3": table.EMPTY, "JV5 male2": table.EMPTY}, wired=BODIES)

    assert said["voices"].startswith("female3 and male2 make no sound")
    assert "female3 and male2" in said["wired bodies"]


def test_cards_the_wired_list_has_not_caught_up_with_are_named():
    said = _notes({})

    assert said["not yet wired"].startswith("female2, female3 and male2 have a card")


def test_a_revalued_card_with_the_mega_is_said():
    said = _notes({"JV2 female2": table.REVALUED_CARD}, wired=BODIES)

    assert "JV2 female2" in said["pitches"]


def test_a_revalued_card_with_the_teensy_is_what_it_is_for():
    said = _notes(
        {
            "computing slot": table.TEENSY_ADAPTER,
            "analyser slot": table.EMPTY,
            "JV2 female2": table.REVALUED_CARD,
        }
    )

    assert "pitches" not in said


def test_teensy_mode_with_an_empty_socket_is_silence():
    said = _notes({"mode shunt": table.TEENSY}, board="thomas or teensy")

    assert "every body is silent" in said["sound"]


def test_teensy_mode_takes_the_audio_tests_with_it():
    said = _notes(
        {"mode shunt": table.TEENSY, "teensy socket": table.TEENSY_41},
        board="thomas or teensy",
    )

    assert "test audio loop" in said["sound"]


def test_thomas_mode_is_the_v2_board_and_needs_no_note():
    assert _notes({}, board="thomas or teensy") == {}
