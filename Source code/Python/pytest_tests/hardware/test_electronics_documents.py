# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_electronics_documents.py

"""The electronics section's documents, and which of them can be edited.

Three are written by a person; three more are produced by `next_pcb.py`
and hang **under** `next pcb`, because that is what they are - it is the
reasoning and they are what it produces. As siblings they each had to
carry its name at the front of their own, which is a namespace spelled
out three times in the one place the tree already provides one.

The written/generated difference has to be visible on the page and not
merely stated inside the files, because an `edit` button on a generated
document offers a change the next regeneration silently throws away.
"""
from colloquy.hardware.electronics import Electronics, NextPCB
from colloquy.markdown_document import GeneratedDocument, MarkdownDocument


def _electronics():
    """No owner: `Base` treats None as the root, and nothing here reaches
    up the tree. A SimpleNamespace does not work - `Base.__init__` walks
    `owner.owners`."""
    return Electronics(owner=None)


def _snapshot(document):
    return type(document)._snapshot_if_opened(document, ("app", "x"))


def _generated(electronics=None):
    electronics = electronics or _electronics()
    for document in electronics.documents:
        if isinstance(document, NextPCB):
            return document.generated
    raise AssertionError("no next pcb document")


def test_the_section_offers_the_written_documents_not_the_generated_ones():
    """Four written, not seven: what `next pcb` generates hangs under
    `next pcb`, and `harness` is generated too and is not a document
    anybody edits."""
    names = [document.name for document in _electronics().documents]

    assert names == [
        "as built",
        "dirty rework",
        "next pcb",
        "one board per body",
        "opencm and pro minis",
    ]


def test_the_three_solutions_are_siblings():
    """The second and third are not variations on `next pcb` - they are
    complete answers to the same question, against the same fixed
    harness, and they sit beside it rather than under it."""
    children = _electronics().snapshot_children

    for name in ("next pcb", "one board per body", "opencm and pro minis"):
        assert name in children, name
    for name in ("one board per body", "opencm and pro minis"):
        assert name not in children["next pcb"].snapshot_children, name


def test_what_next_pcb_generates_hangs_under_next_pcb():
    """Short names, and the tree providing the namespace instead of each
    name repeating it."""
    names = [document.name for document in _generated()]

    assert names == ["netlist", "bill of materials", "mechanical"]


def test_the_generated_documents_are_reachable_by_opening_next_pcb():
    """`MarkdownDocument._snapshot_if_opened` used to return its own dict
    outright, which meant a document could never have a child: the walk
    would reach one and opening the parent would not list it."""
    next_pcb = [
        document for document in _electronics().documents
        if isinstance(document, NextPCB)
    ][0]

    states = _snapshot(next_pcb)

    for name in ("netlist", "bill of materials", "mechanical"):
        assert name in states, name
    # And it is still the document it was.
    assert "edit" in states
    assert "rendered" in states


def test_the_generated_documents_cannot_be_edited_from_the_page():
    """Not a convention - the absence of the command is the rule. A saved
    edit would live until the next `py next_pcb.py` and then vanish, which
    is worse than never having been offered."""
    for document in _generated():
        states = _snapshot(document)
        assert "edit" not in states, document.name
        assert "save" not in states, document.name
        assert "editor" not in states, document.name


def test_the_written_documents_can_still_be_edited():
    """The other half of the same rule: this section is where somebody
    writes down what they found with a scalpel in their hand."""
    for document in _electronics().documents:
        assert isinstance(document, MarkdownDocument)
        assert "edit" in _snapshot(document), document.name


def test_a_generated_document_renders_from_its_generator_not_from_a_file():
    """The whole reason it is not a `MarkdownDocument` pointed at the
    written file: that could show a copy from before the last change to
    the design, and be convincing about it."""
    answers = ["# first"]
    document = GeneratedDocument(
        owner=None, document_name="x", source=lambda: answers[0]
    )

    assert "first" in document.render_html()

    answers[0] = "# second"

    assert "second" in document.render_html()


def test_a_generated_document_says_where_its_file_is():
    """Somebody wanting it beside a schematic editor rather than beside a
    browser needs the path, and the node is where they are standing."""
    document = GeneratedDocument(
        owner=None,
        document_name="x",
        source=lambda: "# x",
        written_to="CAD/KiCad/electronic box v2/NETLIST.md",
    )

    states = _snapshot(document)

    assert states["file"]["value"] == "CAD/KiCad/electronic box v2/NETLIST.md"


def test_the_generated_documents_actually_produce_their_content():
    """They call the real generators, so this is also the check that the
    page cannot be opened onto a traceback."""
    wanted = {
        "netlist": "Every Mega pin",
        "bill of materials": "confirm before ordering",
        "mechanical": "Mounting holes: there are none",
    }
    for document in _generated():
        assert document.name in wanted, document.name
        html = document.render_html()
        assert "<table" in html, document.name
        assert "Generated. Do not edit." in html, document.name
