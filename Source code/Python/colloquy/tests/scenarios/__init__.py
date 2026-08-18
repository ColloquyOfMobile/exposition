from pathlib import Path

import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor

from colloquy.base import Base
from colloquy.ui import leaves

# python-markdown has no built-in strikethrough (it's a GFM extension, not
# core markdown), but SCENARIOS.md uses ~~text~~ - register it the same way
# python-markdown registers its own **bold**/*italic* patterns.
_STRIKETHROUGH_RE = r"(~~)(.+?)(~~)"


class _StrikethroughExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(_STRIKETHROUGH_RE, "del"), "strikethrough", 75
        )


class Scenarios(Base):
    """View and edit colloquy/tests/SCENARIOS.md (the interaction-scenario
    catalog) straight from the web UI, instead of needing a text editor on
    whichever machine the server happens to be running on. Defaults to a
    rendered read view; "edit" switches to a plain-text textarea, "save"
    writes it back to disk and returns to the rendered view.
    """

    _file_path = Path(__file__).resolve().parent.parent / "SCENARIOS.md"

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._mode = "view"
        self["save"] = self.save

    @property
    def name(self):
        return "scenarios"

    @property
    def snapshot_children(self):
        return {}

    def read(self):
        try:
            return self._file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def render_html(self):
        return markdown.markdown(
            self.read(),
            extensions=["tables", "fenced_code", "sane_lists", _StrikethroughExtension()],
        )

    def enter_edit(self):
        self._mode = "edit"

    def cancel(self):
        self._mode = "view"

    def save(self, content):
        self._file_path.write_text(content, encoding="utf-8")
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
