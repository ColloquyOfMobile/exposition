"""Tests for "test seeing male1 as the bar turns".

The scenario itself needs a bar, a lit male and three sensors, so what is
covered here is the part that does not: what it writes per sample, when
it refuses to run, and the two graphs it draws out of a finished CSV.
"""

import io
from types import SimpleNamespace

import pandas as pd
import pytest

from colloquy.tests.test_light_sensor_values.test_seeing_male1_as_the_bar_turns import (
    TestSeeingMale1AsTheBarTurns as Scenario,
)
from colloquy.tests.test_light_sensor_values.utils import (
    add_offsets,
    bin_by_angle,
    plot_sensor_by_alignment_offset_as_svg,
    plot_sensor_map_as_svg,
)

MEETING = 64.453


def female(name, angle, value):
    return SimpleNamespace(
        name=name,
        angle=SimpleNamespace(get=lambda: angle),
        light_sensor=SimpleNamespace(read=lambda: value),
    )


def running_scenario(bar_angle=0.0, females=(), duration=600):
    """Enough of the scenario for loop() to run against."""
    return SimpleNamespace(
        _start_time=None,
        _sample_count=0,
        _outcome=None,
        _duration=duration,
        _file=io.StringIO(),
        bar=SimpleNamespace(angle=SimpleNamespace(get=lambda: bar_angle)),
        females=females,
        stop=lambda: None,
    )


def frame(rows):
    return pd.DataFrame(
        rows, columns=["seconds", "body", "bar angle", "angle", "value"]
    )


# --- what a sample records ----------------------------------------------


def test_a_sample_files_the_bar_and_her_own_angle_beside_the_reading():
    from time import time

    scenario = running_scenario(
        bar_angle=64.5,
        females=(female("female2", angle=1.5, value=402),),
    )
    scenario._start_time = time()

    Scenario.loop(scenario)

    row = scenario._file.getvalue().strip().split(", ")
    assert row[1:] == ["female2", "64.5", "1.5", "402"]


def test_the_bar_is_read_once_for_the_whole_row_of_females():
    # Three reads of a moving bar would file three different angles for
    # one instant of one sweep, and the offsets would disagree by however
    # long the sensor reads took. It matters more now that she sweeps too:
    # both angles are moving while the row is taken.
    from time import time

    reads = []

    def bar_angle():
        reads.append(len(reads))
        return 10.0

    scenario = running_scenario(
        females=tuple(female(f"female{n}", angle=0.0, value=200) for n in (1, 2, 3)),
    )
    scenario.bar = SimpleNamespace(angle=SimpleNamespace(get=bar_angle))
    scenario._start_time = time()

    Scenario.loop(scenario)

    assert len(reads) == 1
    assert scenario._sample_count == 3


# --- refusing to run on top of the installation --------------------------


def test_anything_already_driving_the_bodies_is_named():
    idle = SimpleNamespace(name="idle", is_started=False)
    busy = SimpleNamespace(name="bar", is_started=True)
    scenario = SimpleNamespace(
        hardware=SimpleNamespace(name="hardware", is_started=False, males=(idle,)),
        bar=busy,
        females=(idle,),
    )

    assert Scenario._busy_bodies(scenario) == ["bar"]


def test_nothing_running_is_nothing_to_report():
    idle = SimpleNamespace(name="idle", is_started=False)
    scenario = SimpleNamespace(
        hardware=SimpleNamespace(name="hardware", is_started=False, males=(idle,)),
        bar=idle,
        females=(idle,),
    )

    assert Scenario._busy_bodies(scenario) == []


# --- the two angles the graphs are read against --------------------------


def test_the_bar_offset_is_measured_from_her_own_meeting_angle():
    # Not from the bar's origin, which is female1's meeting angle - that
    # is what would leave female2's and female3's humps out at 64.5 and
    # 126 instead of at zero where they can be compared.
    offsets = add_offsets(frame([(0, "female2", 64.453, 0.0, 400)]), MEETING)

    assert offsets["bar offset"][0] == pytest.approx(0.0)


