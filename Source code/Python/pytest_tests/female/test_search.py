"""Unit tests for colloquy.hardware.female.search.Search.

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
from colloquy.hardware.female.search import Search
from colloquy.hardware.female.search.read_pattern import ReadPattern


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

    assert search.snapshot_children == {
        search.read_pattern.name: search.read_pattern
    }
