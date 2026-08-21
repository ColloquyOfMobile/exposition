"""Unit tests for colloquy.drivers.female.search.Search.

Search is the female's live search behaviour: setup() starts her
ReadPattern child, and loop() sways her between her min/max positions
whenever she isn't already moving - the mirror of the male's own search.

(Both methods used to be deliberate stubs raising NotImplementedError,
which crashed every female's thread within two ticks; the tests below were
originally regression guards for *that*. They now lock in the working
behaviour instead.)

Search.__init__ eagerly builds its ReadPattern child (the `read_pattern`
property is called once from __init__ to register it as a dict-like
child), and ReadPattern.__init__ only sets plain instance attributes, a
threading.Lock, and an empty deque - no filesystem/serial/thread access -
so constructing the real Search class directly against a stub owner is
safe and simpler than the unbound-method-double pattern.

Note: ReadPattern.name reads `self.owner.owner.name` (owner = the Search
instance, owner.owner = Search's own owner), so the stub owner passed to
Search needs a `.name` attribute for construction to succeed.
"""
from types import SimpleNamespace

from colloquy.base_thread import BaseThread
from colloquy.drivers.female.search import Search
from colloquy.drivers.female.search.read_pattern import ReadPattern


def make_search(stub_factory):
    owner = stub_factory(name="female1", owners=[])
    return Search(owner=owner)


def test_setup_starts_read_pattern(stub_factory):
    # Never call the real .start() in this suite (see conftest) - it would
    # spawn a thread. Record the call instead.
    search = make_search(stub_factory)
    starters = []
    search.read_pattern.start = lambda started_by=None: starters.append(started_by)

    search.setup()

    assert starters == [search], "read_pattern must be started by search itself"


def test_loop_sways_the_body_when_it_is_still(stub_factory):
    search = make_search(stub_factory)
    toggled = []
    search.owner.is_moving = False
    search.owner.toggle_position = lambda: toggled.append(True)

    search.loop()

    assert toggled == [True]


def test_loop_leaves_a_moving_body_alone(stub_factory):
    search = make_search(stub_factory)
    toggled = []
    search.owner.is_moving = True
    search.owner.toggle_position = lambda: toggled.append(True)

    search.loop()

    assert toggled == []


def test_setdown_is_a_noop(stub_factory):
    search = make_search(stub_factory)

    # setdown() does nothing: read_pattern stops itself once it notices
    # search (its started_by) is no longer running.
    assert search.setdown() is None


def test_name_is_search(stub_factory):
    search = make_search(stub_factory)

    assert search.name == "search"


def test_read_pattern_child_is_built_and_registered(stub_factory):
    search = make_search(stub_factory)

    assert isinstance(search.read_pattern, ReadPattern)
    assert search[search.read_pattern.name] is search.read_pattern


def test_read_pattern_is_memoized(stub_factory):
    search = make_search(stub_factory)

    assert search.read_pattern is search.read_pattern


def test_snapshot_children_exposes_read_pattern(stub_factory):
    search = make_search(stub_factory)

    children = search.snapshot_children

    assert children[search.read_pattern.name] is search.read_pattern
    # And what she looks like doing it, beside the start that begins it.
    assert children["scenarios"].names == ("female-looking",)
    assert set(children) == {search.read_pattern.name, "scenarios"}


def make_search_with_drives(stub_factory, wants, last_match=None, moving=True):
    """A real Search whose owner exposes just what loop() touches: her
    drive state, whether she is moving, and her ReadPattern's last match."""
    owner = stub_factory(
        name="female1",
        owners=[],
        is_moving=moving,
        toggle_position=lambda: None,
        drives=SimpleNamespace(which_is_frustated=lambda: wants),
    )
    search = Search(owner=owner)
    # Swap the real ReadPattern for a stand-in rather than patching its
    # class: a property set on the class would leak into every other test
    # in this file.
    search._read_pattern = SimpleNamespace(
        name="read pattern female1",
        last_match=last_match,
        start=lambda started_by=None: None,
    )
    return search


def test_she_answers_a_male_who_wants_what_she_wants(stub_factory):
    search = make_search_with_drives(stub_factory, wants=("O",),
                                     last_match=("male1", ("O",)))
    stopped = []
    search.stop = lambda: stopped.append(True)

    search.loop()

    assert search.partner == ("male1", "O")
    assert stopped == [True], "finding a partner ends the search"


def test_she_ignores_a_male_asking_for_something_else(stub_factory):
    # TJ switches on her own drive state and lets every match outside it
    # fall through - she keeps looking rather than answering.
    search = make_search_with_drives(stub_factory, wants=("O",),
                                     last_match=("male1", ("P",)))
    stopped = []
    search.stop = lambda: stopped.append(True)

    search.loop()

    assert search.partner is None
    assert stopped == []


def test_a_male_offering_both_gives_her_the_one_she_wants(stub_factory):
    search = make_search_with_drives(stub_factory, wants=("P",),
                                     last_match=("male2", ("O", "P")))
    search.stop = lambda: None

    search.loop()

    assert search.partner == ("male2", "P")


def test_when_both_want_both_the_shared_drive_differs_per_male(stub_factory):
    # Logic_fem.ino case 4: male I gives O, male II gives P, so two males
    # don't always end up sharing the same drive.
    for male, expected in (("male1", "O"), ("male2", "P")):
        search = make_search_with_drives(stub_factory, wants=("O", "P"),
                                         last_match=(male, ("O", "P")))
        search.stop = lambda: None

        search.loop()

        assert search.partner == (male, expected)


def test_a_female_short_of_nothing_answers_nobody(stub_factory):
    search = make_search_with_drives(stub_factory, wants=tuple(),
                                     last_match=("male1", ("O", "P")))
    search.stop = lambda: None

    search.loop()

    assert search.partner is None


def test_taking_the_partner_clears_it(stub_factory):
    # One find is acted on once: Female.loop() consumes it when handing it
    # to reinforcement.
    search = make_search_with_drives(stub_factory, wants=("O",),
                                     last_match=("male1", ("O",)))
    search.stop = lambda: None
    search.loop()

    assert search.take_partner() == ("male1", "O")
    assert search.take_partner() is None


def test_she_keeps_swaying_while_she_looks(stub_factory):
    swayed = []
    search = make_search_with_drives(stub_factory, wants=("O",), moving=False)
    search.owner.toggle_position = lambda: swayed.append(True)

    search.loop()

    assert swayed == [True]


def test_starting_a_search_forgets_the_previous_find(stub_factory, monkeypatch):
    # Cleared in start(), synchronously, not in setup() on the new thread:
    # a caller that starts a search and then moves bodies around before
    # looking would otherwise read the previous run's answer for as long
    # as that takes - which read as an instant find the moment a second
    # run began.
    search = make_search_with_drives(stub_factory, wants=("O",),
                                     last_match=("male1", ("O",)))
    search.stop = lambda: None
    search.loop()
    assert search.partner == ("male1", "O")

    # Stop at Search.start()'s own work; spawning a thread is BaseThread's
    # business and this suite never does it.
    monkeypatch.setattr(BaseThread, "start", lambda self, started_by=None: None)

    search.start()

    assert search.partner is None
