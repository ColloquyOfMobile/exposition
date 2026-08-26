"""One test per fault shape, because the shapes are the whole design.

`TestAudioBringup` needs a board, two amplifiers, two microphones and a
room. This is the part of it that needs two lists of numbers - and it is
the part that has to be right on the afternoon somebody is standing over
a reworked PCB with a scope, because a diagnosis that sends them to the
wrong half of the chain costs more than no diagnosis at all.

Each test below builds the readings a particular fault would produce and
checks that the report names that fault. They are written from the fault
backwards, not from the code forwards.
"""
import pytest

from colloquy.drivers import audio
from colloquy.tests.test_audio_bringup import diagnosis

WIRED = ["female1", "male1"]
QUIET = 50
LOUD = 700


def sweep(loud=None):
    """Seven band values: quiet everywhere except the bands in `loud`.

    `loud` is a dict keyed by band *index*, which is why it is a
    positional dict rather than keyword arguments - a band index is an
    int and kwargs have to be strings.
    """
    values = [QUIET] * len(audio.BANDS_HZ)
    for index, value in (loud or {}).items():
        values[index] = value
    return tuple(values)


def sweeps(loud=None, count=6):
    """Several sweeps, each differing slightly - a live analyser never
    reads exactly the same thing twice, and `health` leans on that."""
    return [tuple(value + (n % 3) for value in sweep(loud)) for n in range(count)]


def band(body):
    return audio.band_of_body(body)


def working_run():
    """Both channels good: each voice heard in its own band by both ears."""
    floor = {name: sweeps() for name in WIRED}
    healths = [diagnosis.health(name, floor[name]) for name in WIRED]
    readings = []
    for singer in WIRED:
        tone = {name: sweeps({band(singer): LOUD}) for name in WIRED}
        for listener in WIRED:
            readings.append(
                diagnosis.read(singer, listener, floor[listener], tone[listener])
            )
    return healths, readings


# --- stage one: does the ear answer at all -------------------------------


def test_a_live_ear_reads_alive():
    health = diagnosis.health("female1", sweeps())

    assert health.ok
    assert "alive" in health.verdict
    assert health.module == 0


def test_a_floating_input_reads_pinned_high_and_says_which_pin():
    """The commonest bring-up fault of all: the analyser output never
    reached the ADC row, so the pin is floating."""
    health = diagnosis.health("male1", [(1023,) * 7] * 4)

    assert not health.ok
    assert "pinned high" in health.verdict
    assert "A3" in health.verdict


def test_a_dead_module_reads_pinned_low():
    health = diagnosis.health("female1", [(0,) * 7] * 4)

    assert not health.ok
    assert "pinned low" in health.verdict


def test_a_reading_that_never_changes_is_frozen():
    """A live analyser never reads exactly the same seven numbers twice.
    One that does is not being read at all."""
    identical = [(40, 41, 42, 43, 44, 45, 46)] * 5

    health = diagnosis.health("female1", identical)

    assert not health.ok
    assert "frozen" in health.verdict


def test_no_sweeps_at_all_is_a_link_fault_not_a_hearing_one():
    assert diagnosis.health("female1", []).verdict == "no reading came back"


def test_a_quiet_room_does_not_look_like_a_broken_ear():
    """The trap this stage deliberately avoids. In silence the MSGEQ7's
    seven outputs legitimately sit at much the same low level, so 'all
    bands alike' is *normal* here - checking it would fail a working
    board in a quiet room, which is the worst possible first stage."""
    flat_but_alive = [(48, 48, 49, 48, 47, 48, 48), (49, 48, 48, 49, 48, 48, 47)]

    assert diagnosis.health("female1", flat_but_alive).ok


# --- stage two: which half of the chain -----------------------------------


def test_a_clean_run_says_so_and_asks_for_nothing():
    healths, readings = working_run()

    assert diagnosis.summarise(healths, readings, WIRED).startswith("all 4")
    steps = diagnosis.diagnose(healths, readings, WIRED)
    assert len(steps) == 1
    assert "worked" in steps[0]


def test_a_dead_ear_stops_the_report_before_anything_else():
    """Everything after stage one is a rise over a floor. A floor that is
    not being measured makes the rest of the run noise, so the report
    must not go on to blame voices."""
    healths = [
        diagnosis.health("female1", sweeps()),
        diagnosis.health("male1", [(1023,) * 7] * 4),
    ]

    steps = diagnosis.diagnose(healths, [], WIRED)

    assert any("male1's ear is not answering" in step for step in steps)
    assert any("J11 row 7-8" in step for step in steps)
    assert not any("speaking side" in step for step in steps)


