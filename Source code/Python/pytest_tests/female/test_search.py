"""Unit tests for colloquy.hardware.female.search.Search.

Per CLAUDE.md ("Male blink pattern / female pattern reading"), Search.loop()
and Search.setup() are documented, deliberate stubs: females currently move
via Female.turn_back_and_forth instead of Search's own thread, and nothing
wires up Search's thread automatically, so both methods unconditionally
`raise NotImplementedError("use the turn_back_and_forth thread")`. These
tests lock that behaviour down as a regression guard - they are NOT trying
to "fix" or work around it.

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
import pytest

from colloquy.hardware.female.search import Search
from colloquy.hardware.female.search.read_pattern import ReadPattern


def make_search(stub_factory):
    owner = stub_factory(name="female1", owners=[])
    return Search(owner=owner)


def test_loop_raises_not_implemented(stub_factory):
    search = make_search(stub_factory)

    with pytest.raises(NotImplementedError):
        search.loop()


def test_setup_raises_not_implemented(stub_factory):
    search = make_search(stub_factory)

    with pytest.raises(NotImplementedError):
        search.setup()


def test_setdown_is_a_noop(stub_factory):
    search = make_search(stub_factory)

    # Unlike loop()/setup(), setdown() is *not* stubbed out - it should
    # just do nothing (no NotImplementedError, no exception at all).
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
