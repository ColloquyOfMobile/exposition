"""Unit tests for colloquy.code_documentation.CodeDocumentation.

A plain Base wrapped around one markdown file on disk, so it can be built
against a stub owner and pointed at a tmp_path copy of the document. Two
things are worth pinning: that it still finds the file after being moved
out of `colloquy/tests/` (a relative path computed from __file__ is
exactly the kind of thing a move breaks silently - the node would just
render an empty page), and the view/edit/save cycle, which is the only
way the document can be written from the machine the server runs on.
"""
from pathlib import Path

import pytest

from colloquy.code_documentation import CodeDocumentation


@pytest.fixture
def node(stub_factory):
    return CodeDocumentation(owner=stub_factory())


@pytest.fixture
def local_node(node, tmp_path, monkeypatch):
    """The same node, writing to a throwaway file instead of the repo's."""
    path = tmp_path / "CODE_DOCUMENTATION.md"
    path.write_text("# Title\n\nA ~~struck~~ line.\n", encoding="utf-8")
    monkeypatch.setattr(type(node), "_file_path", path)
    return node


# --- where the document lives --------------------------------------------


def test_it_points_at_the_document_next_to_the_package():
    # Computed from __file__, so this is what a move gets wrong. It lives
    # beside colloquy/ itself now, not under colloquy/tests/, because it
    # documents the whole package rather than the scenarios in there.
    assert CodeDocumentation._file_path.name == "CODE_DOCUMENTATION.md"
    assert CodeDocumentation._file_path.parent.name == "colloquy"


def test_the_document_is_actually_there():
    # The one test in this file that reads the real repo: a broken path
    # renders an empty page rather than raising, so nothing else would
    # notice.
    assert CodeDocumentation._file_path.is_file()
    assert CodeDocumentation._file_path.read_text(encoding="utf-8").startswith("#")


def test_a_missing_file_reads_as_empty_rather_than_raising(node, tmp_path, monkeypatch):
    monkeypatch.setattr(type(node), "_file_path", tmp_path / "gone.md")

    assert node.read() == ""


# --- the name the page shows ---------------------------------------------


def test_it_is_named_for_what_it_is(node):
    assert node.name == "code documentation"


def test_it_has_no_children_of_its_own(node):
    assert node.snapshot_children == {}


# --- view / edit / save --------------------------------------------------


def test_it_opens_on_the_rendered_view(local_node):
    states = local_node._snapshot_if_opened(("code documentation",))

    assert set(states) == {"edit", "rendered"}
    assert "html" in states["rendered"]


def test_the_rendered_view_understands_the_extensions_the_document_uses(local_node):
    # Strikethrough is a GFM extension rather than core markdown, and the
    # document uses ~~ to mark a claim as withdrawn - see section 10.
    html = local_node.render_html()

    assert "<del>struck</del>" in html
    assert "<h1>" in html


def test_edit_swaps_the_rendered_view_for_a_textarea(local_node):
    local_node.enter_edit()

    states = local_node._snapshot_if_opened(("code documentation",))

    assert set(states) == {"cancel", "editor"}
    assert states["editor"]["editor"] == local_node.read()


def test_cancel_goes_back_without_writing(local_node):
    before = local_node.read()
    local_node.enter_edit()

    local_node.cancel()

    assert set(local_node._snapshot_if_opened(())) == {"edit", "rendered"}
    assert local_node.read() == before


def test_save_writes_the_file_and_returns_to_the_rendered_view(local_node):
    local_node.enter_edit()

    local_node.save("# Rewritten\n")

    assert local_node.read() == "# Rewritten\n"
    assert set(local_node._snapshot_if_opened(())) == {"edit", "rendered"}


def test_save_is_reachable_as_a_command(node):
    # Registered in __init__ rather than found by name: the page posts the
    # textarea's content to .../call/save.
    assert node["save"] == node.save


# --- what a browser actually posts ---------------------------------------


def test_saving_a_document_back_unchanged_changes_nothing(local_node):
    """The bug this file was written after.

    A textarea posts its line breaks as CRLF, and `Path.write_text` opens
    in text mode, so on Windows every posted "\r\n" was written as
    "\r\r\n". Saving the document unchanged grew it by one byte per line,
    and saving again grew it again.
    """
    original = "# Title\r\n\r\nA line.\r\nAnother.\r\n"
    local_node._file_path.write_bytes(original.encode("utf-8"))

    local_node.save(local_node.read())
    once = local_node._file_path.read_bytes()
    local_node.save(local_node.read())
    twice = local_node._file_path.read_bytes()

    assert b"\r" not in once
    assert once == twice
    assert once.decode("utf-8").splitlines() == original.splitlines()


def test_a_lone_carriage_return_is_a_line_break_too(local_node):
    local_node.save("one\rtwo\r\nthree\n")

    assert local_node._file_path.read_bytes() == b"one\ntwo\nthree\n"
