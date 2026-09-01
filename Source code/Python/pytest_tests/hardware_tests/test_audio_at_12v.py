# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_audio_at_12v.py

"""The supply comparison, and the gain control it has to see past.

What is worth pinning here is the *judging*, not the serial driving -
the sweep itself is `test_audio_subsystem`'s, borrowed whole. The one
thing this test adds is a verdict about two passes taken minutes apart
through a microphone whose automatic gain control exists to hide the
difference between them, and a verdict is exactly the kind of thing that
can go on being confidently wrong for months.

Every method here is called unbound against a duck-typed double: the
real thing does filesystem I/O at construction (see conftest).
"""
from types import SimpleNamespace

import pytest

from colloquy.tests.test_audio_at_12v import (
    SUPPLIES,
    _decibels,
    _share,
)
# Aliased because pytest collects anything named Test*, and warns about
# the constructor when it tries. Same trick as the neighbouring audio
# suites.
from colloquy.tests.test_audio_at_12v import TestAudioAt12V as SupplyTest
from colloquy.tests.test_audio_subsystem import protocol

LOW, HIGH = SUPPLIES

# 160 Hz is timer 1 and lands in band index 1 (BANDS_HZ is 63, 160, 400,
# 1000, 2500, 6250, 16000). Pinned here so a table change is caught.
TIMER = 1
BAND = protocol.expected_band(TIMER)


def double(results=None):
    fake = SimpleNamespace(
        _results=results if results is not None else {},
        _supply=None,
        _silence=None,
        MARGIN=SupplyTest.MARGIN,
        DB_NOISE_FLOOR=SupplyTest.DB_NOISE_FLOOR,
    )
    # _comparison calls it on self; borrowed rather than reimplemented,
    # since what is under test is the sentence it produces.
    fake._describe = lambda before, after: SupplyTest._describe(fake, before, after)
    return fake


def best(rise, share, module=0):
    return {"rise": rise, "share": share, "silent share": 0.1, "module": module}


def compare(before, after):
    fake = double({LOW: {TIMER: before}, HIGH: {TIMER: after}})
    rows = SupplyTest._comparison(fake)
    return rows[protocol.TIMERS[TIMER]["hz"]]


# --- the arithmetic ------------------------------------------------------


def test_the_band_lands_where_the_table_says():
    assert protocol.BANDS_HZ[BAND] == protocol.TIMERS[TIMER]["hz"]


def test_share_is_the_band_over_the_whole_spectrum():
    values = (10, 60, 10, 10, 4, 3, 3)
    assert _share(values, 1) == pytest.approx(60 / 100)


def test_share_of_nothing_is_nothing_rather_than_a_division():
    """A module that read all zeros is an unwired input, not a silent
    room, and it must not take the process down on the way to saying so."""
    assert _share((0, 0, 0, 0, 0, 0, 0), 1) == 0.0


def test_decibels_refuses_a_rise_that_was_never_there():
    """Dividing by a rise at or below zero produces a number that looks
    like a measurement. There is no answer to "how many times louder than
    nothing", so the row says so instead of inventing one."""
    assert _decibels(0, 400) is None
    assert _decibels(-5, 400) is None
    assert _decibels(400, 0) is None


def test_decibels_is_the_ordinary_amplitude_ratio():
    assert _decibels(100, 200) == pytest.approx(6.02, abs=0.01)


# --- the comparison itself -----------------------------------------------


def test_there_is_no_comparison_until_both_passes_are_in():
    """The whole design of the node: one pass is half a measurement, and
    a page that drew a row after the first one would be drawing a
    comparison against nothing."""
    fake = double({LOW: {TIMER: best(rise=400, share=0.6)}})

    assert SupplyTest._comparison(fake) is None


def test_both_passes_in_gives_one_row_per_tone():
    fake = double({LOW: {}, HIGH: {}})

    rows = SupplyTest._comparison(fake)

    assert len(rows) == len(protocol.TIMERS_BY_PITCH)


def test_a_tone_that_got_louder_says_so():
    row = compare(best(rise=100, share=0.30), best(rise=400, share=0.62))

    assert "louder" in row
    assert "+12.0 dB" in row


def test_a_tone_that_got_quieter_is_not_believed_on_its_own():
    """At a higher rail a quieter tone is usually clipping, or a supply
    that never actually changed. Either way it is a wiring question
    before it is a result."""
    row = compare(best(rise=400, share=0.62), best(rise=100, share=0.30))

    assert "QUIETER" in row
    assert "check the wiring" in row


# --- the gain control, which is the whole reason for `share` -------------


