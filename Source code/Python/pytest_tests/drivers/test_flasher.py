"""What the flasher refuses to do, and why.

The refusals are the whole safety of this node. Flashing rewrites the
board that carries every light and every light sensor in the piece, from
a page anybody can open, and the ways it can go wrong are not
hypothetical: the installation has at least two USB serial leads in it
and the other one is the servo bus.

Called unbound against doubles, per conftest: `Flasher` is a BaseThread
hanging off a real `Arduino`, and neither is constructible here.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from colloquy.drivers.arduino.boards import Board
from colloquy.drivers.arduino.flasher import Flasher

MEGA = Board("COM7", "Arduino Mega 2560 (R3)", True, 0x2341, 0x0042, None)
U2D2 = Board("COM4", "FTDI FT232R - the U2D2 is an FTDI device", False, 0x0403, 0x6001, None)


class FakeThread:
    """A double for one running BaseThread, as `all_threads` yields them.

    A class rather than a SimpleNamespace because `all_threads` is a set
    and SimpleNamespace is not hashable.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name
        self.is_started = True

    def __repr__(self):
        return f"FakeThread({self.path.as_posix()})"


def thread(path):
    return FakeThread(path)


@pytest.fixture
def flasher(monkeypatch):
    """A Flasher double with everything clear: board mounted, a real Mega
    on the chosen port, nothing running."""
    import colloquy.drivers.arduino.flasher as module

    monkeypatch.setattr(module.boards, "detect", lambda ports=None: [MEGA, U2D2])

    fake = SimpleNamespace(
        colloquy=SimpleNamespace(
            hardware=SimpleNamespace(main_pcb=SimpleNamespace(is_mounted=True))
        ),
        port="COM7",
        all_threads=set(),
        IN_THE_WAY=Flasher.IN_THE_WAY,
        _threads_in_the_way=lambda: [],
        _outcome=None,
        _detail=None,
    )
    # The real thing calls its own refusal check from three places, so the
    # double has to be able to answer it as itself.
    fake._why_not_flash = lambda: Flasher._why_not_flash(fake)
    return fake


def why_not(flasher):
    return Flasher._why_not_flash(flasher)


# --- the five refusals ---------------------------------------------------


def test_all_clear_refuses_nothing(flasher):
    assert why_not(flasher) is None


def test_it_will_not_flash_a_board_that_has_been_taken_out(flasher):
    """`main pcb` says the board is physically out of the rack, so there
    is nothing on the end of the lead to write to."""
    flasher.colloquy.hardware.main_pcb.is_mounted = False

    assert "unmounted" in why_not(flasher)


def test_no_port_chosen_says_where_to_choose_one(flasher):
    flasher.port = None

    assert "com port" in why_not(flasher)


def test_a_port_this_machine_does_not_have_lists_the_ones_it_does(flasher):
    """params.json outlives the laptop that wrote it, so a remembered COM
    number is a normal thing to meet rather than a fault."""
    flasher.port = "COM99"

    refusal = why_not(flasher)

    assert "COM99" in refusal
    assert "COM7" in refusal


def test_it_refuses_to_flash_the_u2d2(flasher):
    """The one this exists for. Pointing avrdude at the servo bus is a
    thing a person does once, by choosing the wrong COM number, and the
    board detection already knows the difference by the chip on the
    board rather than by the number Windows handed out this week."""
    flasher.port = "COM4"

    refusal = why_not(flasher)

    assert "FTDI" in refusal
    assert "not a board to flash" in refusal


def test_it_refuses_while_the_piece_is_running(flasher):
    """The board spends twenty seconds in its bootloader, answering
    nothing. A female mid-pattern-read would simply read darkness."""
    flasher._threads_in_the_way = lambda: [thread("drivers/female1")]

    refusal = why_not(flasher)

    assert "female1" in refusal
    assert "bootloader" in refusal


# --- which threads count as in the way -----------------------------------


def in_the_way(*paths):
    fake = SimpleNamespace(
        all_threads={thread(path) for path in paths},
        IN_THE_WAY=Flasher.IN_THE_WAY,
    )
    return sorted(t.name for t in Flasher._threads_in_the_way(fake))


def test_a_body_is_in_the_way():
    assert in_the_way("drivers/female1", "drivers/male2/search") == ["female1", "search"]


def test_a_hardware_test_is_in_the_way():
    assert in_the_way("tests/test audio loop") == ["test audio loop"]


def test_the_git_watcher_is_not_in_the_way():
    """The bug this filter was written after. `Repository` is started by
    main.py on every run and never touches a serial port - refusing on
    "something is running" hid the flash link on the installation
    permanently, which is the one machine it is for.
    """
    assert in_the_way("repository") == []


def test_the_flasher_does_not_count_itself():
    """It hangs under `drivers` too, and it is running by definition at
    the moment it renders its own page - so without the `is not self` it
    would refuse on the grounds of its own existence."""
    me = thread("drivers/arduino/flash firmware")
    me.all_threads = {me}
    me.IN_THE_WAY = Flasher.IN_THE_WAY

    assert Flasher._threads_in_the_way(me) == []


def test_a_thread_at_the_root_with_no_path_parts_is_not_in_the_way():
    """`Base.path` is empty at the root, and `parts[0]` on it would
    raise rather than answer."""
    assert in_the_way("") == []


# --- what the page offers ------------------------------------------------


def test_the_flash_link_appears_only_when_it_would_do_something(flasher):
    """Same rule as `Repository.pull`: the node is quiet until there is a
    reason not to be, and the reason is on the reading beside it."""
    flasher.compile_only = lambda request=None: None
    flasher.flash = lambda request=None: None
    flasher._with_scenarios = lambda children: children

    offered = Flasher.snapshot_children.fget(flasher)
    assert "flash the board" in offered
    assert "compile only" in offered

    flasher.colloquy.hardware.main_pcb.is_mounted = False
    offered = Flasher.snapshot_children.fget(flasher)
    assert "flash the board" not in offered
    # The safe half stays: it touches nothing but a temporary folder, so
    # there is never a reason to withhold it.
    assert "compile only" in offered


def test_compiling_needs_no_board_at_all(flasher):
    """No refusals on the compile path - it is how you find out whether
    this machine has a working toolchain without gambling a board on the
    answer."""
    started = []
    flasher._begin = lambda job: started.append(job) or "compiling"
    flasher.colloquy.hardware.main_pcb.is_mounted = False
    flasher.port = None

    assert Flasher.compile_only(flasher) == "compiling"
    assert started == [("compile", None)]


def test_a_refused_flash_never_starts_the_thread(flasher):
    flasher.colloquy.hardware.main_pcb.is_mounted = False
    flasher._begin = lambda job: pytest.fail("should not have begun")

    answer = Flasher.flash(flasher)

    assert answer.startswith("refused:")
    assert flasher._outcome == answer
