# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_reinforcement.py

"""The second half of the interaction: what happens when a pair meets.

Until this was written a female recognised a male and then stopped, and
nothing in the installation came of a match - `Reinforcement` raised on
its first tick and said so. The exchange is TJ's (`Logic_fem.ino`,
`Logic_male.ino`, and the `an-answer-in-sound` scenario): she sings his
own pattern back, he answers with his `R`, and every round takes a fixed
amount off the appetite they share until it is gone.

**The ears are emulated** (`drivers/hearing/`), because the microphones
are not in service. That is a real limitation and it is what these tests
are written against: they pin the *behaviour*, and they cannot say
anything about whether a microphone would have heard it.

Threads are never started here - `loop()`, `setup()` and `setdown()` are
called by hand against small doubles, the way conftest.py describes.
"""
from types import SimpleNamespace

import pytest

from colloquy import Colloquy
from colloquy.drivers.female.reinforcement import Reinforcement as FemaleReinforcement
from colloquy.drivers.hearing import Hearing
from colloquy.drivers.male import Male
from colloquy.drivers.male.reinforcement import Reinforcement as MaleReinforcement

PATTERNS = Colloquy.light_patterns.fget(None)


def pattern(male, drive):
    return PATTERNS[male][(drive,) if drive else tuple()]


class FakeSing:
    """A `Sing` that records what it was asked to send."""

    def __init__(self, transmitting=False, bits=()):
        self.pattern = ()
        self.bits = tuple(bits)
        self.is_transmitting = transmitting
        self.started = 0
        self.stopped = 0

    def start(self, started_by=None):
        self.started += 1
        self.bits = tuple(self.pattern)
        self.is_transmitting = True

    def stop(self):
        self.stopped += 1
        self.is_transmitting = False


class FakeDrive:
    def __init__(self, value=100):
        self.value = value
        self.decreases = 0
        self.last_amount = None
        import contextlib

        self.lock = contextlib.nullcontext()

    def decrease(self, amount=None):
        self.decreases += 1
        self.last_amount = amount
        self.value = max(0, self.value - (20 if amount is None else amount))

    @property
    def is_satisfied(self):
        return self.value < 12.5


class FakeSatisfaction:
    """The six-second moment, recorded rather than run."""

    def __init__(self):
        self.about_args = None
        self.started = 0
        self.stopped = 0

    def about(self, male_name, drive_name):
        self.about_args = (male_name, drive_name)

    def start(self, started_by=None):
        self.started += 1

    def stop(self):
        self.stopped += 1


def body(name, sing=None):
    return SimpleNamespace(name=name, sing=sing or FakeSing())


# --- the emulated ears ---------------------------------------------------


def hearing(*bodies):
    node = Hearing.__new__(Hearing)
    node._bodies = {b.name: b for b in bodies}
    return node


def test_a_body_hears_whoever_is_singing():
    her = body("female1")
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))

    assert hearing(her, him).heard_by(her) == ("male1", pattern("male1", None))


def test_nobody_listens_to_their_own_voice():
    """TJ's `sense_sound_active = false` while transmitting - it is why a
    male never decodes his own R as an answer (CODE_DOCUMENTATION 9.12)."""
    her = body("female1", FakeSing(transmitting=True, bits=(1,) * 10))
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))

    assert hearing(her, him).heard_by(her) is None


def test_silence_between_bursts_is_not_a_voice():
    """A `Sing` in its 2.35s gap is not singing, and that gap is part of
    the message."""
    her = body("female1")
    him = body("male1", FakeSing(transmitting=False, bits=pattern("male1", None)))

    assert hearing(her, him).heard_by(her) is None


def test_hears_is_exact_about_who_and_what():
    her = body("female1")
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))
    ears = hearing(her, him)

    assert ears.hears(her, "male1", pattern("male1", None))
    assert not ears.hears(her, "male2", pattern("male1", None))
    assert not ears.hears(her, "male1", pattern("male1", "O"))