def test_a_flat_level_with_a_climbing_share_is_read_as_louder():
    """The case this node exists for. The MAX9814's AGC holds its output
    roughly constant against exactly the change being measured, so the
    band level barely moves - while the tone takes a larger slice of a
    total the AGC is holding still, the room noise in the other six bands
    being turned down along with it."""
    row = compare(best(rise=400, share=0.35), best(rise=410, share=0.55))

    assert "gain control" in row
    assert "larger share" in row


def test_a_flat_level_and_a_flat_share_is_not_called_a_null_result():
    """It sends you to your ear rather than concluding. A bench with two
    passes minutes apart cannot distinguish "no change" from "a change
    this cannot see", and saying the first would talk somebody out of a
    decision taken on better grounds."""
    row = compare(best(rise=400, share=0.50), best(rise=405, share=0.505))

    assert "listen to it" in row
    assert "louder" not in row.replace("no change", "")


def test_a_change_under_the_bench_noise_floor_is_not_called_a_change():
    """Two passes with a screwdriver between them do not repeat to better
    than a decibel or so, and reporting 0.4 dB as an improvement is
    inventing precision this bench does not have."""
    row = compare(best(rise=400, share=0.50), best(rise=420, share=0.50))

    assert "no change this bench can resolve" in row


# --- what a silent channel means -----------------------------------------


def test_silent_at_both_supplies_is_not_a_statement_about_the_supply():
    """An unwired analyser input is a floating ADC pin, and a floating pin
    does not read silence. Two floors compared give a confident number
    about a channel nobody has connected."""
    row = compare(best(rise=3, share=0.14), best(rise=5, share=0.15))

    assert "nothing to compare" in row
    assert "unwired" in row


def test_one_pass_missing_a_tone_says_so_rather_than_guessing():
    fake = double({LOW: {TIMER: best(rise=400, share=0.6)}, HIGH: {}})

    rows = SupplyTest._comparison(fake)

    assert rows[protocol.TIMERS[TIMER]["hz"]] == "not measured in both passes"


# --- recording a pass ----------------------------------------------------


def test_a_tone_is_recorded_by_the_module_that_heard_it_best():
    """One row per tone, not twenty-five. Which module heard it is
    `test audio subsystem`'s question; this one is about five amplifiers
    on one rail, so the reading kept is "how loud did this get in the
    room at all"."""
    fake = double({LOW: {}})
    fake._supply = LOW
    quiet = [10] * 7
    fake._silence = {0: tuple(quiet), 1: tuple(quiet), 2: tuple(quiet)}

    loud = list(quiet)
    loud[BAND] = 500
    middling = list(quiet)
    middling[BAND] = 200
    averages = {
        0: tuple(middling),
        1: tuple(loud),
        2: tuple(quiet),
    }

    SupplyTest._record(fake, TIMER, averages)

    kept = fake._results[LOW][TIMER]
    assert kept["module"] == 1
    assert kept["rise"] == pytest.approx(490)


def test_a_module_with_no_floor_reading_is_skipped_rather_than_guessed():
    """No silence for that module means no rise can be computed for it.
    Treating a missing floor as zero would make an unread module look
    like the loudest one on the bench."""
    fake = double({LOW: {}})
    fake._supply = LOW
    fake._silence = {0: tuple([10] * 7)}

    loud = [10] * 7
    loud[BAND] = 900
    quiet = [10] * 7
    quiet[BAND] = 100

    SupplyTest._record(fake, TIMER, {0: tuple(quiet), 7: tuple(loud)})

    assert fake._results[LOW][TIMER]["module"] == 0


# --- throwing a pass away ------------------------------------------------


def test_forgetting_clears_both_passes():
    """The failure it prevents is a quiet one: a 5 V pass from before
    somebody moved a microphone, compared against a 12 V pass from after,
    reads as a beautifully convincing result."""
    fake = double({LOW: {TIMER: best(400, 0.6)}, HIGH: {TIMER: best(800, 0.7)}})

    SupplyTest._forget(fake)

    assert fake._results == {}
    assert SupplyTest._comparison(fake) is None


# --- which machine it can be run on --------------------------------------


