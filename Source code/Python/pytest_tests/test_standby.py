# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_standby.py

"""The server while the main PCB is out of the rack.

With the board gone there is nothing to drive, so the tree is not served
at all: `/` answers with three things - the Gerbers, the KiCad projects,
and the press that says a board is back - and every address under `/app`
goes there. That gate is the whole of what keeps the drivers from being
activated, so it is what is pinned hardest: no path, no method and no
stale link reaches a node while the note says out.

The rest is the routes that page leads to, and the one rule they share:
nothing raised while answering one may leave, because outside a command
an exception emergency-stops the installation and takes the server down -
over a zip, or a manifest somebody merged badly.

Installation-side only (the mock has no board to take out), and no live
server: the methods are bound onto a double, `test_restart_link.py`'s
arrangement.
"""
import io
import json
import zipfile
from contextlib import contextmanager
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from colloquy.hardware.pcb_files import gerbers, kicad_projects
from colloquy.repository import Notice
from colloquy.server2 import Server2, standby, updates
from colloquy.server2.wsgi2 import WSGI2


class FakeMainPCB:
    def __init__(self, mounted, calls):
        self.is_mounted = mounted
        self.unmounted_at = "" if mounted else "2026-10-11"
        self._calls = calls

    def remount(self):
        self._calls.append("remount")
        self.is_mounted = True

    def unmount(self):
        self._calls.append("unmount")
        self.is_mounted = False
        return True


class FakeRepository:
    def __init__(self, auto_update=False, notice=None, running="abc1234 a commit"):
        self.auto_update = auto_update
        self.notice = notice
        self.running = running
        self.summary = "up to date with origin/Refactor"
        self.last_checked = "20s ago"
        self.restart_is_due = False
        self.git = SimpleNamespace(tracked=lambda folder: [])
        self.calls = []

    def restarting(self):
        self.calls.append("restarting")


class FakeColloquy:
    def __init__(self, mounted=False, repository=None):
        self.calls = []
        self.hardware = SimpleNamespace(main_pcb=FakeMainPCB(mounted, self.calls))
        self.repository = repository or FakeRepository()
        self.servos_were_opened = False

    def shutdown(self):
        self.calls.append("shutdown")

    def join_all(self):
        self.calls.append("join_all")

    @contextmanager
    def hold_commands(self):
        self.calls.append("held")
        yield True


# What `_parse` hands the rest of the request to. Recorded rather than
# run: what is under test is which of them a request reaches.
RECORDED = (
    "_parse_app",
    "_parse_post",
    "_parse_emergency_stop",
    "_parse_shutdown",
    "_parse_restart",
    "_parse_static",
    "_parse_virtual_panel",
)

BORROWED = (
    "_parse",
    "_parse_path",
    "_redirect",
    "_board_is_out",
    "_parse_standby",
    "_parse_mount_main_pcb",
    "_parse_unmount_main_pcb",
    "_parse_update_status",
    "_parse_download",
    "_download_gerbers",
    "_download_board",
    "_download_kicad",
    "_download_unavailable",
    "_commit",
    "_attachment",
    "_homing_lines",
)


class FakeWSGI:
    def __init__(self, mounted=False, repository=None):
        self.colloquy = FakeColloquy(mounted, repository)
        self.shutdown_event = Event()
        self.restart_event = Event()
        self.all_threads = set()
        self._root = Path("app")
        self._environ = {}
        self.reached = []
        self.logged = []
        for name in BORROWED:
            setattr(self, name, getattr(WSGI2, name).__get__(self))
        for name in RECORDED:
            setattr(self, name, self._recorder(name))

    def _recorder(self, name):
        def record(*args):
            self.reached.append((name,) + tuple(str(arg) for arg in args[-2:]))
            return "200 OK", [], b"the tree"

        return record

    def log(self, line):
        self.logged.append(line)

    def get(self, path, method="GET"):
        self._environ = {"PATH_INFO": path, "REQUEST_METHOD": method}
        return self._parse()


def header(headers, name):
    for key, value in headers:
        if key.lower() == name.lower():
            return value
    return None


# --- the gate ------------------------------------------------------------


def test_with_the_board_out_the_front_page_is_the_three_options():
    status, _headers, body = FakeWSGI(mounted=False).get("/")
    page = body.decode("utf-8")

    assert status.startswith("200")
    assert "The main PCB is out" in page
    assert 'href="/download/gerbers"' in page
    assert 'href="/download/kicad"' in page
    assert 'href="/mount-main-pcb"' in page