def test_the_page_says_the_ears_are_emulated():
    """The same rule as `drivers > arduino` saying which board it drives:
    a run that works here is not evidence a microphone would have heard
    it."""
    ears = hearing(body("female1"))

    assert ears.is_emulated is True


# --- her half ------------------------------------------------------------


def female_reinforcement(partner=("male1", "O"), drive_value=100):
    node = FemaleReinforcement.__new__(FemaleReinforcement)
    node.partner = partner
    node._last_heard = None
    node._satisfied_at = None
    node._rounds = 0
    drive = FakeDrive(drive_value)
    her = body("female1")
    node._owner = SimpleNamespace(
        name="female1",
        sing=her.sing,
        turn_to_origin=lambda: None,
        drives=SimpleNamespace(o_drive=drive, p_drive=FakeDrive(100)),
        colloquy=SimpleNamespace(light_patterns=PATTERNS),
        drivers=SimpleNamespace(hearing=None),
        # TJ gives each female her own decrement - see params.
        reinforcement_decrement=25,
        satisfaction=FakeSatisfaction(),
    )
    node._log = lambda *args, **kwargs: None
    node.drive = drive
    return node


def test_she_sings_his_own_pattern_back_at_him():
    """Not a message of her own: his identity with the one appetite named
    that they share."""
    node = female_reinforcement(partner=("male2", "P"))

    FemaleReinforcement.setup(node)

    assert node.female.sing.pattern == pattern("male2", "P")
    assert node.female.sing.started == 1


def test_she_refuses_to_start_without_a_partner():
    """A reinforcement with nobody to reinforce with is a bug, not a
    quiet no-op."""
    node = female_reinforcement(partner=None)

    with pytest.raises(ValueError):
        FemaleReinforcement.setup(node)


def test_hearing_his_R_takes_the_shared_appetite_down():
    node = female_reinforcement()
    FemaleReinforcement.setup(node)
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))
    node.female.sing.is_transmitting = False
    node.female.drivers.hearing = hearing(node.female, him)

    FemaleReinforcement.loop(node)

    assert node.rounds == 1
    assert node.drive.decreases == 1


def test_his_call_is_not_his_R_and_does_not_reinforce():
    """She waits for one specific message. A male still calling is not
    answering her."""
    node = female_reinforcement()
    FemaleReinforcement.setup(node)
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", "O")))
    node.female.sing.is_transmitting = False
    node.female.drivers.hearing = hearing(node.female, him)

    FemaleReinforcement.loop(node)

    assert node.rounds == 0


def test_enough_rounds_zero_the_drive_and_open_the_satisfaction_moment():
    """TJ zeroes it outright rather than leaving it under the floor, so
    the moment is a real reset and not a body hungry again in seconds."""
    node = female_reinforcement(drive_value=30)
    FemaleReinforcement.setup(node)
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))
    node.female.sing.is_transmitting = False
    node.female.drivers.hearing = hearing(node.female, him)

    for _ in range(3):
        FemaleReinforcement.loop(node)

    assert node.drive.value == 0
    assert node.is_satisfied_moment
    # And she stops singing: there is nothing more to say to him.
    assert node.female.sing.stopped >= 1


def test_she_gives_up_when_the_answer_stops_coming():
    node = female_reinforcement()
    FemaleReinforcement.setup(node)
    node.female.sing.is_transmitting = False
    node.female.drivers.hearing = hearing(node.female)
    stopped = []
    node.stop = lambda: stopped.append(True)
    node._last_heard -= FemaleReinforcement.PATIENCE + 1

    FemaleReinforcement.loop(node)

    assert stopped == [True]


def test_her_patience_is_tjs_number():
    """205 ticks of his 50 ms clock - long enough to sit through two
    bursts and the silences around them."""
    assert FemaleReinforcement.PATIENCE == pytest.approx(10.25)
    assert FemaleReinforcement.SATISFACTION == pytest.approx(6.0)


# --- his half ------------------------------------------------------------