def test_the_installation_is_offered_this_one(monkeypatch, stub_factory):
    """The gate this test lost, and why.

    Every other bench test is hidden on the installation because the
    board it needs is in an office and always will be. This one is the
    exception: the supply it measures is the *piece's*, so the board is
    carried to the installation and run beside it. Gating it on the
    hostname hid it on the one machine somebody would be standing at
    with a screwdriver, and typing the URL got you a picker offering a
    stand-in - two passes that differ by nothing, which reads exactly
    like a rail change that bought you nothing.

    Whether it is talking to a board is a question about the lead now,
    asked on its own page (`board is real`), not about the computer.
    """
    from colloquy.tests.group import TestGroup

    supply = stub_factory(name="test audio at 12v", is_started=False)
    group = TestGroup(
        owner=stub_factory(), name="manual tests", summary="..."
    ).fill(tests=(supply,))

    monkeypatch.setattr(
        "colloquy.machines.socket.gethostname", lambda: "Colloquy-Laptop"
    )
    assert list(group.snapshot_children) == ["test audio at 12v"]

    monkeypatch.setattr(
        "colloquy.machines.socket.gethostname", lambda: "DESKTOP-MRSLS88"
    )
    assert list(group.snapshot_children) == ["test audio at 12v"]


def test_the_supply_picker_shares_the_subsystems_params_key():
    """The same board on the same lead. Having chosen it once on one page
    only to be asked again on the next is the kind of small lie about the
    hardware this tree is meant not to tell."""
    from colloquy.tests.test_audio_at_12v import SupplyComPort
    from colloquy.tests.test_audio_subsystem import AudioComPort

    assert SupplyComPort.params_section == AudioComPort.params_section
    assert SupplyComPort.stand_in == AudioComPort.stand_in


# --- the pass that broke a module ----------------------------------------


def amplifier_double(module="GF1002", rated=5.0):
    """Only what `_why_not_measure` and `_measure` touch.

    `amplifier` is set outright rather than left to the property: a
    SimpleNamespace does not inherit one. What the property itself reads
    is pinned separately below, against the shipped defaults.
    """
    return SimpleNamespace(
        amplifier=(module, rated),
        is_started=False,
        _outcome=None,
        _supply=None,
        log=lambda *args, **kwargs: None,
        start=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("started a pass that should have been refused")
        ),
    )


def why_not(double, supply):
    return SupplyTest._why_not_measure(double, supply)


def test_a_pass_above_the_recorded_rating_is_refused():
    """2026-09-01: `measure at 12 V` was pressed with Thomas's GF1002s
    fitted and one died the instant the rail came up. The wiring was this
    test's own document's; what was wrong was a number nobody had a
    source for. docs/errors/2026-09-01-01.txt."""
    double = amplifier_double()

    refusal = why_not(double, "12 V")

    assert refusal is not None
    assert "GF1002" in refusal
    assert "5 V" in refusal and "12 V" in refusal


def test_the_pass_at_the_rail_it_survives_still_runs():
    """Refusing both would make the test dead rather than safe. It is
    exactly as runnable as the hardware allows."""
    assert why_not(amplifier_double(), "5 V") is None


def test_a_module_rated_for_the_rail_unblocks_it():
    """Which is the way back: fit one and record it. Never by editing a
    document."""
    wide = amplifier_double(module="something rated for it", rated=15.0)

    assert why_not(wide, "5 V") is None
    assert why_not(wide, "12 V") is None


def test_the_refusal_stops_the_pass_rather_than_only_reporting_it():
    """The double's `start` raises, so a refusal that fell through to it
    fails here rather than in a comment."""
    double = amplifier_double()
    double._why_not_measure = lambda supply: SupplyTest._why_not_measure(
        double, supply
    )

    outcome = SupplyTest._measure(double, "12 V")

    assert outcome.startswith("refused: ")
    assert double._outcome == outcome
    assert double._supply is None


def test_the_rating_is_read_out_of_params():
    """Instant, like the flasher's refusals: it runs on a page load, from
    the params entry alone, and touches no hardware to decide."""
    double = SimpleNamespace(
        params={"audio": {"amplifier module": "GF1002", "amplifier max supply volts": 5}}
    )

    assert SupplyTest.amplifier.fget(double) == ("GF1002", 5.0)


def test_every_supply_the_page_offers_has_a_voltage():
    """`SUPPLIES` is the labels and `SUPPLY_VOLTS` is what the refusal
    compares. A label without a voltage would be a pass nothing checks."""
    from colloquy.tests.test_audio_at_12v import SUPPLY_VOLTS

    assert set(SUPPLIES) == set(SUPPLY_VOLTS)


def test_the_shipped_default_refuses_the_twelve_volt_pass():
    """What a fresh params.json does, which is the whole of the
    protection: the number ships at the rail the module is known to
    survive, not at the one somebody hoped for."""
    from colloquy.params import DEFAULTS

    shipped = SimpleNamespace(params={"audio": DEFAULTS["audio"]})
    double = amplifier_double(*SupplyTest.amplifier.fget(shipped))

    assert why_not(double, "12 V") is not None
    assert why_not(double, "5 V") is None