def test_both_ears_dead_points_upstream_of_either():
    healths = [diagnosis.health(name, [(1023,) * 7] * 4) for name in WIRED]

    steps = diagnosis.diagnose(healths, [], WIRED)

    assert any("J9 35" in step for step in steps)


def test_a_voice_nobody_heard_asks_you_to_listen_first():
    """The one thing the software cannot do. A tone not being generated
    and a tone going into a dead amplifier are both silence; one second
    of listening splits the chain in half."""
    floor = {name: sweeps() for name in WIRED}
    healths = [diagnosis.health(name, floor[name]) for name in WIRED]
    readings = []
    # male1 is heard by both; female1 by neither.
    for listener in WIRED:
        readings.append(
            diagnosis.read("female1", listener, floor[listener], sweeps())
        )
        readings.append(
            diagnosis.read(
                "male1", listener, floor[listener], sweeps({band("male1"): LOUD})
            )
        )

    steps = diagnosis.diagnose(healths, readings, WIRED)
    joined = " ".join(steps)

    assert "female1 was not heard by any ear" in joined
    assert "Listen while 'hold female1' is on" in joined
    # And when you cannot hear it, it names the pin to scope and the
    # filter channel it should be feeding.
    assert "D11" in joined
    assert "160 Hz square wave" in joined
    assert "filter IN 160" in joined
    # male1 worked, so it is not accused of anything. Counted rather than
    # matched on "male1 ...": "female1 was heard by nobody" *contains*
    # "male1 was heard by nobody", which is the same female/male substring
    # collision that once turned "f2" into "femaleale2" in the simulator.
    assert joined.count("was not heard by any ear") == 1


def test_nothing_heard_at_all_names_what_the_channels_share():
    """Two separate investigations when one cause covers both is the
    expensive way round."""
    floor = {name: sweeps() for name in WIRED}
    healths = [diagnosis.health(name, floor[name]) for name in WIRED]
    readings = [
        diagnosis.read(singer, listener, floor[listener], sweeps())
        for singer in WIRED
        for listener in WIRED
    ]

    joined = " ".join(diagnosis.diagnose(healths, readings, WIRED))

    assert "power to the amplifiers" in joined
    assert "J4 4" in joined
    assert "volume pots" in joined


# --- the strobe, which is the subtle one ---------------------------------


def test_sound_arriving_without_bands_separating_is_the_strobe():
    """The multiplexer not advancing means all seven reads return one
    band. That looks like silence *unless* you notice the overall level
    rose - which is exactly the tell."""
    floor = {name: sweeps() for name in WIRED}
    healths = [diagnosis.health(name, floor[name]) for name in WIRED]
    # Every band up together: sound arrived, nothing separated.
    risen = [tuple(v + 200 for v in s) for s in sweeps()]
    readings = [
        diagnosis.read(singer, listener, floor[listener], risen)
        for singer in WIRED
        for listener in WIRED
    ]

    steps = diagnosis.diagnose(healths, readings, WIRED)
    joined = " ".join(steps)

    assert "multiplexer is not advancing" in joined
    assert "D4" in joined and "D3" in joined
    assert "never one ear" in joined
    # It stops there: with the bands not separating, nothing about which
    # voice was heard means anything yet.
    assert len(steps) == 1


def test_plain_silence_is_not_blamed_on_the_strobe():
    """The other side of the same test. Nothing arriving must not be
    reported as a mux fault - the level did not rise."""
    floor = {name: sweeps() for name in WIRED}
    healths = [diagnosis.health(name, floor[name]) for name in WIRED]
    readings = [
        diagnosis.read(singer, listener, floor[listener], sweeps())
        for singer in WIRED
        for listener in WIRED
    ]

    joined = " ".join(diagnosis.diagnose(healths, readings, WIRED))

    assert "multiplexer" not in joined


# --- wrong band, and crossed channels ------------------------------------


