"""Unit tests for the two markdown documents on the page.

`MarkdownDocument` is a plain Base wrapped around one file on disk, so it
can be built against a stub owner and pointed at a tmp_path copy. Both
documents are the same machinery with a different file and a different
name - which is the point of the base class, and worth a test each so
that a document cannot lose its file by being moved.

The one thing they do *not* share is where they hang, and that is the
whole of what distinguishes them:

- the **code documentation** is on the root and hidden on the
  installation's own machine, since reading source is not what that
  machine is for;
- the **hardware setup** hangs off the audio bench test and is not gated
  at all - it is about that one bench, and a bench is where it is wanted;
- the **three electronics documents** hang under `hardware`, beside the
  main PCB's own state, and are not gated either. `next pcb` also
  carries the three documents generated from it - see
  `test_electronics_documents.py`. The machine with the
  board in it is the one place none of it is hypothetical, and the
  machine somebody is holding a scalpel over is likely to be the other
  one.
"""
import pytest

from colloquy.code_documentation import CodeDocumentation
from colloquy.hardware.electronics import (
    AsBuilt,
    DirtyRework,
    NextPCB,
    OneBoardPerBody,
)
from colloquy.tests.test_audio_subsystem.setup_document import HardwareSetup
from colloquy.markdown_document import MarkdownDocument

DOCUMENTS = (
    CodeDocumentation,
    HardwareSetup,
    AsBuilt,
    DirtyRework,
    NextPCB,
    OneBoardPerBody,
)


@pytest.fixture(params=DOCUMENTS, ids=lambda cls: cls.__name__)
def document(request, stub_factory):
    return request.param(owner=stub_factory())


@pytest.fixture
def local(document, tmp_path, monkeypatch):
    """The same document, over a throwaway file instead of the repo's."""
    monkeypatch.setattr(type(document), "folder", tmp_path)
    document.file_path.write_text(
        "# Title\n\nA ~~struck~~ line.\n", encoding="utf-8"
    )
    return document


# --- where each document lives -------------------------------------------


def test_each_document_sits_beside_what_it_describes(document):
    # Computed from __file__, so this is what a move gets wrong - and a
    # broken path renders an empty page rather than raising, so nothing
    # else would notice. They live in different folders on purpose: one
    # describes the package, the other describes one test's bench.
    assert document.file_path.suffix == ".md"
    expected = {
        "CODE_DOCUMENTATION.md": "colloquy",
        "HARDWARE_SETUP.md": "test_audio_subsystem",
        "AS_BUILT.md": "electronics",
        "DIRTY_REWORK.md": "electronics",
        "NEXT_PCB.md": "electronics",
        "ONE_BOARD_PER_BODY.md": "electronics",
    }
    assert document.file_path.parent.name == expected[document.file_name]


def test_each_document_is_actually_there(document):
    assert document.file_path.is_file()
    assert document.file_path.read_text(encoding="utf-8").startswith("#")


def test_no_two_documents_share_a_file(stub_factory):
    """Four of them now share a folder as well as a base class, and a
    copied `file_name` would have two nodes editing one file - with the
    second save silently undoing the first."""
    names = [cls.file_name for cls in DOCUMENTS]

    assert len(set(names)) == len(names)
    assert set(names) == {
        "CODE_DOCUMENTATION.md",
        "HARDWARE_SETUP.md",
        "AS_BUILT.md",
        "DIRTY_REWORK.md",
        "NEXT_PCB.md",
        "ONE_BOARD_PER_BODY.md",
    }


def test_no_two_documents_share_a_name_on_the_page(stub_factory):
    """They are registered into their owner by name, so two alike would
    mean one of them simply not being drawn."""
    names = [cls.document_name for cls in DOCUMENTS]

    assert len(set(names)) == len(names)


def test_they_are_named_for_what_they_are(document):
    assert document.name in {
        "code documentation",
        "hardware setup",
        "as built",
        "dirty rework",
        "next pcb",
        "one board per body",
    }
    assert document.name == type(document).document_name


def test_a_missing_file_reads_as_empty_rather_than_raising(
    document, tmp_path, monkeypatch
):
    monkeypatch.setattr(type(document), "folder", tmp_path / "nowhere")

    assert document.read() == ""


