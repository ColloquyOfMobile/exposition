# -*- coding: utf-8 -*-
# Source code/Python/colloquy/markdown_document.py

"""One markdown file on disk, read and written from the page.

There are two of them now - the code documentation and the hardware setup
- and there was very nearly a second copy of all of this. What a document
node is: a rendered read view by default, "edit" for a plain-text
textarea, "save" to write it back and return to the read view. Nothing
about it is specific to either document except its file and its name.

Editing from the page rather than from a text editor is the point. The
machine that runs the server is not always the machine somebody is
sitting at, and at a rig it never is.
"""
from pathlib import Path

import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor

from colloquy.base import Base
from colloquy.ui import leaves
from colloquy.utils import write_text

# python-markdown has no built-in strikethrough (it's a GFM extension, not
# core markdown), but the code documentation uses ~~text~~ to mark a claim
# as withdrawn - register it the same way python-markdown registers its
# own **bold**/*italic* patterns.
_STRIKETHROUGH_RE = r"(~~)(.+?)(~~)"

_FOLDER = Path(__file__).resolve().parent


class _StrikethroughExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(_STRIKETHROUGH_RE, "del"), "strikethrough", 75
        )


def render_markdown(text):
    """Markdown to HTML, with the extensions both document kinds want."""
    return markdown.markdown(
        text,
        extensions=[
            "tables",
            "fenced_code",
            "sane_lists",
            _StrikethroughExtension(),
        ],
    )


class MarkdownDocument(Base):
    """Subclass and set `file_name` and `document_name`."""

    # Beside colloquy/ itself, not under any one corner of it: these
    # describe the whole thing. `folder` is a class attribute rather than
    # a constant so a test can point a document at a throwaway copy
    # instead of writing to the repo's own.
    folder = _FOLDER
    file_name = None
    document_name = None

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._mode = "view"
        self["save"] = self.save

    @property
    def file_path(self):
        return self.folder / self.file_name

    @property
    def name(self):
        return self.document_name

    @property
    def snapshot_children(self):
        return {}

    def read(self):
        try:
            return self.file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def render_html(self):
        return render_markdown(self.read())

    def enter_edit(self):
        self._mode = "edit"

    def cancel(self):
        self._mode = "view"

    def save(self, content):
        write_text(self.file_path, content)
        self._mode = "view"
        self.open()

    def _snapshot_if_opened(self, path):
        if self._mode == "edit":
            return {
                "cancel": self.cancel,
                "editor": leaves.editor(path, "editor", self.read()),
            }

        return {
            "edit": self.enter_edit,
            "rendered": leaves.html(path, "rendered", self.render_html()),
        }

class GeneratedDocument(Base):
    """A document produced by code: shown, never edited.

    **Rendered from the generator on every view, not from the file.** The
    generated documents are also written to disk - that is what somebody
    opens beside a schematic editor - but a page that read the file could
    show a copy from before the last change to the design, and be
    convincing about it. Calling the generator is what makes the page and
    the design the same thing by construction.

    It follows that there is no `edit` and no `save`. `MarkdownDocument`
    has both, and hanging one of those on a generated file would offer an
    edit that the next `py next_pcb.py` silently throws away. The file
    says "Generated. Do not edit." at the top; this is that rule expressed
    as the absence of a button rather than as a sentence.

    `source` is a callable returning markdown, so the import it needs
    happens when somebody opens the node rather than at startup - which
    matters for the mechanical one, since it parses a 1.7 MB board file.
    """

    def __init__(self, owner, document_name, source, written_to=None):
        super().__init__(owner=owner)
        self._document_name = document_name
        self._source = source
        self._written_to = written_to

    @property
    def name(self):
        return self._document_name

    @property
    def snapshot_children(self):
        return {}

    def read(self):
        return self._source()

    def render_html(self):
        return render_markdown(self.read())

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._written_to is not None:
            # Where the copy on disk lives, for whoever wants it next to
            # KiCad rather than next to a browser.
            leaves.into(states, path)("file", self._written_to)
        states["rendered"] = leaves.html(path, "rendered", self.render_html())
        return states
