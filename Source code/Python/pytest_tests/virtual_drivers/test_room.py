"""The room from TJ's Rhino model (colloquy.virtual_drivers.room and the
room.json that export_room.py writes): what the model says, how its
anonymous females get their names, and the calibration held against it."""
import hashlib

import pytest

from colloquy.hardware.pcb_files.gerbers import REPO_FOLDER
from colloquy.params import DEFAULTS
from colloquy.virtual_drivers import room


def _with(origins):
    return {"bar": {"interaction_origins": origins}}


# The defaults with female2's two entries exchanged: what the model says
# the defaults should have been.
SWAPPED = _with(
    {
        "male1": {"female1": 0, "female2": 246.094, "female3": 125.977},
        "male2": {"female1": 181.641, "female2": 64.453, "female3": 304.688},
    }
)


def test_room_json_is_the_model_as_it_is_now():
    """The model is not in git (182 MB): where it is, the JSON must be
    what the generator makes of it now. Re-run `py export_room.py`."""
    record = room.load()
    model = REPO_FOLDER / record["source"]
    if not model.is_file():
        pytest.skip(f"{record['source']} is not on this machine")
    sha = hashlib.sha256()
    with model.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            sha.update(block)
    assert record["source sha256"] == sha.hexdigest(), (
        "the Rhino model changed: run `py export_room.py`"
    )


def test_the_model_has_three_females_a_third_of_a_turn_apart():
    angles = sorted(f["at"] for f in room.load()["females"])

    assert len(angles) == 3
    for a, b in zip(angles, angles[1:] + [angles[0] + 360]):
        assert abs((b - a) - 120) < 1


def test_the_model_has_the_males_at_either_end_of_the_bar():
    first, second = sorted(m["at"] for m in room.load()["males"])

    assert abs((second - first) - 180) < 0.5


def test_a_female_faces_the_pivot_with_her_sensor_in_front_of_her_mirror():
    for female in room.load()["females"]:
        assert female["mirror"]["left"] < 0 < female["mirror"]["right"]
        assert female["sensor"]["forward"] > female["mirror"]["forward"] > 0


def test_female1_is_where_the_bars_zero_puts_male1():
    place = room.place(DEFAULTS)

    assert place.at["female1"] == 0
    assert place.anchor == DEFAULTS["bar"]["interaction_origins"]["male1"]["female1"]
    assert room.gap(place.meeting("male1", "female1"), place.anchor) < 1e-9


def test_the_order_round_the_room_is_the_one_the_calibration_fits_best():
    # Both males' entries for female3 (126 and 305 degrees) put her a
    # third of a turn from female1 in the bar's positive turn.
    place = room.place(DEFAULTS)

    assert abs(place.at["female3"] - 120) < 1
    assert abs(place.at["female2"] - 240) < 1
    assert place.agreeing == 4


def test_the_other_order_is_taken_when_the_calibration_says_so():
    mirrored = _with(
        {
            "male1": {"female1": 0, "female2": 120, "female3": 240},
            "male2": {"female1": 180, "female2": 300, "female3": 60},
        }
    )

    place = room.place(mirrored)

    assert abs(place.at["female2"] - 120) < 1
    assert place.agreeing == 6


def test_the_males_take_turns_as_the_bar_turns():
    place = room.place(DEFAULTS)
    met = [place.nearest(angle)[0] for angle in (0, 60, 120, 180, 240, 300)]

    assert met == ["male1", "male2"] * 3


def test_the_defaults_have_the_males_swapped_on_female2():
    found = {(m.male, m.female): m for m in room.meetings(room.place(DEFAULTS), DEFAULTS)}

    wrong = {pair for pair, meeting in found.items() if not meeting.agrees}
    assert wrong == {("male1", "female2"), ("male2", "female2")}
    assert found[("male1", "female2")].faces == ("male2", "female2")
    assert found[("male2", "female2")].faces == ("male1", "female2")
    assert "male1 facing nobody" in found[("male1", "female2")].describe()


def test_exchanging_female2s_entries_makes_every_meeting_agree():
    place = room.place(SWAPPED)

    assert place.agreeing == 6
    assert all(m.agrees for m in room.meetings(place, SWAPPED))


def test_a_broken_table_is_read_as_the_defaults_never_raised():
    for broken in ({}, {"bar": None}, _with("nonsense"), _with({"male1": {"female2": "x"}})):
        place = room.place(broken)
        assert len(room.meetings(place, broken)) == 6