def male_reinforcement(partner=("female1", "O")):
    node = MaleReinforcement.__new__(MaleReinforcement)
    node.partner = partner
    node._last_heard = None
    node._satisfied_at = None
    node._rounds = 0
    drive = FakeDrive(100)
    him = body("male1")
    ring = SimpleNamespace(
        color=None, on=lambda: None, off=lambda: None, set=lambda v: None
    )
    node._owner = SimpleNamespace(
        name="male1",
        sing=him.sing,
        ring=ring,
        turn_to_origin=lambda: None,
        drives=SimpleNamespace(o_drive=drive, p_drive=FakeDrive(100)),
        colloquy=SimpleNamespace(light_patterns=PATTERNS),
        drivers=SimpleNamespace(hearing=None),
        # A stand-in for the light he would have collected - see params.
        reinforcement_decrement=17,
        satisfaction=FakeSatisfaction(),
    )
    node._log = lambda *args, **kwargs: None
    node.drive = drive
    return node


def test_he_answers_with_his_R_and_nothing_else():
    """The seventh message, one per male, and the only thing a male ever
    sings."""
    node = male_reinforcement()

    MaleReinforcement.setup(node)

    assert node.male.sing.pattern == pattern("male1", None)


def test_he_keeps_going_while_she_keeps_singing_his_call_back():
    node = male_reinforcement()
    MaleReinforcement.setup(node)
    her = body("female1", FakeSing(transmitting=True, bits=pattern("male1", "O")))
    node.male.sing.is_transmitting = False
    node.male.drivers.hearing = hearing(node.male, her)

    MaleReinforcement.loop(node)

    assert node.rounds == 1
    assert node.drive.decreases == 1


def test_he_ignores_a_reply_meant_for_the_other_male():
    node = male_reinforcement()
    MaleReinforcement.setup(node)
    her = body("female1", FakeSing(transmitting=True, bits=pattern("male2", "O")))
    node.male.sing.is_transmitting = False
    node.male.drivers.hearing = hearing(node.male, her)

    MaleReinforcement.loop(node)

    assert node.rounds == 0


# --- and what starts his half ---------------------------------------------


def male_listening(frustrated=("O",), heard=None):
    """A male mid-search, with the ears reporting `heard`."""
    return SimpleNamespace(
        name="male1",
        drives=SimpleNamespace(which_is_frustated=lambda: frustrated),
        colloquy=SimpleNamespace(light_patterns=PATTERNS),
        drivers=SimpleNamespace(
            hearing=SimpleNamespace(heard_by=lambda body: heard)
        ),
    )


def test_his_own_call_sung_back_is_an_answer():
    fake = male_listening(heard=("female1", pattern("male1", "O")))

    assert Male._answered_by(fake) == ("female1", "O")


def test_silence_is_not_an_answer():
    assert Male._answered_by(male_listening(heard=None)) is None


def test_another_males_call_is_not_an_answer():
    """Which is the whole of TJ's test, and the reason two males calling
    at once do not steal each other's replies."""
    fake = male_listening(heard=("female1", pattern("male2", "O")))

    assert Male._answered_by(fake) is None


def test_an_appetite_he_no_longer_wants_is_not_an_answer():
    fake = male_listening(
        frustrated=("P",), heard=("female1", pattern("male1", "O"))
    )

    assert Male._answered_by(fake) is None


# --- one round per burst, not one per tick -------------------------------


def test_a_burst_counts_once_however_often_the_loop_asks():
    """The defect the simulator found.

    The loop runs every few milliseconds and a burst sounds for two
    seconds. Counting every yes took a full appetite to nothing in four
    seconds; TJ counts a *match*, and his receiver produces one per
    pattern.
    """
    node = female_reinforcement()
    FemaleReinforcement.setup(node)
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))
    node.female.sing.is_transmitting = False
    node.female.drivers.hearing = hearing(node.female, him)

    for _ in range(50):
        FemaleReinforcement.loop(node)

    assert node.rounds == 1
    assert node.drive.decreases == 1


