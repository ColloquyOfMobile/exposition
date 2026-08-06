from pathlib import Path
from colloquy.base import Base


class Scenarios(Base):
    """View and edit colloquy/tests/SCENARIOS.md (the interaction-scenario
    catalog) straight from the web UI, instead of needing a text editor on
    whichever machine the server happens to be running on.
    """

    _file_path = Path(__file__).resolve().parent.parent / "SCENARIOS.md"

    def __init__(self, owner):
        super().__init__(owner=owner)
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

    def save(self, content):
        self._file_path.write_text(content, encoding="utf-8")
        self.open()

    def _snapshot_if_opened(self, path):
        return {
            "editor": {
                "path": path + ("editor",),
                "name": "editor",
                "editor": self.read(),
            }
        }
