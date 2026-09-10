# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_goertzel_ear_results.py

"""A Goertzel ear run, written down and read back.

The run used to live only in memory: `setup()` clears the recording and a
restart takes it anyway, so the only run anybody ever had was the last
one. That is fine for "did she hear it just now" and no use at all for
the questions asked between runs - is the 6250 Hz bin always the weak
one, did moving the microphone help, is it worse than it was last week.

What is worth pinning is the shape of the file, because the file is what
outlives the person who knows how it was made:

- **a mark keeps its own exact time**, in a row of its own. Its whole
  value is that the moment is known rather than inferred, and hanging it
  on the next block would blur it by up to a quarter of a second.
- **the pitches come out of the header** on the way back in, so a pitch
  list that moves afterwards cannot relabel an old measurement.
- **a bad row costs a row**, not the file.

`tmp_path` throughout: this suite never writes into the repository, and
the reader and writer are pure enough to check with no board, no thread
and no clock (the times are handed in).
"""
import pytest

from colloquy.tests.test_goertzel_ear import protocol, recording as rec
from colloquy.tests.test_goertzel_ear.recording import Recording
from colloquy.tests.test_goertzel_ear.results import Results

from types import SimpleNamespace


def recorded(marks=(), blocks=20, hz=1000, rise_from=10):
    """A run with one pitch lifting partway through. Times handed in."""
    recording = Recording(protocol.PITCHES)
    recording.start(1000.0)
    pressed = list(marks)
    for index in range(blocks):
        now = 1000.0 + index * 0.25
        while pressed and pressed[0][0] <= index:
            _, label = pressed.pop(0)
            recording.mark(now, label)
        levels = {pitch: 1.0 for pitch in protocol.PITCHES}
        if index >= rise_from:
            levels[hz] = 30.0
        recording.add(now, levels)
    return recording


@pytest.fixture
def owner():
    return SimpleNamespace(owner=None, owners=[])


# --- the file -----------------------------------------------------------


def test_the_header_names_every_pitch_and_the_two_edges(tmp_path):
    path = recorded().write(tmp_path / "run.csv")

    header = path.read_text(encoding="utf-8").splitlines()[0]

    assert header.startswith(rec.TIME_COLUMN)
    assert header.endswith(rec.MARK_COLUMN)
    for hz in protocol.PITCHES:
        assert f"{hz} Hz" in header


def test_a_mark_gets_a_row_of_its_own_at_the_moment_it_happened():
    """Its own row, because its own time is the whole of what it is worth
    - known at the press rather than inferred from the numbers."""
    rows = recorded(marks=[(4, "1000 Hz on")]).rows()

    marked = [row for row in rows if row[-1]]

    assert len(marked) == 1
    assert marked[0][0] == "1.000"
    assert marked[0][-1] == "1000 Hz on"
    # And nothing else on it: a level beside a mark would be a reading
    # taken at a moment nothing was measured.
    assert set(marked[0][1:-1]) == {""}


def test_the_press_is_written_after_the_block_it_shares_a_moment_with():
    """A block and a press at the same instant: the press caused the
    block, not the other way round, so it goes after it."""
    rows = recorded(marks=[(4, "1000 Hz on")]).rows()

    at_one_second = [row for row in rows if row[0] == "1.000"]

    assert len(at_one_second) == 2
    assert not at_one_second[0][-1]
    assert at_one_second[1][-1] == "1000 Hz on"


def test_the_rows_are_in_time_order():
    """Blocks and presses interleaved, so the file reads the way the run
    went rather than as two lists stapled together."""
    rows = recorded(marks=[(4, "1000 Hz on"), (12, "silence")]).rows()

    times = [float(row[0]) for row in rows]

    assert times == sorted(times)


def test_a_run_that_read_nothing_writes_no_file(tmp_path):
    """A refusal, or a lead pulled before the first block. `results`
    would list an empty file as a graph with no picture in it."""
    path = tmp_path / "run.csv"

    assert recorded(blocks=0).write(path) is None
    assert not path.exists()


# --- reading it back ----------------------------------------------------


def test_a_run_comes_back_as_it_went_in(tmp_path):
    path = recorded(marks=[(4, "1000 Hz on"), (12, "silence")]).write(
        tmp_path / "run.csv"
    )

    series, marks = rec.read(path)

    assert [label for label, _ in series] == [
        f"{hz} Hz" for hz in protocol.PITCHES
    ]
    assert [len(points) for _, points in series] == [20] * 5
    assert marks == [(1.0, "1000 Hz on"), (3.0, "silence")]
    assert dict(series)["1000 Hz"][19] == (4.75, 30.0)


