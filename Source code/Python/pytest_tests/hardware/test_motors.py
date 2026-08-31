# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_motors.py

"""Taking the Dynamixel chain off without losing the calibration.

What is worth pinning here is an *order* and an *omission*, and both are
easy to break from a distance:

- the note is written before the homing, so a homing that fails halfway
  still leaves the next start knowing (`main_pcb.unmount`'s rule);
- the in-run latch is set after it, because a guard reading the note
  would skip the very move that protects the turn count;
- and this must not call `power_down()`, whose first step latches the
  class-level `_shutdown` event and makes every later `start()` in the
  process a silent no-op.

`Motors` is built against a duck-typed owner rather than a real
`Colloquy` (see conftest: never build the real object graph).
"""
from pathlib import Path
from types import SimpleNamespace

from colloquy.hardware.motors import Motors


class FakeColloquy:
    """What `Motors` asks of the root: params, and the two servo steps."""

    def __init__(self, arrived=True):
        self.params = {"motors": {"plugged in": True, "unplugged at": ""}}
        self.done = []
        self._arrived = arrived

    def move_to_origin(self):
        # Recorded with the note as it stands *at the moment of the move*,
        # which is what the ordering test reads.
        self.done.append(("home", self.params["motors"]["plugged in"]))
        return self._arrived

    def disable_torque(self):
        self.done.append(("torque off", None))


class FakeThread:
    def __init__(self, name, parts):
        self.name = name
        self.path = SimpleNamespace(parts=parts)
        self.stopped = False
        self.joined = False

    def stop(self):
        self.stopped = True

    def join(self):
        self.joined = True


def make_motors(arrived=True, threads=()):
    """A Motors node on a fake owner, with a fake set of running threads."""
    colloquy = FakeColloquy(arrived=arrived)
    owner = SimpleNamespace(colloquy=colloquy, path=Path("hardware"))

    motors = Motors.__new__(Motors)
    motors._dict = {}
    motors._owner = owner
    motors._were_unplugged = False
    motors._outcome = None
    motors._log = lambda *a, **k: None
    motors._all_threads = set(threads)
    return motors, colloquy


# `Base` reaches its logger and thread registry through machinery a bare
# double does not have, so those two are patched on the instance above.
# Everything else under test is the node's own code.


def _patch(monkeypatch, node):
    monkeypatch.setattr(type(node), "log", property(lambda self: self._log))
    monkeypatch.setattr(
        type(node), "all_threads", property(lambda self: self._all_threads)
    )


# --- the order the steps happen in ---------------------------------------


def test_the_note_is_written_before_anything_is_moved(monkeypatch):
    """main_pcb.unmount's rule. A power-down that fails halfway must still
    leave the next start knowing the chain is going away."""
    node, colloquy = make_motors()
    _patch(monkeypatch, node)

    node.unplug()

    # The move saw the note already written.
    assert ("home", False) in colloquy.done


def test_everything_is_homed_before_torque_is_cut(monkeypatch):
    """Cutting torque first would leave every body wherever it stood, which
    is the outcome the whole sequence exists to avoid."""
    node, colloquy = make_motors()
    _patch(monkeypatch, node)

    node.unplug()

    steps = [step for step, _ in colloquy.done]
    assert steps.index("home") < steps.index("torque off")


def test_the_in_run_latch_is_set_only_after_the_homing(monkeypatch):
    """The note and the latch cannot be one thing: the note is written
    first, so a guard reading it would skip the move that protects the
    turn count. Before the unplug the latch is False; the move still ran."""
    node, colloquy = make_motors()
    _patch(monkeypatch, node)

    assert node.were_unplugged_this_run is False
    node.unplug()

    assert node.were_unplugged_this_run is True
    assert any(step == "home" for step, _ in colloquy.done)


# --- what it must not do -------------------------------------------------


def test_it_does_not_shut_the_process_down(monkeypatch):
    """`power_down()` opens with BaseThread.shutdown(), which sets the
    class-level _shutdown event - after which every start() in the process
    returns immediately. Right for /shutdown, fatal here: the reason to
    unplug the motors is to power something else and go on testing it from
    this same page."""
    node, colloquy = make_motors()
    _patch(monkeypatch, node)

    # The double has no shutdown/join_all at all, so reaching for one raises.
    assert not hasattr(colloquy, "shutdown")
    assert not hasattr(colloquy, "join_all")

    node.unplug()


def test_only_what_drives_the_piece_is_stopped(monkeypatch):
    """Filed by where a thread hangs in the tree, the same filter as the
    flasher's IN_THE_WAY. `Repository` is started by main.py on every run
    and never touches a servo; stopping it would end the origin watch for
    the rest of the session."""
    search = FakeThread("female1 search", ("drivers", "female1", "search"))
    test = FakeThread("test search", ("tests", "test search"))
    repository = FakeThread("repository", ("repository",))
    node, _ = make_motors(threads=(search, test, repository))
    _patch(monkeypatch, node)

    node.unplug()

    assert search.stopped and search.joined
    assert test.stopped and test.joined
    assert not repository.stopped


# --- what it says afterwards ---------------------------------------------


def test_a_bar_that_did_not_get_home_is_said_so(monkeypatch):
    """Silence here would be the worst outcome: the turn count is gone and
    only a measurement at the rig brings it back."""
    node, _ = make_motors(arrived=False)
    _patch(monkeypatch, node)

    node.unplug()

    assert "WARNING" in node._outcome
    assert "turn count" in node._outcome


def test_a_clean_unplug_says_it_is_safe_to_pull(monkeypatch):
    node, _ = make_motors()
    _patch(monkeypatch, node)

    node.unplug()

    assert "safe to unplug" in node._outcome


def test_unplugging_twice_moves_nothing(monkeypatch):
    """The second press meets a chain that is already off. Homing it would
    be commanding servos that are not there."""
    node, colloquy = make_motors()
    _patch(monkeypatch, node)

    node.unplug()
    colloquy.done.clear()
    node.unplug()

    assert colloquy.done == []
    assert "already noted as unplugged" in node._outcome


# --- putting them back ---------------------------------------------------


def test_the_chain_coming_back_is_a_deliberate_press(monkeypatch):
    """Nothing clears the note on its own, exactly as nothing clears the
    main PCB's: the alternative is an installation that quietly decides it
    can move when it cannot."""
    node, _ = make_motors()
    _patch(monkeypatch, node)

    node.unplug()
    assert node.is_plugged_in is False

    node.replug()
    assert node.is_plugged_in is True
    assert node.were_unplugged_this_run is False
    assert "Restart" in node._outcome


def test_the_page_offers_one_command_at_a_time(monkeypatch):
    """Offering "unplug" on a chain that is already off is offering a run
    that can only refuse."""
    node, _ = make_motors()
    _patch(monkeypatch, node)

    assert list(node.snapshot_children) == ["unplug the motors"]

    node.unplug()

    assert list(node.snapshot_children) == ["the motors are back"]
