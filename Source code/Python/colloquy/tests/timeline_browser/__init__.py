from pathlib import Path

from colloquy.base import Base

from colloquy.code_documentation import write_text
from .rendering import render_html
from colloquy.ui import leaves


class Timeline(Base):
    """One *.timeline file: a rough, sequential prediction of what the
    installation does from some starting point (see the file's own leading
    "#" comment for which scenario it covers). Defaults to a rendered view;
    "edit" switches to a plain-text textarea, "save" writes it back to disk
    and returns to the rendered view - same view/edit shape as Scenarios.
    """

    def __init__(self, owner, file_path):
        super().__init__(owner=owner)
        self._file_path = file_path
        self._mode = "view"
        self["save"] = self.save

    @property
    def name(self):
        return self._file_path.stem

    @property
    def snapshot_children(self):
        return {}

    def read(self):
        try:
            return self._file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def enter_edit(self):
        self._mode = "edit"

    def cancel(self):
        self._mode = "view"

    def save(self, content):
        write_text(self._file_path, content)
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
            "rendered": leaves.html(path, "rendered", render_html(self.read())),
        }


class Timelines(Base):
    """Browse the *.timeline files under colloquy/tests/timelines/ from the
    web UI. File list is rescanned every request, so a new file dropped in
    that folder shows up without a restart.
    """

    _folder = Path(__file__).resolve().parent.parent / "timelines"

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._children = {}

    @property
    def name(self):
        return "timelines"

    @property
    def snapshot_children(self):
        if not self._folder.exists():
            return {}

        found = {}
        for file_path in sorted(self._folder.glob("*.timeline")):
            key = file_path.stem
            found[key] = self._children.get(key) or Timeline(
                owner=self, file_path=file_path
            )

        self._children = found
        return dict(self._children)