def test_a_voice_that_lands_in_some_band_is_never_sent_to_a_scope():
    """A tone that peaked anywhere is being generated and is reaching a
    microphone, whatever band it landed in - so its speaking side works.
    Sending somebody to scope the pin of a voice that plainly came out is
    the most expensive kind of wrong."""
    floor = {name: sweeps() for name in WIRED}
    healths = [diagnosis.health(name, floor[name]) for name in WIRED]
    # female1's tone arrives, but in male1's band. male1's is fine.
    readings = []
    for listener in WIRED:
        readings.append(
            diagnosis.read(
                "female1", listener, floor[listener], sweeps({band("male1"): LOUD})
            )
        )
        readings.append(
            diagnosis.read(
                "male1", listener, floor[listener], sweeps({band("male1"): LOUD})
            )
        )

    joined = " ".join(diagnosis.diagnose(healths, readings, WIRED))

    assert "not heard by any ear" not in joined
    assert "Scope" not in joined
    assert "wrong filter channel" in joined


def test_a_tone_in_the_wrong_band_is_called_a_frequency_not_a_room():
    floor = {name: sweeps() for name in WIRED}
    healths = [diagnosis.health(name, floor[name]) for name in WIRED]
    wrong = sweeps({band("male1"): LOUD})
    readings = [
        diagnosis.read("female1", listener, floor[listener], wrong)
        for listener in WIRED
    ]
    readings += [
        diagnosis.read(
            "male1", listener, floor[listener], sweeps({band("male1"): LOUD})
        )
        for listener in WIRED
    ]

    joined = " ".join(diagnosis.diagnose(healths, readings, WIRED))

    assert "arrived at 2500 Hz instead of 160 Hz" in joined
    assert "not the room" in joined
    assert "wrong filter channel" in joined


def test_two_voices_in_each_others_bands_are_named_as_crossed():
    """The fault that is invisible by ear: both tones come out, both land
    in a real band, and the two are simply exchanged."""
    floor = {name: sweeps() for name in WIRED}
    healths = [diagnosis.health(name, floor[name]) for name in WIRED]
    readings = []
    for listener in WIRED:
        readings.append(
            diagnosis.read(
                "female1", listener, floor[listener], sweeps({band("male1"): LOUD})
            )
        )
        readings.append(
            diagnosis.read(
                "male1", listener, floor[listener], sweeps({band("female1"): LOUD})
            )
        )

    steps = diagnosis.diagnose(healths, readings, WIRED)
    joined = " ".join(steps)

    assert "arrived in each other's bands" in joined
    assert "crossed" in joined
    # And nothing else. A crossed pair makes every pair in the grid read
    # silent, so a report built by listing symptoms opens with two walls
    # of "scope this pin" and buries the one sentence that explains them
    # at the bottom. Somebody holding a scope reads from the top.
    assert len(steps) == 2
    assert "Scope" not in joined
    assert "volume pot" not in joined


def test_one_body_alone_cannot_be_crossed_with_anything():
    """The crossed check needs two. With one channel wired it must not
    invent a partner."""
    floor = {"female1": sweeps()}
    healths = [diagnosis.health("female1", floor["female1"])]
    readings = [
        diagnosis.read(
            "female1", "female1", floor["female1"], sweeps({band("female1"): LOUD})
        )
    ]

    steps = diagnosis.diagnose(healths, readings, ["female1"])

    assert "crossed" not in " ".join(steps)
    assert "worked" in steps[0]


# --- the reading itself ---------------------------------------------------


def test_a_rise_smaller_than_the_margin_is_not_a_tone():
    floor = sweeps()
    barely = sweeps({band("female1"): QUIET + diagnosis.MARGIN - 5})

    assert diagnosis.read("female1", "female1", floor, barely).verdict == "silent"


def test_the_loudest_rise_wins_rather_than_merely_a_rise():
    values = {band("female1"): QUIET + diagnosis.MARGIN + 10, band("male1"): LOUD}

    reading = diagnosis.read("female1", "male1", sweeps(), sweeps(values))

    assert reading.verdict.startswith("wrong band")


def test_mean_bands_of_nothing_is_none_rather_than_zeros():
    """A missing sweep must not average to a floor of zero, which would
    make the next tone look enormous."""
    assert diagnosis.mean_bands([]) is None


@pytest.mark.parametrize("body", sorted(audio.VOICES))
def test_every_body_can_be_diagnosed_not_just_the_two_wired_today(body):
    """The third channel goes in tomorrow and the fourth after it."""
    floor = sweeps()
    health = diagnosis.health(body, floor)
    reading = diagnosis.read(body, body, floor, sweeps({band(body): LOUD}))

    assert health.ok
    assert reading.heard
