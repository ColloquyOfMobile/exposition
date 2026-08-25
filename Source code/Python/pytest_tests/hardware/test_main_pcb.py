"""Taking the main PCB out without losing the calibration.

The board carries both serial links, so unmounting it disconnects the
Arduino and the U2D2 together. Two things have to be true afterwards:
everything is at its origin (a servo powered down away from it loses its
turn count), and the next start knows the board is gone rather than
failing to open two ports that are not there.

It lives under `hardware` rather than `drivers`: that section is the
physical installation - a board and whether it is in the rack - as
opposed to the layer that drives the piece.

`MainPCB` is a plain `Base` over one params entry, so it builds against a
stub owner - no bus, no filesystem beyond the dict it is handed.
"""
from types import SimpleNamespace

from colloquy.hardware.main_pcb import MainPCB


def make_pcb(mounted=True, unmounted_at="", arrived=True, has_server=True):
    """A MainPCB over a throwaway params dict and a recording colloquy."""
    done = []
    params = {"main pcb": {"mounted": mounted, "unmounted at": unmounted_at}}

    colloquy = SimpleNamespace(
        params=params,
        power_down=lambda: (done.append("powered down"), arrived)[1],
        request_stop=lambda: (done.append("asked to stop"), has_server)[1],
    )
    owner = SimpleNamespace(owners=[], colloquy=colloquy, name="hardware")
    pcb = MainPCB(owner=owner)
    pcb._log = lambda *a, **k: None
    pcb.done = done
    pcb.stored = params["main pcb"]
    return pcb


# --- the note ------------------------------------------------------------


def test_a_new_installation_believes_the_board_is_in():
    assert make_pcb().is_mounted is True


def test_unmounting_writes_the_note():
    pcb = make_pcb()

    pcb.unmount()

    assert pcb.stored["mounted"] is False
    assert pcb.stored["unmounted at"], "when it happened is worth recording"
    assert pcb.is_mounted is False


def test_the_note_is_written_before_anything_is_moved():
    """Order on purpose: a shutdown that fails halfway still leaves the
    next start knowing the board is going away."""
    pcb = make_pcb()
    written = []
    real = pcb.params

    class Watched(dict):
        def __setitem__(self, key, value):
            written.append((key, len(pcb.done)))
            super().__setitem__(key, value)

    pcb.colloquy.params["main pcb"] = Watched(real)

    pcb.unmount()

    # Both writes happened while nothing had been done yet.
    assert [count for _key, count in written] == [0, 0]


def test_remounting_clears_it():
    pcb = make_pcb(mounted=False, unmounted_at="2026-08-25T10:00:00")

    pcb.remount()

    assert pcb.stored["mounted"] is True
    assert pcb.stored["unmounted at"] == ""


def test_nothing_clears_the_note_on_its_own():
    """A board that is out stays out until somebody says otherwise - the
    alternative is an installation that quietly decides it has hardware
    when it has not."""
    pcb = make_pcb(mounted=False, unmounted_at="2026-08-25T10:00:00")

    pcb.is_mounted
    pcb._snapshot_if_opened(("hardware", "main pcb"))

    assert pcb.stored["mounted"] is False


# --- what unmounting actually does ---------------------------------------


def test_unmounting_homes_everything_and_stops_the_server():
    pcb = make_pcb()

    message = pcb.unmount()

    assert pcb.done == ["powered down", "asked to stop"]
    assert "unmounted" in message
    assert "reached its origin" in message


def test_unmounting_warns_when_something_did_not_get_home():
    """The one thing somebody about to pull a cable needs told."""
    pcb = make_pcb(arrived=False)

    message = pcb.unmount()

    assert "WARNING" in message
    assert "check the bar" in message


def test_unmounting_says_so_when_there_is_no_server_to_stop():
    pcb = make_pcb(has_server=False)

    message = pcb.unmount()

    assert "close the process by hand" in message


# --- the page ------------------------------------------------------------


def test_only_the_command_that_makes_sense_is_offered():
    mounted = make_pcb(mounted=True)
    assert "unmount the main PCB" in mounted.snapshot_children
    assert "the main PCB is back" not in mounted.snapshot_children

    out = make_pcb(mounted=False)
    assert "the main PCB is back" in out.snapshot_children
    assert "unmount the main PCB" not in out.snapshot_children


def test_the_state_is_readable_at_a_glance():
    path = ("hardware", "main pcb")

    mounted = make_pcb(mounted=True)._snapshot_if_opened(path)
    assert mounted["state"]["value"] == "mounted"

    out = make_pcb(mounted=False, unmounted_at="2026-08-25T10:00:00")
    states = out._snapshot_if_opened(path)
    assert "UNMOUNTED" in states["state"]["value"]
    assert "2026-08-25T10:00:00" in states["state"]["value"]
    # And what that means for anybody wondering why nothing moves.
    assert "not opened at startup" in states["what that means"]["value"]


def test_an_unmounted_board_with_no_recorded_date_still_reads():
    states = make_pcb(mounted=False, unmounted_at="")._snapshot_if_opened(
        ("hardware", "main pcb")
    )

    assert "unknown" in states["state"]["value"]
