"""Who starts a search, and - the new half - who stops one.

Two supervisory loops, neither of which could stop anything before:

- `Male.loop()` starts his search when an appetite is up and now stops it
  when both fall back below the interested floor. TJ's `Logic_male.ino`
  transmits only while `internal_drive_state` is not the inert one.
- `Bar.loop()` decides whether the bar is wandering, by watching the
  males' search flags. It has no appetite of its own, so that is the only
  thing that can tell it - and with nobody calling there is nothing for
  the rail to carry anywhere.

Called unbound against doubles exposing only what each loop touches (see
conftest): constructing a real Male or Bar reaches for a servo bus.
"""
from types import SimpleNamespace

from colloquy.drivers.bar import Bar
from colloquy.drivers.male import Male


class FakeSearch:
    """A search that records being started and stopped, without threads."""

    def __init__(self, is_started=False):
        self.is_started = is_started
        self.starts = []
        self.stops = 0

    def start(self, started_by=None):
        self.starts.append(started_by)
        self.is_started = True

    def stop(self):
        self.stops += 1
        self.is_started = False


def make_male(satisfied, searching):
    search = FakeSearch(is_started=searching)
    return SimpleNamespace(
        name="male1",
        search=search,
        is_satisfied=lambda: satisfied,
        log=lambda *args, **kwargs: None,
        # He now also checks whether anybody is singing his call back
        # before deciding to keep calling - see Male._answered_by. Nobody
        # is, in every test here: this file is about the search half.
        reinforcement=FakeSearch(),
        _answered_by=lambda: None,
    )


def make_bar(male_searching, bar_searching):
    search = FakeSearch(is_started=bar_searching)
    males = [
        SimpleNamespace(name=f"male{i + 1}", search=FakeSearch(is_started=flag))
        for i, flag in enumerate(male_searching)
    ]
    return SimpleNamespace(
        search=search,
        males=males,
        log=lambda *args, **kwargs: None,
    )


# --- the male ------------------------------------------------------------


def test_a_hungry_male_starts_calling():
    male = make_male(satisfied=False, searching=False)

    Male.loop(male)

    assert male.search.is_started is True
    assert male.search.starts == [male]


def test_a_male_already_calling_is_left_alone():
    male = make_male(satisfied=False, searching=True)

    Male.loop(male)

    assert male.search.starts == []
    assert male.search.stops == 0


def test_a_male_who_wants_nothing_stops_calling():
    """The half that was missing (CODE_DOCUMENTATION 1.2): he used to
    start the first time an appetite climbed and then call for the rest of
    the run, whatever his drives did afterwards."""
    male = make_male(satisfied=True, searching=True)

    Male.loop(male)

    assert male.search.stops == 1
    assert male.search.is_started is False


def test_a_satisfied_male_is_not_started():
    male = make_male(satisfied=True, searching=False)

    Male.loop(male)

    assert male.search.starts == []
    assert male.search.stops == 0


# --- the bar -------------------------------------------------------------


def test_the_bar_sets_off_when_a_male_calls():
    bar = make_bar(male_searching=(True, False), bar_searching=False)

    Bar.loop(bar)

    assert bar.search.is_started is True
    assert bar.search.starts == [bar]


def test_either_male_is_enough():
    # It used to `return` inside the loop over males, so this pins that
    # the second one counts as much as the first.
    bar = make_bar(male_searching=(False, True), bar_searching=False)

    Bar.loop(bar)

    assert bar.search.is_started is True


def test_the_bar_keeps_going_while_anyone_is_calling():
    bar = make_bar(male_searching=(True, True), bar_searching=True)

    Bar.loop(bar)

    assert bar.search.starts == []
    assert bar.search.stops == 0


def test_the_bar_stops_when_the_last_male_goes_quiet():
    """What lets the piece come to rest. Without it the first male to get
    hungry set the rail going for the rest of the run, sliding back and
    forth in front of nobody (CODE_DOCUMENTATION 4.1)."""
    bar = make_bar(male_searching=(False, False), bar_searching=True)

    Bar.loop(bar)

    assert bar.search.stops == 1
    assert bar.search.is_started is False


def test_a_stopped_bar_with_nobody_calling_stays_stopped():
    bar = make_bar(male_searching=(False, False), bar_searching=False)

    Bar.loop(bar)

    assert bar.search.starts == []
    assert bar.search.stops == 0


def test_the_bar_reads_the_search_flag_not_the_appetite():
    """Deliberate: a male whose drives just went quiet may still have a
    search thread winding down, and the rail should follow the thread. So
    the double here has no is_satisfied() at all - if Bar.loop() ever
    reaches for one, this raises."""
    bar = make_bar(male_searching=(True, False), bar_searching=False)
    assert not hasattr(bar.males[0], "is_satisfied")

    Bar.loop(bar)

    assert bar.search.is_started is True