def test_the_next_burst_counts_again():
    """The silence between bursts is what separates two messages - which
    is the same thing it does on the light channel."""
    node = female_reinforcement()
    FemaleReinforcement.setup(node)
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))
    node.female.sing.is_transmitting = False
    node.female.drivers.hearing = hearing(node.female, him)

    for _ in range(20):
        FemaleReinforcement.loop(node)
    him.sing.is_transmitting = False          # his 2.35s of silence
    for _ in range(20):
        FemaleReinforcement.loop(node)
    him.sing.is_transmitting = True           # and the next burst
    for _ in range(20):
        FemaleReinforcement.loop(node)

    assert node.rounds == 2


def test_his_half_counts_bursts_the_same_way():
    node = male_reinforcement()
    MaleReinforcement.setup(node)
    her = body("female1", FakeSing(transmitting=True, bits=pattern("male1", "O")))
    node.male.sing.is_transmitting = False
    node.male.drivers.hearing = hearing(node.male, her)

    for _ in range(50):
        MaleReinforcement.loop(node)

    assert node.rounds == 1


# --- what a round is worth, and when appetites stand still ---------------


def test_each_female_takes_her_own_amount_off():
    """TJ's `FEMALE_reinforcement_decrement` is 1200, 600 and 1200 on his
    0-4800 scale, so 25, 12.5 and 25 here. Not all the same on purpose:
    female2 needs twice as many rounds and holds a partner twice as
    long."""
    node = female_reinforcement()
    node.female.reinforcement_decrement = 12.5
    FemaleReinforcement.setup(node)
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))
    node.female.sing.is_transmitting = False
    node.female.drivers.hearing = hearing(node.female, him)

    FemaleReinforcement.loop(node)

    assert node.drive.last_amount == 12.5
    assert node.drive.value == 87.5


def test_the_male_uses_his_own_figure_too():
    node = male_reinforcement()
    MaleReinforcement.setup(node)
    her = body("female1", FakeSing(transmitting=True, bits=pattern("male1", "O")))
    node.male.sing.is_transmitting = False
    node.male.drivers.hearing = hearing(node.male, her)

    MaleReinforcement.loop(node)

    assert node.drive.last_amount == 17


def test_the_five_decrements_are_in_params():
    """One table, and the two males are marked in it as a stand-in for the
    light they would have collected."""
    from colloquy.params import DEFAULTS

    decrements = DEFAULTS["reinforcement decrement"]

    assert decrements["female1"] == 25
    assert decrements["female2"] == 12.5
    assert decrements["female3"] == 25
    assert set(decrements) == {"female1", "female2", "female3", "male1", "male2"}


class FakeReinforcementState:
    def __init__(self, is_started, is_satisfied_moment):
        self.is_started = is_started
        self.is_satisfied_moment = is_satisfied_moment


def body_in(is_started, moment):
    from colloquy.drivers.female import Female

    fake = SimpleNamespace(reinforcement=FakeReinforcementState(is_started, moment))
    return Female.is_in_satisfaction_moment.fget(fake)


def test_a_body_in_its_moment_says_so():
    assert body_in(True, True) is True


def test_a_body_merely_reinforcing_is_not_in_the_moment():
    assert body_in(True, False) is False


def test_the_flag_does_not_outlive_the_thread():
    """Reinforcement keeps `_satisfied_at` after it ends, so without the
    `is_started` half a body would never be hungry again."""
    assert body_in(False, True) is False


def test_an_appetite_stands_still_during_the_moment():
    """TJ calls incrementInternalDrives() only in the *else* of
    `if (internal_satisfaction)` - so for those six seconds a body is not
    getting hungry again, and the moment is not being undone while it is
    still being shown."""
    from colloquy.drivers.drive import Drive

    climbed = []
    fake = SimpleNamespace(
        body=SimpleNamespace(is_in_satisfaction_moment=True),
        increment=lambda: climbed.append(1),
        _update_interval=0.0,
    )

    Drive.loop(fake)

    assert climbed == []