@pytest.mark.parametrize(
    "path",
    [
        "/app",
        "/app/drivers",
        "/app/drivers/female1/search/call/start",
        "/app/exposition/call/start",
        "/app/tests/autotests/test%20search/call/start",
        "/app/hardware/main%20pcb",
    ],
)
def test_no_address_reaches_the_tree_while_the_board_is_out(path):
    """What "the drivers are not activated" rests on. There is no Arduino
    and no servo bus behind any of these, and a link that reached a node
    would be a way to start a thread at hardware that is not there."""
    wsgi = FakeWSGI(mounted=False)

    status, headers, _body = wsgi.get(path)

    assert status.startswith("303")
    assert header(headers, "Location") == "/"
    assert wsgi.reached == []


def test_nor_does_a_post():
    """`save` is a command like any other, reached by another door."""
    wsgi = FakeWSGI(mounted=False)

    status, headers, _body = wsgi.get("/app/exposition/schedule/call/save", "POST")

    assert status.startswith("303") and header(headers, "Location") == "/"
    assert wsgi.reached == []


def test_with_the_board_in_the_usual_page_is_untouched():
    wsgi = FakeWSGI(mounted=True)

    wsgi.get("/")
    wsgi.get("/app/drivers/arduino")
    wsgi.get("/app/exposition/schedule/call/save", "POST")

    assert [reach[0] for reach in wsgi.reached] == [
        "_parse_app",
        "_parse_app",
        "_parse_post",
    ]


@pytest.mark.parametrize(
    "path, route",
    [
        ("/restart", "_parse_restart"),
        ("/shutdown", "_parse_shutdown"),
        ("/emergency-stop", "_parse_emergency_stop"),
        ("/static/update_watch.js", "_parse_static"),
    ],
)
def test_what_does_not_go_through_the_tree_is_answered_as_usual(path, route):
    """The gate is on the tree and on nothing else - the restart, the
    stop and the script the page itself loads all stay reachable."""
    wsgi = FakeWSGI(mounted=False)

    wsgi.get(path)

    assert [reach[0] for reach in wsgi.reached] == [route]


# --- the page ------------------------------------------------------------


def page_of(colloquy=None):
    return standby.page(colloquy or FakeColloquy()).decode("utf-8")


def test_the_page_says_since_when_and_what_that_means():
    page = page_of()

    assert "2026-10-11" in page
    assert "drivers are off" in page


def test_the_page_lists_every_board_with_what_an_order_form_asks():
    page = page_of()

    for board in gerbers.load():
        assert board.title in page
        assert board.size in page
        assert f'href="/pcb/{board.id}/fabrication"' in page
        assert f'href="/pcb/{board.id}/schematic"' in page
        assert f'src="/pcb/{board.id}/preview"' in page


def test_the_page_draws_no_emergency_stop_and_no_way_into_the_tree():
    """Nothing can move, so there is nothing to stop - and that press
    latches the shutdown event, which would silently end the one thread
    still running here: the watch that keeps this machine up to date."""
    page = page_of()

    assert "emergency-stop" not in page
    assert 'href="/app' not in page


def test_the_page_says_the_press_restarts_and_starts_nothing():
    page = page_of()

    assert "restarts" in page
    assert "Nothing starts moving by itself" in page


@pytest.mark.parametrize(
    "error", [gerbers.PackageError("no fabrication package"), RuntimeError("boom")]
)
def test_a_package_that_cannot_be_read_costs_only_its_own_section(monkeypatch, error):
    """This is the installation's front page for weeks. A manifest
    somebody merged badly must not be what takes down the page the other
    download and the way back are on."""

    def broken():
        raise error

    monkeypatch.setattr(gerbers, "load", broken)

    page = page_of()

    assert "Not available" in page and str(error) in page
    assert 'href="/download/kicad"' in page
    assert 'href="/mount-main-pcb"' in page


def test_nothing_else_on_the_page_can_take_it_down_either(monkeypatch):
    def broken(*args, **kwargs):
        raise OSError("disk went away")

    monkeypatch.setattr(kicad_projects, "summary", broken)
    colloquy = FakeColloquy()
    colloquy.repository = SimpleNamespace(auto_update=False, git=None)

    page = page_of(colloquy)

    assert "size unknown" in page
    assert "could not be read" in page
    assert 'href="/mount-main-pcb"' in page


def test_the_page_says_whether_this_machine_updates_itself():
    assert "automatic updates are off" in page_of()

    updating = FakeColloquy(repository=FakeRepository(auto_update=True))
    assert "restarts onto it by itself" in page_of(updating)


