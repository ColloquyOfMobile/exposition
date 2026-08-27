# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_electronics_documents.py

"""The electronics section's six documents, and which of them can be edited.

Three are written by a person and three are produced by `next_pcb.py`. The
difference has to be visible on the page and not merely stated in the
files, because an `edit` button on a generated document offers a change
that the next regeneration silently throws away.
"""
from colloquy.hardware.electronics import Electronics
from colloquy.markdown_document import GeneratedDocument, MarkdownDocument


def _electronics():
    """No owner: `Base` treats None as the root, and nothing here reaches
    up the tree. A SimpleNamespace does not work - `Base.__init__` walks
    `owner.owners`."""
    return Electronics(owner=None)


def _snapshot(document):
    return type(document)._snapshot_if_opened(document, ("app", "x"))


def test_the_section_offers_the_written_and_the_generated():
    names = [document.name for document in _electronics().documents]

    assert names == [
        "as built",
        "dirty rework",
        "next pcb",
        "next pcb netlist",
        "next pcb bill of materials",
        "next pcb mechanical",
    ]


def test_the_generated_documents_cannot_be_edited_from_the_page():
    """Not a convention - the absence of the command is the rule. A saved
    edit would live until the next `py next_pcb.py` and then vanish, which
    is worse than never having been offered."""
    for document in _electronics().documents:
        if not isinstance(document, GeneratedDocument):
            continue
        states = _snapshot(document)
        assert "edit" not in states, document.name
        assert "save" not in states, document.name
        assert "editor" not in states, document.name


def test_the_written_documents_can_still_be_edited():
    """The other half of the same rule: this section is where somebody
    writes down what they found with a scalpel in their hand."""
    for document in _electronics().documents:
        if isinstance(document, GeneratedDocument):
            continue
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
        "next pcb netlist": "Every Mega pin",
        "next pcb bill of materials": "confirm before ordering",
        "next pcb mechanical": "Mounting holes: there are none",
    }
    for document in _electronics().documents:
        if document.name not in wanted:
            continue
        html = document.render_html()
        assert "<table" in html, document.name
        assert "Generated. Do not edit." in html, document.name
