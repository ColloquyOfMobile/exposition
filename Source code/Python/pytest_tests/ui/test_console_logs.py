"""A browser can read worker output without running a tree command."""
import json
from pathlib import Path
from types import SimpleNamespace

from colloquy.logger import Logger
from colloquy.logs import Logs, monitor
from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui.mock import MockApp, OfflineServer, request


def test_home_opens_the_console_as_a_tree_branch():
    app = MockApp()
    _, home = request("/home", app=app)
    assert "<h1>Home</h1>" in home
    assert 'href="/home/logs"' in home
    assert 'id="monitor"' not in home
    for route in ("/home/logs", "/home/call/logs/open"):
        status, page = request(route, app=app)
        assert status == "200 OK"
        assert page.count('id="monitor"') == 1
    _, closed = request("/home/call/logs/close", app=app)
    assert 'id="monitor"' not in closed


def test_live_feed_merges_elapsed_times_and_discovers_new_workers(tmp_path, monkeypatch):
    monkeypatch.setattr(Logger, "_log_folder", tmp_path)
    (tmp_path / "main.log").write_text("59.99s ready\n01:00.10s finished\n")
    _, body = request("/thread-log")
    assert json.loads(body)["sources"] == ["main"]
    (tmp_path / "tests").mkdir()
    nested = tmp_path / "tests" / "scope.log"
    nested.write_text("01:00.00:\n+ first\n+ second\n")
    _, body = request("/thread-log")
    assert json.loads(body)["events"] == [
        ["59.99s", "main", "ready"],
        ["01:00.00", "tests/scope", ""],
        ["01:00.00", "tests/scope", "+ first"],
        ["01:00.00", "tests/scope", "+ second"],
        ["01:00.10s", "main", "finished"],
    ]
    nested.write_text("01:01.00 <input>\n", encoding="utf-8")
    _, _, body = monitor.response({"QUERY_STRING": "source=tests%2Fscope"})
    assert json.loads(body)["events"] == [["01:01.00", "tests/scope", "<input>"]]


def test_tail_is_bounded_and_a_missing_selection_stays_empty(tmp_path):
    (tmp_path / "run.log").write_text("00.01s old\n" * 5000 + "01.20s newest\n")
    revision, initial = monitor.snapshot(tmp_path, "run")
    rows = initial["events"]
    assert len(rows) == monitor.MAX_EVENTS
    assert rows[-1] == ["01.20s", "run", "newest"]
    assert len(monitor.tail(tmp_path / "run.log").encode()) <= monitor.TAIL_BYTES
    assert monitor.snapshot(tmp_path, "run", revision) == (revision, None)
    assert monitor.snapshot(tmp_path, "../other")[1]["events"] == []


def test_a_thread_can_have_both_output_and_child_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(Logger, "_log_folder", tmp_path)
    (tmp_path / "tests.log").write_text("parent")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "scope.log").write_text("child")
    root = Logs(None)
    branch = root.snapshot_children["tests"]
    focus = branch._snapshot_if_opened(("logs", "tests"))
    assert focus["content"]["pre"] == "parent"
    assert focus["scope"]["path"] == ("logs", "tests", "scope")
    assert branch.snapshot_children["scope"]._snapshot_if_opened(())["content"]["pre"] == "child"


def test_an_expanded_editor_saves_without_losing_its_parent_view():
    app = MockApp()
    status, html = request("/app/documents/call/notes/open", app=app)
    assert status == "200 OK"
    assert 'action="/app/documents/call/notes/save"' in html
    status, _ = request("/app/documents/call/notes/save", app=app, content="new text")
    assert status.startswith("303")
    assert "new text" in request("/app/documents", app=app)[1]


def test_monitor_keeps_clear_of_the_command_lock_and_obeys_standby(tmp_path, monkeypatch):
    monkeypatch.setattr(Logger, "_log_folder", tmp_path)
    pcb = SimpleNamespace(is_mounted=True)
    root = SimpleNamespace(hardware=SimpleNamespace(main_pcb=pcb))
    server = OfflineServer(root)
    def get():
        answers = []
        response = WSGI2(server, {"PATH_INFO": "/thread-log"}, lambda *args: answers.append(args))
        body = b"".join(response)
        return answers[0][0], body
    status, body = get()
    assert status == "200 OK" and json.loads(body)["events"] == []
    pcb.is_mounted = False
    assert get()[0].startswith("303")


def test_preview_session_preserves_installation_logs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Logger, "_log_folder", Path("local/logs"))
    Logger.start_session()
    installation = Logger.folder() / "main.log"
    installation.write_text("keep")
    Logger.start_session(preview=True)
    Logger()("preview only")
    assert installation.read_text() == "keep"
    assert "preview only" in (Logger.folder() / "MainThread.log").read_text()
