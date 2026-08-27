"""What one ear made of one voice, in a word.

`TestAudioLoop` itself needs an Arduino, five speakers and a room. This is
the part of it that needs two tuples of numbers, and it is the part worth
being sure about: every one of the four words sends somebody looking in a
different place, so a verdict that is merely *plausible* costs an
afternoon at the installation.
"""
from colloquy.drivers import audio
from colloquy.tests.test_audio_loop import verdicts

MARGIN = 60

# Quiet everywhere. Seven bands, since that is what the analyser answers.
FLOOR = (50,) * len(audio.BANDS_HZ)


def reading(band, level, floor=FLOOR):
    """The floor with one band raised."""
    values = list(floor)
    values[band] = level
    return tuple(values)


# --- the four words ------------------------------------------------------


def test_a_voice_arriving_in_its_own_band_is_heard():
    heard = reading(audio.band_of_body("female2"), 800)

    assert verdicts.verdict(FLOOR, heard, "female2", MARGIN) == "heard"


def test_nothing_rising_is_silent():
    assert verdicts.verdict(FLOOR, FLOOR, "female2", MARGIN) == "silent"


def test_a_rise_smaller_than_the_margin_is_still_silent():
    """The margin is here to reject drift and room noise, not to measure
    anything - so a band that crept up by less than it is not a tone."""
    barely = reading(audio.band_of_body("female2"), 50 + MARGIN - 1)

    assert verdicts.verdict(FLOOR, barely, "female2", MARGIN) == "silent"


def test_a_voice_arriving_somewhere_else_names_the_band_it_arrived_in():
    """The most useful of the four and the least likely: it means a body
    is wired to another body's filter channel, or an ear to the wrong
    analog input. Naming the band is what turns it into an instruction."""
    wrong = reading(audio.band_of_body("male1"), 800)

    result = verdicts.verdict(FLOOR, wrong, "female2", MARGIN)

    assert result.startswith("wrong band")
    assert f"{audio.VOICES['male1']['hz']} Hz" in result


def test_a_missing_sweep_is_a_broken_link_not_a_broken_chain():
    assert verdicts.verdict(None, FLOOR, "female2", MARGIN) == "no reading"
    assert verdicts.verdict(FLOOR, None, "female2", MARGIN) == "no reading"
    assert verdicts.verdict((), (), "female2", MARGIN) == "no reading"


# --- the order the two questions are asked in ----------------------------


def test_a_tone_at_the_wrong_frequency_is_not_reported_as_silence():
    """The bug this ordering exists to avoid. Asking "did the expected
    band rise" first makes a tone coming out at the wrong pitch report as
    silent, which sends somebody to look at the amplifier when the fault
    is in the timer."""
    wrong = reading(audio.band_of_body("male2"), 900)

    assert verdicts.verdict(FLOOR, wrong, "female1", MARGIN) != "silent"


def test_the_loudest_rise_wins_not_merely_a_rise():
    """A little energy leaking into the right band while a lot arrives in
    the wrong one is a wrong band, not a success."""
    values = list(FLOOR)
    values[audio.band_of_body("female1")] = 50 + MARGIN + 10
    values[audio.band_of_body("male2")] = 900

    assert verdicts.verdict(FLOOR, tuple(values), "female1", MARGIN).startswith(
        "wrong band"
    )


def test_a_noisy_floor_is_subtracted_rather_than_ignored():
    """Every reading is a rise over that ear's own silence, so an ear
    sitting next to a noisy fan is not thereby deaf."""
    noisy = list(FLOOR)
    noisy[audio.band_of_body("male2")] = 900
    noisy = tuple(noisy)

    # The same 900 is still there while female1 sings - it has not risen.
    heard = list(noisy)
    heard[audio.band_of_body("female1")] = 800

    assert verdicts.verdict(noisy, tuple(heard), "female1", MARGIN) == "heard"


# --- the summary line ----------------------------------------------------


def test_a_clean_run_says_so_in_one_line():
    all_heard = {(a, b): "heard" for a in "12345" for b in "12345"}

    assert verdicts.summarise(all_heard) == "all 25 voice/ear pairs heard"


def test_a_failed_run_lists_only_the_pairs_that_failed():
    results = {("female1", "male2"): "silent", ("female1", "female1"): "heard"}

    summary = verdicts.summarise(results)

    assert summary.startswith("1/2 heard")
    assert "female1 -> male2: silent" in summary
    assert "female1 -> female1" not in summary


def test_a_run_that_measured_nothing_does_not_claim_success():
    """`heard == total` is true of an empty grid, and "all 0 pairs heard"
    on a run that never got a reading would be the worst line here."""
    assert verdicts.summarise({}) == "nothing was measured"
