"""Tests for "test seeing male1 as the bar turns".

The scenario itself needs a bar, a lit male and three sensors, so what is
covered here is the part that does not: what it writes per sample, when
it refuses to run, and the graph it draws out of a finished CSV.
"""

import io
from types import SimpleNamespace

import pandas as pd
import pytest

from colloquy.tests.test_light_sensor_values.test_seeing_male1_as_the_bar_turns import (
    TestSeeingMale1AsTheBarTurns as Scenario,
)
from colloquy.tests.test_light_sensor_values.utils import (
    bin_by_angle,
    plot_sensor_by_bar_offset_as_svg,
)


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
    # long the sensor reads took.
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
    scenario.hardware.males = (idle,)

    assert Scenario._busy_bodies(scenario) == ["bar"]


def test_nothing_running_is_nothing_to_report():
    idle = SimpleNamespace(name="idle", is_started=False)
    scenario = SimpleNamespace(
        hardware=SimpleNamespace(name="hardware", is_started=False, males=(idle,)),
        bar=idle,
        females=(idle,),
    )

    assert Scenario._busy_bodies(scenario) == []


# --- the graph -----------------------------------------------------------


@pytest.fixture
def recorded():
    """A sweep past one female: dark everywhere, lit around 64 degrees."""
    rows = []
    for bar_angle in range(0, 130):
        value = 400 if 54 <= bar_angle <= 75 else 195
        rows.append((bar_angle, "female2", float(bar_angle), 0.0, value))
    df = pd.DataFrame(rows, columns=["seconds", "body", "bar angle", "angle", "value"])
    df["bar offset"] = df["bar angle"] - df["angle"]
    return df


def test_the_offset_is_the_bar_minus_her_own_aim(recorded):
    # Her own angle is what makes it an offset rather than just the bar's
    # position - two runs with her parked differently should line up.
    turned = recorded.copy()
    turned["angle"] = 10.0
    turned["bar offset"] = turned["bar angle"] - turned["angle"]

    _x, means, _spreads, _counts = bin_by_angle(turned, "female2", 1.0, "bar offset")
    x, straight_means, _spreads, _counts = bin_by_angle(
        recorded, "female2", 1.0, "bar offset"
    )

    assert list(means) == list(straight_means)
    assert x.min() == 0.0


def test_binning_by_her_own_angle_is_still_the_default(recorded):
    # The sibling test calls it with no column at all.
    x, _means, _spreads, _counts = bin_by_angle(recorded, "female2", 1.0)

    assert list(x) == [0.0]


def test_the_graph_marks_where_the_bar_puts_male1_in_front_of_her(recorded):
    svg = io.StringIO()

    plot_sensor_by_bar_offset_as_svg(
        output=svg,
        df=recorded,
        body="female2",
        threshold=300,
        meeting_angle=64.453,
        bin_width=1.0,
    )
    drawn = svg.getvalue()

    assert "male1 in front of her (64.453 deg)" in drawn
    assert "threshold (300)" in drawn
    assert "Bar angle minus her own (degrees)" in drawn


def test_the_title_says_where_the_brightest_offset_was(recorded):
    # The answer the run is for, without having to read the curve.
    svg = io.StringIO()

    plot_sensor_by_bar_offset_as_svg(
        output=svg,
        df=recorded,
        body="female2",
        threshold=300,
        meeting_angle=64.453,
        bin_width=1.0,
    )

    assert "brightest 400 at 54 deg" in svg.getvalue()


def test_a_female_with_no_readings_draws_nothing(recorded):
    assert (
        plot_sensor_by_bar_offset_as_svg(
            output=io.StringIO(),
            df=recorded,
            body="female3",
            threshold=300,
            meeting_angle=125.977,
            bin_width=1.0,
        )
        is None
    )