# --- saying the board is back --------------------------------------------


def test_mounting_writes_the_note_then_restarts():
    wsgi = FakeWSGI(mounted=False)

    status, _headers, body = wsgi.get("/mount-main-pcb")

    assert status.startswith("200")
    # The note first: a restart that came up before it was written would
    # come up into the standby page again.
    assert wsgi.colloquy.calls == ["remount", "shutdown", "join_all"]
    assert wsgi.shutdown_event.is_set() and wsgi.restart_event.is_set()
    page = body.decode("utf-8")
    assert "noted as mounted" in page
    assert "Nothing starts moving by itself" in page


def test_the_page_it_answers_with_comes_back_by_itself():
    """Sticky, because the process that drew it is on its way down and
    has nothing further to say - the script waits for a new one."""
    _status, _headers, body = FakeWSGI(mounted=False).get("/mount-main-pcb")
    page = body.decode("utf-8")

    assert 'data-phase="restarting"' in page and "data-sticky" in page
    assert f'data-boot="{updates.BOOT}"' in page
    assert "update_watch.js" in page
    # And a plain link, for a browser with no script.
    assert 'href="/"' in page


def test_mounting_twice_is_not_two_restarts():
    """A stale link, or that page loaded again after the restart."""
    wsgi = FakeWSGI(mounted=True)

    status, headers, _body = wsgi.get("/mount-main-pcb")

    assert status.startswith("303") and header(headers, "Location") == "/"
    assert wsgi.colloquy.calls == []
    assert not wsgi.restart_event.is_set()


def test_unmounting_twice_does_not_stop_the_server():
    """The second time it would do one thing only - end the process, on
    a machine whose front page is now the downloads and whose updates
    arrive only while it is up."""
    wsgi = FakeWSGI(mounted=False)

    status, headers, _body = wsgi.get("/unmount-main-pcb")

    assert status.startswith("303") and header(headers, "Location") == "/"
    assert wsgi.colloquy.calls == []
    assert not wsgi.shutdown_event.is_set()


def test_unmounting_a_mounted_board_still_does():
    wsgi = FakeWSGI(mounted=True)

    status, _headers, body = wsgi.get("/unmount-main-pcb")

    assert status.startswith("200")
    assert "unmount" in wsgi.colloquy.calls
    assert wsgi.shutdown_event.is_set()
    assert "the new PCB is mounted" in body.decode("utf-8")


# --- the downloads -------------------------------------------------------


def test_the_gerbers_come_as_one_attachment():
    status, headers, body = FakeWSGI().get("/download/gerbers")

    assert status.startswith("200")
    assert header(headers, "Content-Type") == "application/zip"
    assert header(headers, "Content-Disposition") == (
        'attachment; filename="colloquy-gerbers-abc1234.zip"'
    )
    assert header(headers, "Content-Length") == str(len(body))
    package = zipfile.ZipFile(io.BytesIO(body))
    assert "README.txt" in package.namelist()
    assert "abc1234" in package.read("README.txt").decode("utf-8")


def test_one_board_comes_as_the_zip_a_fab_takes():
    board = gerbers.load()[0]

    status, headers, body = FakeWSGI().get(f"/download/gerbers/{board.id}")

    assert status.startswith("200")
    assert board.zip_name in header(headers, "Content-Disposition")
    assert sorted(zipfile.ZipFile(io.BytesIO(body)).namelist()) == sorted(board.files)


def test_the_downloads_do_not_need_the_board_out():
    status, _headers, _body = FakeWSGI(mounted=True).get("/download/gerbers")

    assert status.startswith("200")


@pytest.mark.parametrize(
    "path", ["/download", "/download/nonesuch", "/download/gerbers/nonesuch"]
)
def test_a_download_that_does_not_exist_is_a_404_with_a_way_home(path):
    status, _headers, body = FakeWSGI().get(path)

    assert status.startswith("404")
    assert b'href="/"' in body


def test_a_download_that_fails_is_answered_not_raised(monkeypatch):
    """Outside a command an exception reaches the catch-all, which
    emergency-stops the installation and shuts the server down."""

    def broken():
        raise OSError("disk went away")

    monkeypatch.setattr(gerbers, "load", broken)
    wsgi = FakeWSGI(mounted=True)

    status, _headers, body = wsgi.get("/download/gerbers")

    assert status.startswith("500")
    assert b"disk went away" in body
    assert any("disk went away" in line for line in wsgi.logged)