def test_the_alignment_offset_takes_her_own_aim_off_as_well():
    # The bar ten degrees past her station and her turned ten degrees
    # after it is the two of them lined up - if the angles add up, which
    # is what the map is there to check.
    offsets = add_offsets(frame([(0, "female2", 74.453, 10.0, 400)]), MEETING)

    assert offsets["bar offset"][0] == pytest.approx(10.0)
    assert offsets["alignment offset"][0] == pytest.approx(0.0)


def test_add_offsets_leaves_the_frame_it_was_given_alone():
    # plot() slices one female out of the run's frame and adds her own
    # offsets to it; the next female must not inherit them.
    df = frame([(0, "female2", 64.453, 0.0, 400)])

    add_offsets(df, MEETING)

    assert "bar offset" not in df.columns


# --- the graph -----------------------------------------------------------


@pytest.fixture
def recorded():
    """A sweep past female2, who is swaying while the bar carries him.

    Brightest exactly where the two angles cancel and falling away either
    side of it - the model the alignment offset assumes - so a graph built
    from this should peak at zero.
    """
    # Both angles vary independently, as they do in a run where the bar
    # and her sway cross each other over and over.
    rows = []
    for step, bar_angle in enumerate(range(0, 130)):
        for aim in range(-10, 11):
            offset = bar_angle - MEETING - aim
            value = round(195 + 205 * max(0.0, 1.0 - abs(offset) / 20.0))
            rows.append((step, "female2", float(bar_angle), float(aim), value))
    return add_offsets(frame(rows), MEETING)


def test_a_run_lit_where_the_angles_cancel_peaks_at_zero(recorded):
    # The whole reason the offset subtracts her aim: pooled over every
    # combination of the two, the brightest offset is where they cancel.
    x, means, _spreads, _counts = bin_by_angle(
        recorded, "female2", 1.0, "alignment offset"
    )

    assert abs(float(x[means.argmax()])) <= 1.0


def test_binning_by_her_own_angle_is_still_the_default(recorded):
    # The sibling test calls it with no column at all, and gets her aim.
    x, _means, _spreads, _counts = bin_by_angle(recorded, "female2", 1.0)

    assert x.min() == -10.0
    assert x.max() == 10.0


def test_the_graph_marks_the_two_of_them_lined_up(recorded):
    svg = io.StringIO()

    plot_sensor_by_alignment_offset_as_svg(
        output=svg,
        df=recorded,
        body="female2",
        threshold=300,
        meeting_angle=MEETING,
        bin_width=1.0,
    )
    drawn = svg.getvalue()

    assert "facing each other (bar at 64.453 deg, she at 0)" in drawn
    assert "threshold (300)" in drawn
    assert "less her own aim" in drawn


def test_the_title_says_where_the_brightest_offset_was(recorded):
    # The answer the run is for, without having to read the curve.
    svg = io.StringIO()

    plot_sensor_by_alignment_offset_as_svg(
        output=svg,
        df=recorded,
        body="female2",
        threshold=300,
        meeting_angle=MEETING,
        bin_width=1.0,
    )

    assert "at 0 deg" in svg.getvalue()


def test_a_female_with_no_readings_draws_nothing(recorded):
    assert (
        plot_sensor_by_alignment_offset_as_svg(
            output=io.StringIO(),
            df=recorded,
            body="female3",
            threshold=300,
            meeting_angle=125.977,
            bin_width=1.0,
        )
        is None
    )


# --- the map that checks the subtraction ---------------------------------


def test_the_map_draws_both_angles_and_the_line_they_cancel_on(recorded):
    svg = io.StringIO()

    plot_sensor_map_as_svg(
        output=svg, df=recorded, body="female2", threshold=300, bin_width=2.0
    )
    drawn = svg.getvalue()

    assert "Bar angle from her meeting angle (degrees)" in drawn
    assert "Her own aim from her origin (degrees)" in drawn
    assert "where the two angles cancel" in drawn


def test_the_map_has_nothing_to_draw_for_a_female_who_was_not_there(recorded):
    assert (
        plot_sensor_map_as_svg(
            output=io.StringIO(), df=recorded, body="female3", threshold=300
        )
        is None
    )
