"""`test_search`'s own logic: what counts as a miss, and how an event reads.

The miss is the whole reason that test exists - `test_read_pattern` holds
a pair still and so can only ever answer "yes, eventually" - so the span
bookkeeping that produces one is worth pinning here, where it can be
driven by a clock instead of by a bar.

`_track_view_span` and `_close_view_span` are called unbound against a
double carrying only the three dicts they touch (see conftest): building
a real TestSearch reaches for a result folder and the whole driver tree.
"""
from types import SimpleNamespace

from colloquy.light_pattern_timing import CYCLE_DURATION
# Aliased away from the Test* prefix: pytest tries to collect any
# module-level class called Test<something> and warns that it cannot,
# because this one takes constructor arguments.
from colloquy.tests.test_search import TestSearch as SearchRun
from colloquy.tests.test_search import events


def make_test(female_name="female1"):
    """Everything the span methods touch, and no more."""
    logged = []

    fake = SimpleNamespace(
        _view_span={female_name: None},
        _log_miss=lambda female, male, seconds, now: logged.append(
            (female.name, male, round(seconds, 1))
        ),
    )
    # _track_view_span calls its sibling when a different male arrives, so
    # the double carries the real one bound to itself rather than a stub -
    # otherwise the handover test would pass against a method that never
    # ran.
    fake._close_view_span = lambda female, now: SearchRun._close_view_span(
        fake, female, now
    )
    fake.logged = logged
    return fake


def female(name="female1"):
    return SimpleNamespace(name=name)


def male(name="male1"):
    return SimpleNamespace(name=name)


# --- opening and extending a span ----------------------------------------


def test_a_span_opens_when_a_male_comes_into_view():
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, male(), now=100.0)

    assert test._view_span["female1"] == ["male1", 100.0, 0, False]


def test_nothing_opens_when_nobody_is_in_view():
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, None, now=100.0)

    assert test._view_span["female1"] is None


def test_the_same_male_extends_the_span_rather_than_restarting_it():
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, male(), now=100.0)
    SearchRun._track_view_span(test, f, male(), now=101.0)

    # Still timed from when he arrived, or she would never accumulate
    # enough view for a miss to be possible.
    assert test._view_span["female1"][1] == 100.0


# --- what makes it a miss -------------------------------------------------


def test_a_long_silent_span_is_a_miss_while_it_is_still_open():
    """Reported during the run, not only when he leaves: a female who
    never reads anybody should show up on the page while somebody is
    still standing there to notice."""
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, male(), now=100.0)
    SearchRun._track_view_span(test, f, male(), now=100.0 + events.MISS_AFTER)

    assert test.logged == [("female1", "male1", round(events.MISS_AFTER, 1))]


def test_a_span_is_only_ever_reported_once():
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, male(), now=100.0)
    for extra in (events.MISS_AFTER, events.MISS_AFTER + 5, events.MISS_AFTER + 30):
        SearchRun._track_view_span(test, f, male(), now=100.0 + extra)

    assert len(test.logged) == 1


def test_a_short_span_is_not_a_miss():
    """She may simply have arrived in the gap between two bursts. Two
    whole cycles is the bar precisely so that the marginal ones are not
    counted."""
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, male(), now=100.0)
    SearchRun._close_view_span(test, f, now=100.0 + CYCLE_DURATION)

    assert test.logged == []


def test_a_long_span_that_ends_silently_is_a_miss():
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, male(), now=100.0)
    SearchRun._close_view_span(test, f, now=100.0 + events.MISS_AFTER + 1)

    assert len(test.logged) == 1


def test_a_span_she_read_in_is_never_a_miss():
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, male(), now=100.0)
    test._view_span["female1"][2] += 1  # _log_read counts the decode here
    SearchRun._close_view_span(test, f, now=100.0 + events.MISS_AFTER + 10)

    assert test.logged == []


def test_a_different_male_closes_the_span_and_opens_a_new_one():
    """The bar carried somebody else in. The first man's silence is still
    a miss, and the second one starts with a clean clock."""
    test, f = make_test(), female()

    SearchRun._track_view_span(test, f, male("male1"), now=100.0)
    SearchRun._track_view_span(
        test, f, male("male2"), now=100.0 + events.MISS_AFTER + 1
    )

    assert [row[1] for row in test.logged] == ["male1"]
    assert test._view_span["female1"][0] == "male2"
    assert test._view_span["female1"][1] == 100.0 + events.MISS_AFTER + 1


def test_the_miss_threshold_is_two_send_cycles():
    # Long enough that she cannot merely have arrived during a gap: a
    # male is dark for 2.35s of every 4.35s.
    assert events.MISS_AFTER == CYCLE_DURATION * 2
    assert events.MISS_AFTER > CYCLE_DURATION + 2.0


# --- how an event reads ---------------------------------------------------


def test_a_clean_read_says_so():
    reading = events.describe_read("female1", "male1", ("P",), "male1", ("P",))

    assert reading == "female1 read male1 wanting P - as expected"
    assert events.is_correct(reading)


def test_only_what_differs_is_named():
    assert events.describe_read("female1", "male1", ("P",), "male2", ("P",)) == (
        "female1 read male2 wanting P - expected male1"
    )
    assert events.describe_read("female1", "male1", ("P",), "male1", ("O",)) == (
        "female1 read male1 wanting O - expected P"
    )
    assert events.describe_read("female1", "male1", ("P",), "male2", ("O",)) == (
        "female1 read male2 wanting O - expected male1 wanting P"
    )


def test_reading_somebody_with_nobody_in_view_is_its_own_sentence():
    """Either the geometry is wrong about what she can see, or light is
    reaching her from somewhere unintended. Both are worth a distinct
    sentence rather than being filed as a wrong male."""
    reading = events.describe_read("female1", None, None, "male1", ("P",))

    assert reading == "female1 read male1 wanting P - nobody was in view"
    assert not events.is_correct(reading)


def test_both_appetites_read_as_both():
    assert events.drive_label(("O", "P")) == "both"
    assert events.drive_label(tuple()) == "nothing"
    assert events.drive_label(None) == "nothing"


def test_a_find_says_who_and_which_drive():
    assert events.describe_found("female1", "male1", "P") == (
        "female1 found male1 sharing the P drive - search restarted"
    )


def test_no_sentence_ever_contains_a_comma():
    """Every one of these is written as the last column of a CSV, so a
    comma in one splits the row. test_read_pattern lost a column to
    ('O', 'P') exactly this way, and the damage is invisible until
    somebody parses the results months later."""
    sentences = [
        events.describe_read("female1", "male1", ("O", "P"), "male2", ("O", "P")),
        events.describe_read("female1", None, None, "male1", ("O", "P")),
        events.describe_miss("female1", "male1", 9.0),
        events.describe_found("female1", "male1", "P"),
        events.drive_label(("O", "P")),
    ]
    for sentence in sentences:
        assert "," not in sentence, sentence


def test_a_miss_says_how_long_she_had_him():
    assert events.describe_miss("female2", "male1", 11.4) == (
        "female2 had male1 in view for 11s and read nothing"
    )


def test_the_tally_ignores_clean_reads_and_orders_by_how_often():
    rows = [
        (events.READ, "female1 read male1 wanting P - as expected"),
        (events.READ, "female1 read male2 wanting P - expected male1"),
        (events.READ, "female1 read male2 wanting P - expected male1"),
        (events.MISS, "female3 had male1 in view for 9s and read nothing"),
    ]

    lines = events.tally_lines(rows)

    assert len(lines) == 2
    assert lines[0].startswith("2 times")
    assert "expected male1" in lines[0]
    assert lines[1].startswith("once")