def test_the_kicad_projects_are_handed_out_in_pieces(tmp_path, monkeypatch):
    """A hundred megabytes: built to disk and streamed, never held whole."""
    archive = tmp_path / "colloquy-kicad-0123456789ab.zip"
    archive.write_bytes(b"PK" + bytes(200_000))
    monkeypatch.setattr(kicad_projects, "files", lambda tracked=None: ())
    monkeypatch.setattr(kicad_projects, "archive", lambda folder, listed: archive)

    status, headers, body = FakeWSGI().get("/download/kicad")

    assert status.startswith("200")
    assert not isinstance(body, bytes)
    pieces = list(body)
    assert len(pieces) > 1
    assert header(headers, "Content-Length") == str(sum(len(piece) for piece in pieces))
    assert header(headers, "Content-Disposition") == (
        'attachment; filename="colloquy-kicad-abc1234.zip"'
    )


def test_a_response_in_pieces_is_sent_in_pieces():
    def send(content):
        fake = SimpleNamespace(
            _status="200 OK", _headers=[], _content=content,
            _start_response=lambda status, headers: None,
        )
        return list(WSGI2.__iter__(fake))

    assert send(b"whole") == [b"whole"]
    assert send(iter([b"one", b"two"])) == [b"one", b"two"]


# --- the update banner ---------------------------------------------------


def test_a_machine_that_does_not_update_itself_draws_no_banner():
    repository = FakeRepository(auto_update=False)

    assert updates.banner_html(repository) == ""
    assert updates.script_html(repository) == ""


def test_with_nothing_to_say_the_banner_is_there_and_hidden():
    """There, so the script has something to fill in when an update
    starts under a page that is already open."""
    html = updates.banner_html(FakeRepository(auto_update=True), back="/app/tests")

    assert 'id="update-notice"' in html and "hidden" in html
    assert 'data-back="/app/tests"' in html
    assert "update_watch.js" in updates.script_html(FakeRepository(auto_update=True))


def test_the_banner_says_what_the_repository_says():
    notice = Notice("restarting", "An update has been pulled.", 12.2)
    html = updates.banner_html(FakeRepository(auto_update=True, notice=notice))

    assert 'data-phase="restarting"' in html
    assert "An update has been pulled. Restarting in 13 s." in html
    assert "hidden" not in html.split("</style>")[1]


def test_the_way_back_is_quoted():
    """It is read back out of an attribute and navigated to."""
    html = updates.banner_html(
        FakeRepository(auto_update=True), back="/app/hardware/main pcb"
    )

    assert 'data-back="/app/hardware/main%20pcb"' in html


def test_update_status_is_what_the_script_is_told():
    notice = Notice("pulling", "Updating: pulling 3 commits.")
    wsgi = FakeWSGI(repository=FakeRepository(auto_update=True, notice=notice))

    status, headers, body = wsgi.get("/update-status")

    assert status.startswith("200")
    assert header(headers, "Cache-Control") == "no-store"
    assert json.loads(body) == {
        "boot": updates.BOOT,
        "phase": "pulling",
        "text": "Updating: pulling 3 commits.",
    }


def test_update_status_answers_with_nothing_going_on():
    _status, _headers, body = FakeWSGI().get("/update-status")

    assert json.loads(body) == {"boot": updates.BOOT, "phase": "", "text": ""}


# --- the restart the server gives itself ---------------------------------


class FakeServer:
    update_wants_a_restart = Server2.update_wants_a_restart
    restart_for_update = Server2.restart_for_update

    def __init__(self, due):
        self.colloquy = FakeColloquy()
        self.colloquy.repository.restart_is_due = due
        self.shutdown_event = Event()
        self.restart_event = Event()


def test_the_server_restarts_when_the_repository_says_it_is_due():
    server = FakeServer(due=True)
    assert server.update_wants_a_restart() is True

    server.restart_for_update()

    # The note for the next process, then the same two calls /restart
    # makes - waiting for a command in flight, since nobody chose the
    # moment of this one.
    assert server.colloquy.repository.calls == ["restarting"]
    assert server.colloquy.calls == ["held", "shutdown", "join_all"]
    assert server.shutdown_event.is_set() and server.restart_event.is_set()


def test_and_not_otherwise():
    assert FakeServer(due=False).update_wants_a_restart() is False


def test_a_stop_already_under_way_is_not_turned_into_a_restart():
    """/shutdown sets the event from a worker thread while the accept
    loop is about to ask. A restart decided at that moment would bring
    back a server somebody had just stopped."""
    server = FakeServer(due=True)
    server.shutdown_event.set()

    assert server.update_wants_a_restart() is False