def test_the_pitches_are_taken_from_the_header_not_from_the_code(tmp_path):
    """A file is a record of the run that made it. If the five pitches
    move, an old run has to keep saying what it actually measured."""
    path = tmp_path / "old.csv"
    path.write_text(
        "seconds, 60 Hz, 90 Hz, mark\n"
        "0.000, 1.0, 2.0, \n"
        "0.250, 3.0, 4.0, \n"
        "0.500, , , 60 Hz on\n",
        encoding="utf-8",
    )

    series, marks = rec.read(path)

    assert [label for label, _ in series] == ["60 Hz", "90 Hz"]
    assert dict(series)["90 Hz"][1] == (0.25, 4.0)
    assert marks == [(0.5, "60 Hz on")]


def test_a_half_written_last_line_costs_a_row_and_not_the_file(tmp_path):
    """A run killed mid-write, or a file somebody has been editing. This
    reads old runs to look at them; one bad row must not lose the rest."""
    path = tmp_path / "truncated.csv"
    path.write_text(
        "seconds, 160 Hz, mark\n"
        "0.000, 1.0, \n"
        "0.250, 2.0, \n"
        "0.5, not-a-num, \n",
        encoding="utf-8",
    )

    series, _marks = rec.read(path)

    assert [len(points) for _, points in series] == [2]


def test_it_reads_through_columns_rather_than_building_the_pairs(tmp_path):
    """The same view the live graph draws through, so a run off the disk
    costs the few hundred rows it draws rather than the whole file."""
    from colloquy.ui.graph_view import Columns

    path = recorded().write(tmp_path / "run.csv")

    series, _marks = rec.read(path)

    assert all(isinstance(points, Columns) for _label, points in series)


# --- the listing --------------------------------------------------------


def test_the_runs_are_listed_newest_first(owner, tmp_path):
    """Named for when they happened, so sorting the names backwards is
    newest first - the one somebody wants is nearly always the last."""
    for stem in ("2026_09_08_10h_00min_00s", "2026_09_10_11h_30min_00s"):
        recorded().write(tmp_path / f"{stem}.csv")

    results = Results(owner=owner, dir_path=tmp_path)

    assert list(results.snapshot_children) == [
        "2026_09_10_11h_30min_00s",
        "2026_09_08_10h_00min_00s",
    ]


def test_a_run_that_finishes_while_the_page_is_open_turns_up(owner, tmp_path):
    """Rescanned every request, so nothing has to be restarted - and a
    run copied over from the other computer appears the same way."""
    results = Results(owner=owner, dir_path=tmp_path)
    assert list(results.snapshot_children) == []

    recorded().write(tmp_path / "later.csv")

    assert list(results.snapshot_children) == ["later"]


def test_an_empty_folder_and_a_missing_one_are_both_just_empty(owner, tmp_path):
    results = Results(owner=owner, dir_path=tmp_path / "not there")

    assert results.snapshot_children == {}


def test_a_run_keeps_its_graph_across_requests(owner, tmp_path):
    """A GraphView holds which page the reader is on, so rebuilding one
    per request would put them back at the start on every click."""
    recorded().write(tmp_path / "run.csv")
    results = Results(owner=owner, dir_path=tmp_path)

    first = results.snapshot_children["run"]
    second = results.snapshot_children["run"]

    assert first is second
    assert first.graph is second.graph


def test_a_run_draws_its_marks(owner, tmp_path):
    """The presses are the point of keeping the file at all: a line
    lifting at the rule that carries its own pitch."""
    recorded(marks=[(4, "1000 Hz on")]).write(tmp_path / "run.csv")

    run = Results(owner=owner, dir_path=tmp_path).snapshot_children["run"]

    assert run.graph.marks == [(1.0, "1000 Hz on")]
    assert list(run.snapshot_children) == ["recording"]


def test_a_run_says_what_is_not_in_its_file(owner, tmp_path):
    """The reason this test kept nothing for a while, said on the run
    rather than only in a docstring - a file outlives the person who
    knows how it was made."""
    recorded().write(tmp_path / "run.csv")

    run = Results(owner=owner, dir_path=tmp_path).snapshot_children["run"]
    states = run._snapshot_if_opened(path=("app", "run"))

    assert "heard the tone" in states["not in this file"]["value"]


def test_an_unreadable_file_is_said_rather_than_drawn(owner, tmp_path):
    """A picture with nothing in it, with controls that cannot move, is
    worse than a line saying the file holds nothing."""
    (tmp_path / "empty.csv").write_text("seconds, 160 Hz, mark\n", encoding="utf-8")

    run = Results(owner=owner, dir_path=tmp_path).snapshot_children["empty"]
    states = run._snapshot_if_opened(path=("app", "empty"))

    assert run.graph is None
    assert run.snapshot_children == {}
    assert "nothing readable" in states["read"]["value"]