def test_only_next_pcb_has_children_of_its_own(document):
    """A document is a file on the page and nothing else - except `next
    pcb`, which carries the three things generated from it. They hang
    under it because that is what they are, and because as siblings each
    had to repeat its name at the front of its own."""
    if isinstance(document, NextPCB):
        assert set(document.snapshot_children) == {
            "netlist",
            "bill of materials",
            "mechanical",
        }
    else:
        assert document.snapshot_children == {}


# --- view / edit / save ---------------------------------------------------


def test_it_opens_on_the_rendered_view(local):
    states = local._snapshot_if_opened(("doc",))

    assert set(states) == {"edit", "rendered"} | set(local.snapshot_children)
    assert "html" in states["rendered"]


def test_the_rendered_view_understands_the_extensions_the_documents_use(local):
    # Strikethrough is a GFM extension rather than core markdown, and the
    # code documentation uses ~~ to mark a claim as withdrawn.
    html = local.render_html()

    assert "<del>struck</del>" in html
    assert "<h1>" in html


def test_edit_swaps_the_rendered_view_for_a_textarea(local):
    local.enter_edit()

    states = local._snapshot_if_opened(("doc",))

    assert set(states) == {"cancel", "editor"} | set(local.snapshot_children)
    assert states["editor"]["editor"] == local.read()


def test_cancel_goes_back_without_writing(local):
    before = local.read()
    local.enter_edit()

    local.cancel()

    expected = {"edit", "rendered"} | set(local.snapshot_children)
    assert set(local._snapshot_if_opened(())) == expected
    assert local.read() == before


def test_save_writes_the_file_and_returns_to_the_rendered_view(local):
    local.enter_edit()

    local.save("# Rewritten\n")

    assert local.read() == "# Rewritten\n"
    expected = {"edit", "rendered"} | set(local.snapshot_children)
    assert set(local._snapshot_if_opened(())) == expected


def test_save_is_reachable_as_a_command(document):
    # Registered in __init__ rather than found by name: the page posts the
    # textarea's content to .../call/save.
    assert document["save"] == document.save


# --- what a browser actually posts ---------------------------------------


def test_saving_a_document_back_unchanged_changes_nothing(local):
    """The bug this file was written after.

    A textarea posts its line breaks as CRLF, and `Path.write_text` opens
    in text mode, so on Windows every posted "\r\n" was written as
    "\r\r\n". Saving the document unchanged grew it by one byte per line,
    and saving again grew it again.
    """
    original = "# Title\r\n\r\nA line.\r\nAnother.\r\n"
    local.file_path.write_bytes(original.encode("utf-8"))

    local.save(local.read())
    once = local.file_path.read_bytes()
    local.save(local.read())
    twice = local.file_path.read_bytes()

    assert b"\r" not in once
    assert once == twice
    assert once.decode("utf-8").splitlines() == original.splitlines()


def test_a_lone_carriage_return_is_a_line_break_too(local):
    local.save("one\rtwo\r\nthree\n")

    assert local.file_path.read_bytes() == b"one\ntwo\nthree\n"


# --- the hardware setup's own images -------------------------------------


def test_the_hardware_setup_photographs_are_where_it_says_they_are():
    """Every image the setup document links to is on disk and served.

    They are photographs out of Thomas's PDF, and a broken one shows as a
    little empty box on the page - which nobody notices until they are
    standing at a bench trying to identify a board.
    """
    import re

    from colloquy.server2.wsgi2 import _STATIC_CONTENT_TYPES, _STATIC_ROOTS

    document = HardwareSetup.__new__(HardwareSetup)
    markdown_text = document.file_path.read_text(encoding="utf-8")

    sources = re.findall(r"!\[[^\]]*\]\((/static/[^)]+)\)", markdown_text)
    assert sources, "the setup document has lost its photographs"

    for source in sources:
        relative = source[len("/static/") :]
        path = _STATIC_ROOTS["static"] / relative
        assert path.is_file(), source
        assert path.suffix in _STATIC_CONTENT_TYPES, (
            f"{source} would be served as a download, not shown"
        )
