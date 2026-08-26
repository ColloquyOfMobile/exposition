"""The rule scenarios are filed by, held to.

A scenario describes what the artwork does, second by second, in what is
visible in the room - and it is filed against the thing that starts that
behaviour: wherever the page offers a start(), it also says what will
happen. Every BaseThread declares its own in `scenario_names`, and
BaseThread hangs them beside its start link, so nothing has to remember
to list them in snapshot_children.

Three things can go wrong silently, and each has a test here:
- a declared name with no file behind it (a rename that missed one) -
  the page would draw an empty document rather than raise;
- a file nothing declares - a scenario that has fallen out of the tree
  and can only be found by opening the folder;
- a new thread quietly joining the set that nobody has described. That
  last one is a ratchet rather than a failure: WITHOUT_SCENARIOS below is
  the list as it stands, so adding a thread means either writing a
  scenario or putting it on the list on purpose.

Importing colloquy is enough to reach every thread class - none are
constructed here (see conftest).
"""
import colloquy  # noqa: F401 - imports the whole tree of thread classes
from colloquy.base_thread import BaseThread
from colloquy.scenario_browser import (
    Scenarios,
    all_scenario_names,
    scenario_path,
)


def thread_classes():
    """Every BaseThread subclass the package defines, by qualified name.

    "the package defines" is now enforced rather than assumed.
    `__subclasses__()` sees every subclass that has been *imported*, and
    a test elsewhere in this suite may perfectly well subclass a thread
    to fake one property of it (test_repository does). Those would
    otherwise land in the ratchet below as threads nobody has written a
    scenario for, and only when that test module happened to be
    collected first - which is the worst kind of failure to be handed.
    """
    found = {}

    def walk(cls):
        for sub in cls.__subclasses__():
            if sub.__module__.split(".")[0] == "colloquy":
                found[f"{sub.__module__}.{sub.__name__}"] = sub
            walk(sub)

    walk(BaseThread)
    return found


# Threads with nothing written about them yet. Shrinking this list is the
# work; growing it is a decision.
#
# Every hardware test under colloquy/tests/ is off it: they are startable
# from the page like anything else, and what one of them does to the room
# for the next forty minutes is exactly the kind of thing somebody
# standing in front of the installation needs told.
#
# Of the seven left, three are deliberate and will stay: read_pattern and
# blink have no appearance of their own in the room - what they do is
# described inside their parent's scenario, since a female reading and a
# female swaying are one thing to watch - and the repository watch does
# nothing in the room at all, being a git fetch every five minutes. The
# other four are a real backlog: the exposition thread, a female's light
# sensor and her reinforcement, and the bar's own plain back-and-forth.
#
# A male's light sensors are absent from this list because they are plain
# Base nodes, not threads - only a female's reads on a loop - and
# colloquy.tests.test1 is absent because nothing imports it (see the
# commented-out line in tests/__init__.py).
WITHOUT_SCENARIOS = {
    "colloquy.exposition.Exposition",
    "colloquy.drivers.female.light_sensor.LightSensor",
    "colloquy.drivers.female.reinforcement.Reinforcement",
    "colloquy.drivers.female.search.read_pattern.ReadPattern",
    "colloquy.drivers.male.search.blink.Blink",
    "colloquy.drivers.bar.turn_back_and_forth.TurnBackAndForth",
    "colloquy.repository.Repository",
    "colloquy.drivers.arduino.flasher.Flasher",
}


# --- the two directions of the mapping -----------------------------------


def test_every_declared_scenario_is_on_disk():
    missing = []
    for name, cls in thread_classes().items():
        for scenario in cls.scenario_names:
            if not scenario_path(scenario).is_file():
                missing.append(f"{name} -> {scenario}")

    assert missing == []


def test_every_scenario_on_disk_is_claimed_by_something():
    claimed = set()
    for cls in thread_classes().values():
        claimed.update(cls.scenario_names)

    orphans = sorted(set(all_scenario_names()) - claimed)

    assert orphans == []


def test_the_files_are_named_and_suffixed_as_scenarios():
    # They were *.timeline under colloquy/tests/timelines/ until the word
    # was given back to the artist's meaning of it.
    for name in all_scenario_names():
        path = scenario_path(name)
        assert path.suffix == ".scenario"
        assert path.parent.name == "scenarios"
        assert path.parent.parent.name == "colloquy"


# --- coverage of the start() rule ----------------------------------------


def test_the_threads_without_a_scenario_are_the_ones_we_know_about():
    without = {
        name for name, cls in thread_classes().items() if not cls.scenario_names
    }

    assert without == WITHOUT_SCENARIOS


def test_the_whole_piece_owns_the_encounters_no_single_thread_starts():
    # A male calling and a female looking each have a thread behind them.
    # The two of them meeting has none: it happens when a wandering bar
    # and a turning female line up, so it hangs off the piece itself.
    from colloquy import Colloquy

    assert "a-male-calls-a-female" in Colloquy.scenario_names
    assert "the-satisfaction-moment" in Colloquy.scenario_names
    assert "an-answer-in-sound" in Colloquy.scenario_names


def test_the_three_females_share_one_scenario():
    # Named for a behaviour, not for a node - which is what stops three
    # near-identical files from drifting apart.
    from colloquy.drivers.female.search import Search

    assert Search.scenario_names == ("female-looking",)


# --- the node itself -----------------------------------------------------


def test_a_thread_carries_only_the_scenarios_it_declares(stub_factory):
    node = Scenarios(owner=stub_factory(), names=("male-calling", "male-body"))

    assert list(node.snapshot_children) == ["male-calling", "male-body"]
    assert node.name == "scenarios"


def test_the_same_scenario_node_comes_back_between_requests(stub_factory):
    # Rebuilt children would lose the open/closed state the page keeps on
    # them between one request and the next.
    node = Scenarios(owner=stub_factory(), names=("male-calling",))

    first = node.snapshot_children["male-calling"]
    second = node.snapshot_children["male-calling"]

    assert first is second


def test_a_declared_name_with_no_file_reads_as_empty(stub_factory):
    # Shown as an empty document rather than skipped: a scenario renamed
    # away should be noticed, and the test above is what notices it.
    node = Scenarios(owner=stub_factory(), names=("nothing-of-the-sort",))

    assert node.snapshot_children["nothing-of-the-sort"].read() == ""


def test_a_thread_that_declares_nothing_still_builds(stub_factory):
    assert Scenarios(owner=stub_factory(), names=()).snapshot_children == {}


def test_every_declaring_thread_routes_to_its_scenarios():
    """The bug this test exists for.

    The scenarios were first hung off `_snapshot_if_opened`, which is what
    draws a thread's page - so the link appeared, and clicking it gave
    404. `colloquy/ui/tree.py` walks `snapshot_children`, so that is the
    dict a child has to be in to be reachable. Found on the simulator, one
    click after the front page.

    Checked on the class rather than an instance: `snapshot_children` is a
    property, so what is asserted is that its source calls the helper -
    building a real thread here would mean building the object graph
    (see conftest).
    """
    import inspect

    missing = []
    for name, cls in thread_classes().items():
        if not cls.scenario_names:
            continue
        source = inspect.getsource(cls.snapshot_children.fget)
        if "_with_scenarios" not in source:
            missing.append(name)

    assert missing == []