def test_an_appetite_climbs_the_rest_of_the_time():
    from colloquy.drivers.drive import Drive

    climbed = []
    fake = SimpleNamespace(
        body=SimpleNamespace(is_in_satisfaction_moment=False),
        increment=lambda: climbed.append(1),
        _update_interval=0.0,
    )

    Drive.loop(fake)

    assert climbed == [1]


# --- the six seconds afterwards -------------------------------------------


def test_both_note_tables_are_exactly_the_moment_long():
    """TJ's two tables both sum to 120 ticks of his 50 ms clock, which is
    the six seconds. A table that did not would leave a body mid-note when
    the moment ended."""
    from colloquy.drivers import satisfaction

    for male, ticks in satisfaction.DURATIONS.items():
        assert sum(ticks) == satisfaction.TOTAL_TICKS, male
        assert len(ticks) == len(satisfaction.NOTES_HZ), male


def test_male1_taps_evenly_and_male2_swings():
    """The two rhythms are the whole difference between the two males'
    moments, and which male it was decides the rhythm the pair keeps."""
    from colloquy.drivers import satisfaction

    even = satisfaction.DURATIONS["male1"]
    swung = satisfaction.DURATIONS["male2"]

    assert set(even[:12]) == {5}          # a quarter second a note
    assert even[-3:] == (10, 20, 30)      # then held: 0.5s, 1s, 1.5s
    assert swung[:4] == (10, 5, 10, 5)    # long-short-long-short
    assert swung[-1] == 15                # and only the last held


def test_a_female_keeps_her_partners_rhythm_not_her_own():
    """`internal_partner_ID` in Logic_fem.ino. It is what puts the two of
    them in step without either following the other."""
    from colloquy.drivers.satisfaction import durations_for

    assert durations_for("male1") != durations_for("male2")
    # She is handed the male's name, so she gets his table.
    assert durations_for("male1")[0] == 5 * 0.05


def test_the_notes_walk_in_order_and_then_stop():
    from colloquy.drivers.satisfaction import DURATION, note_at

    assert note_at(0.0, "male1")[0] == 0
    assert note_at(0.2, "male1")[0] == 0          # 5 ticks is 0.25s
    assert note_at(0.3, "male1")[0] == 1
    assert note_at(DURATION - 0.01, "male1")[0] == 14
    assert note_at(DURATION + 0.01, "male1") is None


def test_each_note_is_a_ramp_from_dark_to_full():
    """Her brightness is TJ's `(timer_satisfactionanimation * 256) /
    act_satisfaction_Duration` - a ramp across the note, not a step."""
    from colloquy.drivers.satisfaction import note_at

    _index, at_start = note_at(0.0, "male1")
    _index, part_way = note_at(0.12, "male1")

    assert at_start == 0.0
    assert 0.4 < part_way < 0.6


def test_she_is_started_with_his_rhythm_and_their_colour():
    node = female_reinforcement(drive_value=20)
    FemaleReinforcement.setup(node)
    him = body("male1", FakeSing(transmitting=True, bits=pattern("male1", None)))
    node.female.sing.is_transmitting = False
    node.female.drivers.hearing = hearing(node.female, him)

    FemaleReinforcement.loop(node)

    assert node.is_satisfied_moment
    assert node.female.satisfaction.about_args == ("male1", "O")
    assert node.female.satisfaction.started == 1


def test_he_is_started_with_his_own_rhythm():
    node = male_reinforcement()
    node.drive.value = 10          # one round finishes him
    MaleReinforcement.setup(node)
    her = body("female1", FakeSing(transmitting=True, bits=pattern("male1", "O")))
    node.male.sing.is_transmitting = False
    node.male.drivers.hearing = hearing(node.male, her)

    MaleReinforcement.loop(node)

    assert node.male.satisfaction.about_args == ("male1", "O")
    assert node.male.satisfaction.started == 1
